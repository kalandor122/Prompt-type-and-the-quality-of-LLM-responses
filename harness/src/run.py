"""Pilot runner.

Usage
-----
  python src/run.py --dry-run                 # print the run matrix, no API calls
  python src/run.py --smoke                   # 16 cheap runs to shake out the harness
  python src/run.py --limit 4                 # first N runs only
  python src/run.py                           # the full pilot
  python src/run.py --models gpt-6-luna       # subset
  python src/run.py --arms A,B                # subset

Everything is written under runs/<timestamp>/ so an aborted run never overwrites
a completed one.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from harness import get_driver, usage_tokens          # noqa: E402
from itemloader import (ARMS, CONTINUE_FOLLOWUP, NO_INFO_FOLLOWUP, OK_FOLLOWUP,
                        arm_prompt,
                        load_items, max_rubric_points)  # noqa: E402
from simulator import Simulator, build_wants_block  # noqa: E402
from workspace import materialise as materialise_workspace  # noqa: E402
from workspace import materialise_t3  # noqa: E402
from workspace import materialise_t11, materialise_t13  # noqa: E402

CONFIG = ROOT / "config.json"
ITEMS_DIR = ROOT / "items"


# --------------------------------------------------------------------- config
def load_config(path: str = "") -> dict:
    return json.loads((Path(path) if path else CONFIG).read_text(encoding="utf-8"))


# ------------------------------------------------------------------- run plan
def build_matrix(cfg: dict, items: list[dict], models: list[dict],
                 arms: list[str]) -> list[dict]:
    reps_cfg = cfg.get("reps", {"light": 2, "agentic": 1})
    matrix = []
    for m in models:
        for it in items:
            is_agentic = it.get("category") == "agentic"
            reps = reps_cfg.get("agentic" if is_agentic else "light", 2)
            for arm in arms:
                for rep in range(1, reps + 1):
                    matrix.append({"model": m, "item": it, "arm": arm, "rep": rep})
    rng = random.Random(cfg.get("seed", 0))
    rng.shuffle(matrix)          # interleaved order is load-bearing: see S6.5
    return matrix


def _sim_reply(sim, item, prompt, answer, session, mode):
    """Ask the simulated user, retrying with escalating nudges if it goes silent.

    A reasoning-heavy simulator can spend its whole output budget on thinking and
    return nothing at all. On the 2026-09-29 corpus 42% of simulator turns came
    back empty and the old fallback then told the test model "that's all fine",
    handing it an unearned pass. Measured cause: the simulator averages ~1174
    output tokens and the old cap was 1200, so it was routinely starved.

    Still worth defending against: three attempts with escalating directness,
    and the failure is REPORTED rather than absorbed into a silent default.
    """
    nudges = (
        "",
        "\n\n(Reply with your answer only. No analysis.)",
        "\n\nREPLY WITH ONLY YOUR ANSWER TO THE ASSISTANT. One short paragraph in "
        "your own everyday words. No preamble, no analysis, no list of rules.",
    )
    out, attempts = {}, 0
    for extra in nudges:
        attempts += 1
        out = sim.answer(item, prompt, answer + extra, f"{session}-a{attempts}", mode=mode)
        if (out.get("text") or "").strip():
            break
    out["attempts"] = attempts
    return out


_STOPWORDS = frozenset("""
about above after again against because before being below between both cannot
could doing down during each few from further having here hers herself himself
itself just more most other ought ours ourselves over same should some such than
that their theirs them themselves then there these they this those through under
until very were what when where which while with would your yours yourself must
does have will about which where whatever think best really anything
""".split())

# want_voice is "Whatever you think is best." for wants the user has no
# opinion on. That phrase must never contribute matching keys, or a
# non-answer scores as if it had delivered every one of them.
GENERIC_VOICE = frozenset({
    "whatever you think is best.", "whatever you think is best", "any",
    "any", "either", "any reasonable level", "any within the luxury register",
    "either is acceptable so long as it waits for confirmation before applying",
})


def _artifact_snapshot(sandbox_path) -> dict:
    """Fingerprint whatever the model has written so far.

    NOTE ON INTERPRETATION: in the two-phase design turn 1 is *supposed* to
    write nothing, so this diff does not measure 'did the correction land' —
    any difference just means 'it did the task'. Kept as artifacts_changed.
    Whether the delivered wants were honoured is the rubric's job.
    """
    snap = {}
    if not sandbox_path or not Path(sandbox_path).is_dir():
        return snap
    for f in sorted(Path(sandbox_path).rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(sandbox_path))
            try:
                snap[rel] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            except OSError:
                pass
    return snap


def _wants_delivered(item: dict, sim_text: str) -> int:
    """How many U wants the simulated user actually put into words.

    The honest half of the arm-B/E story: not 'did the output change', but
    'did the user's information reach the model at all'. A silent simulator
    scores 0, which is exactly the failure we want visible.
    """
    if not (sim_text or "").strip():
        return 0
    hay = set(re.sub(r"[^a-z0-9 ]", " ", sim_text.lower()).split())
    n = 0
    for h in item.get("hidden", []):
        if h.get("tag") != "U":
            continue
        voice = (h.get("want_voice") or "").strip().lower()
        src = h.get("want") or ""
        if voice not in GENERIC_VOICE:
            src = f"{src} {h.get('want_voice') or ''}"
        keys = {w for w in re.sub(r"[^a-z0-9 ]", " ", src.lower()).split()
                if len(w) >= 4 and w not in _STOPWORDS}
        # A want counts as delivered when at least two of its distinctive words
        # appear, or one for wants that only have one or two such words
        # ("browser web app"). A proportional rule is wrong here: a want is
        # written as a full spec paragraph with a dozen key words, but the
        # simulated user expresses two of them and that IS the want being
        # delivered. Requiring half the spec silently scored real corrections
        # as zero.
        hit = len(keys & hay)
        if keys and (hit >= 2 or (len(keys) <= 3 and hit >= 1)):
            n += 1
    return n


def _assistant_message(out: dict) -> dict:
    """Echo turn 1 back to the model as a valid assistant message.

    Reasoning models need their reasoning echoed (some gateways expect it), so we
    pass the driver's own assistant message through when it looks like one. The
    old code appended `dict(out1["raw"])` — which for the OpenRouter driver is
    the whole API response object, not a message. Harmless in OpenCode mode
    (where the session holds the conversation) and a hard break in gateway mode
    (where `messages` IS the conversation).
    """
    raw = out.get("raw")
    if isinstance(raw, dict) and raw.get("role"):
        return {k: v for k, v in raw.items() if v is not None}
    if isinstance(raw, list):
        for r in raw:
            if isinstance(r, dict) and r.get("role") == "assistant":
                return {k: v for k, v in r.items() if v is not None}
    return {"role": "assistant", "content": out.get("text", "")}


def run_id_for(entry: dict) -> str:
    """Canonical run id — single definition so resume can match it reliably."""
    item, model = entry["item"], entry["model"]
    return f"{item['id']}-{model['label'].replace(' ', '')}-{entry['arm']}-r{entry['rep']}"


# ---------------------------------------------------------------- one run
def run_one(driver, sim: Simulator, cfg: dict, entry: dict,
            out_root: Path) -> dict:
    model, item, arm = entry["model"], entry["item"], entry["arm"]
    run_id = run_id_for(entry)
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    workspace_dir = None
    session = f"pilot-{run_id}"
    # Seeding is per-item, not per-category: T6 is generated (fresh corruption
    # per run), T3 needs the existing Node/Express app that "for my app"
    # refers to. Without it models correctly report the directory is empty and
    # write nothing -- correct behaviour with no measurable output.
    if item.get("category") == "agentic":
        workspace_dir = run_dir / "workspace"
        # Seeding is per-item, not per-category: T6 is generated (fresh
        # corruption per run), T11 needs the policy + ticket, T13 needs the
        # night's log. Each item has its own materialiser so the workspace it
        # gets is exactly the one its hidden wants describe.
        makers = {"T11": materialise_t11, "T13": materialise_t13}
        maker = makers.get(item.get("id"), materialise_workspace)
        maker(workspace_dir)
        # Seed the model's tool sandbox with the task workspace — without this
        # the agent sees an empty directory and (correctly) says so. The
        # ground_truth.json file stays out: it is for the grader, and letting
        # the model read it would leak the answer it is being scored on.
        sb = getattr(driver, "sandbox", None)
        if sb is not None:
            sb.seed(session, workspace_dir)
    elif item.get("id") == "T3":
        workspace_dir = run_dir / "workspace"
        materialise_t3(workspace_dir)
        sb = getattr(driver, "sandbox", None)
        if sb is not None:
            sb.seed(session, workspace_dir)
    prompt_text = arm_prompt(arm, item)
    messages = [{"role": "user", "content": prompt_text}]
    transcript = [{"turn": 1, "role": "user", "content": prompt_text}]

    t0 = time.time()
    out1 = driver.complete(protocol=model.get("protocol", "chat"), model=model,
                           messages=messages, temperature=cfg.get("temperature", 0.2),
                           max_tokens=cfg.get("max_tokens", 4000), session=session)
    t1_in, t1_out = usage_tokens(out1["usage"])
    transcript.append({"turn": 1, "role": "assistant",
                       "content": out1["text"], "thinking": out1["thinking"]})
    asked = out1["text"].count("?") > 0
    # Fingerprint the model's output NOW, before any correction arrives, so we
    # can tell later whether the correction actually changed anything.
    snap_before = _artifact_snapshot(getattr(driver, "sandbox_for", lambda _s: None)(session))

    final_text, sim_turn = out1["text"], None
    sim_ok = None                      # None = no simulator was consulted (arm A)
    t2_in = t2_out = 0

    if arm in ("B", "D", "E"):
        # Fixed two-turn protocol: exactly one follow-up, then the model finishes.
        #   B = the model asks, the user answers ONLY what was asked
        #   D = the model writes a PLAN, the user corrects the plan
        #   E = the model states its assumptions, the user corrects what is wrong
        # Arms D and E always consult the simulated user; arm B only when a
        # question was actually asked.
        #
        # NEVER default to "That's all fine, go ahead." when the simulator comes
        # back empty. That fallback converts a failed treatment into an
        # anti-treatment: it hands the model an unearned pass, and it is not
        # random (it hit arm E hardest, exactly where corrections mattered).
        # A silent simulator now costs a data point instead of inventing one.
        if arm == "E":
            sim_turn = _sim_reply(sim, item, item["prompt"], out1["text"],
                                  session + "-sim", "correct")
            followup = sim_turn["text"].strip()
        elif arm == "D":
            sim_turn = _sim_reply(sim, item, item["prompt"], out1["text"],
                                  session + "-sim", "plan")
            followup = sim_turn["text"].strip()
        elif asked:
            sim_turn = _sim_reply(sim, item, item["prompt"], out1["text"],
                                  session + "-sim", None)
            followup = sim_turn["text"].strip()
        else:
            followup = NO_INFO_FOLLOWUP
        sim_ok = True
        if sim_turn and not followup:
            # Retry already happened inside _sim_reply and still nothing came
            # back. Say nothing rather than approve; flag the run so it can be
            # excluded from the B/E analysis.
            sim_ok = False
            followup = NO_INFO_FOLLOWUP
        messages.append(_assistant_message(out1))
        # The sim's reply alone is not enough: without an explicit "now do it"
        # the model treats turn 2 as a write-up of work it has already finished
        # and never writes a file. CONTINUE_FOLLOWUP is added identically to B
        # and E, so it is harness mechanics rather than treatment.
        messages.append({"role": "user", "content": followup + CONTINUE_FOLLOWUP})
        transcript.append({"turn": 2, "role": "user", "content": followup,
                           "from_simulator": bool(sim_turn), "simulator_ok": sim_ok})

        out2 = driver.complete(protocol=model.get("protocol", "chat"), model=model,
                               messages=messages, temperature=cfg.get("temperature", 0.2),
                               max_tokens=cfg.get("max_tokens", 4000), session=session)
        t2_in, t2_out = usage_tokens(out2["usage"])
        transcript.append({"turn": 2, "role": "assistant",
                           "content": out2["text"], "thinking": out2["thinking"]})
        final_text = out2["text"]

    # --- summary fallback -------------------------------------------------
    # A model can do the whole task inside its tool loop and reasoning, then
    # return an empty final message. That leaves nothing to grade, and it hides
    # the rubric's central question: did it REPORT the anomaly, or quietly tidy
    # up? So elicit exactly one summary when (and only when) it is needed.
    # Harness mechanics, not treatment — every arm gets it identically.
    summary_prompt = ("Summarise in plain language for the user: what you "
                      "found, what you changed, and anything they should know.")
    if not (final_text or "").strip():
        last_out = out2 if arm in ("B", "E") else out1
        base = last_out.get("messages") or (messages + [
            {"role": "assistant", "content": final_text or ""}])
        try:
            out_s = driver.complete(protocol=model.get("protocol", "chat"),
                                    model=model,
                                    messages=base + [{"role": "user", "content": summary_prompt}],
                                    temperature=cfg.get("temperature", 0.2),
                                    max_tokens=cfg.get("max_tokens", 4000),
                                    session=session, use_tools=False)
        except TypeError:      # drivers that do not take use_tools
            out_s = driver.complete(protocol=model.get("protocol", "chat"),
                                    model=model,
                                    messages=base + [{"role": "user", "content": summary_prompt}],
                                    temperature=cfg.get("temperature", 0.2),
                                    max_tokens=cfg.get("max_tokens", 4000),
                                    session=session)
        t_s_in, t_s_out = usage_tokens(out_s["usage"])
        transcript.append({"turn": 3, "role": "user", "content": summary_prompt,
                           "harness_elicited": True})
        transcript.append({"turn": 3, "role": "assistant", "content": out_s["text"],
                           "thinking": out_s["thinking"], "harness_elicited": True})
        final_text = out_s["text"]
        t1_in, t1_out = t1_in + t_s_in, t1_out + t_s_out

    # ------------------------------------------------------------- artefacts
    snap_after = _artifact_snapshot(getattr(driver, "sandbox_for", lambda _s: None)(session))
    wants_delivered = (_wants_delivered(item, (sim_turn or {}).get("text", ""))
                       if sim_turn else 0)
    # WHAT THIS MEASURES, precisely:
    #   artifacts_changed  - did the file set change at all. In the two-phase
    #                        design turn 1 writes nothing by construction, so
    #                        this is really 'did it do the task'.
    #   wants_delivered    - how many U wants the simulated user put into words
    #                        (0 = silence or a non-answer).
    #   correction_applied - 1 only when the user's information was delivered
    #                        AND the model then produced output. 0 when it
    #                        received the information and wrote nothing.
    #                        Blank for arm A (nothing to apply) or when the
    #                        simulator itself was silent.
    # Whether the output HONOURED those wants is not mechanical and stays with
    # the rubric. Do not read correction_applied as 'the fix was correct'.
    artifacts_changed = (snap_before != snap_after) if (snap_before or snap_after) else None
    if not sim_ok or arm not in ("B", "E"):
        correction_applied = None
    else:
        correction_applied = int(bool(wants_delivered) and bool(snap_after))
    (run_dir / "response.md").write_text(final_text, encoding="utf-8")
    (run_dir / "transcript.json").write_text(
        json.dumps({"run_id": run_id, "model": model, "item_id": item["id"],
                    "arm": arm, "rep": entry["rep"], "asked_questions": asked,
                    "session": session, "elapsed_s": round(time.time() - t0, 1),
                    "correction_applied": correction_applied,
                    "artifacts_before": len(snap_before),
                    "artifacts_after": len(snap_after),
                    "transcript": transcript}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    if sim_turn:
        (run_dir / "simulator_turn.md").write_text(sim_turn["text"], encoding="utf-8")

    # The agent's sandbox sits outside the run folder (so it cannot clobber our
    # bookkeeping), which made its output hard to find. Copy whatever it produced
    # back in so one run directory is self-contained for grading.
    artifact_dir = ""
    sandbox = getattr(driver, "sandbox_for", lambda _s: None)(session)
    if sandbox and Path(sandbox).exists():
        art = run_dir / "artifacts"
        art.mkdir(exist_ok=True)
        for p in sorted(Path(sandbox).rglob("*")):
            if not p.is_file() or p.name in ("last_stdout.txt", "last_stderr.txt"):
                continue
            dest = art / p.relative_to(sandbox)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(p, dest)
            except OSError:
                pass
        artifact_dir = str(art)

    # OpenRouter reports the actual dollars the call cost (usage.include), which
    # beats our estimate from list prices — use it when present. The turn
    # variables differ by arm, so collect whatever turns actually ran.
    _ls = locals()
    reported = 0.0
    for _name in ("out1", "out2", "out3"):
        _o = _ls.get(_name)
        if isinstance(_o, dict):
            try:
                reported += float((_o.get("usage") or {}).get("cost") or 0)
            except (TypeError, ValueError):
                pass
    if reported > 0:
        cost, cost_source = reported, "reported"
    else:
        cost = (t1_in + t2_in) * model.get("price_in", 0) / 1e6 \
            + (t1_out + t2_out) * model.get("price_out", 0) / 1e6
        cost_source = "estimated"

    return {
        "run_id": run_id, "model_id": model["id"], "label": model["label"],
        "item_id": item["id"], "category": item["category"], "arm": arm,
        "rep": entry["rep"], "asked_questions": int(asked),
        # See the comment above: these three are deliberately separate.
        "correction_applied": ("" if correction_applied is None else correction_applied),
        "simulator_ok": ("" if sim_turn is None else int(bool(sim_ok))),
        "simulator_attempts": (sim_turn.get("attempts", 0) if isinstance(sim_turn, dict) else 0),
        "wants_delivered": wants_delivered,
        "artifacts_changed": ("" if artifacts_changed is None else int(artifacts_changed)),
        "artifacts_written": len(snap_after),
        "input_tokens": t1_in + t2_in, "output_tokens": t1_out + t2_out,
        "cost_usd": round(cost, 5), "cost_source": cost_source,
        "elapsed_s": round(time.time() - t0, 1),
        "response_path": str(run_dir / "response.md"),
        "artifact_dir": artifact_dir,
        "rubric_max": max_rubric_points(item),
    }


# ---------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="show how opencode was resolved and the exact command")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel runs; 2 is a good default for an overnight job")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--models", default="", help="comma-separated model ids")
    ap.add_argument("--arms", default="", help="comma-separated, e.g. A,B")
    ap.add_argument("--items", default="", help="comma-separated item ids")
    ap.add_argument("--out", default="")
    ap.add_argument("--config", default="",
                    help="alternate config.json (e.g. config.go.json)")
    ap.add_argument("--resume", action="store_true",
                    help="continue an interrupted run: skip run_ids already in "
                         "<out>/manifest.csv and keep their rows")
    ap.add_argument("--budget", type=float, default=0.0,
                    help="stop cleanly once cumulative spend reaches this many "
                         "USD. --resume continues from there. 0 = no limit.")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config()

    if args.probe:
        from harness import OpenCodeDriver, _wrap_argv
        drv = get_driver(cfg)
        print(drv.describe())
        if isinstance(drv, OpenCodeDriver) and drv.binary:
            print("\nturn 1 argv (creates the session):")
            print("  ", drv.demo_argv("qwen3.7-plus", turn=1))
            print("turn 2 argv (continues it):")
            print("  ", drv.demo_argv("qwen3.7-plus", turn=2))
            print("\nsanity check: running the binary with --version ...")
            import subprocess as _sp
            try:
                p = _sp.run(_wrap_argv(drv.binary, ["--version"]), capture_output=True,
                            text=True, timeout=60)
                print(f"  exit={p.returncode}")
                print(f"  stdout: {(p.stdout or '').strip()[:200]}")
                if (p.stderr or "").strip():
                    print(f"  stderr: {p.stderr.strip()[:200]}   "
                          f"(npm shims are noisy here; ignore if exit=0)")
            except Exception as e:
                print(f"  FAILED to execute: {e}")
                print("  -> set \"binary\" to the real opencode executable, or "
                      "switch \"mode\" to \"gateway\".")
        return 0

    items = load_items(ITEMS_DIR)

    models = cfg["models"]
    if args.models:
        want = {s.strip() for s in args.models.split(",") if s.strip()}
        models = [m for m in models if m["id"] in want or m["label"] in want]
    if args.items:
        want = {s.strip() for s in args.items.split(",") if s.strip()}
        items = [i for i in items if i["id"] in want]
    # Derived from ARMS, not hardcoded: a hardcoded list silently dropped arm E
    # when it was added. `enabled_arms` in config.json narrows what actually runs
    # while leaving the other arm definitions intact and re-enableable.
    arms = list(cfg.get("enabled_arms") or ARMS)
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arm(s) {unknown}; valid: {list(ARMS)}")
    if args.arms:
        arms = [a.strip().upper() for a in args.arms.split(",") if a.strip()]
        unknown = [a for a in arms if a not in ARMS]
        if unknown:
            raise SystemExit(f"unknown arm(s) {unknown}; valid: {list(ARMS)}")

    if args.smoke:
        models, items, arms = models[:2], items[:2], arms
        cfg = dict(cfg, reps={"light": 1, "agentic": 1})

    matrix = build_matrix(cfg, items, models, arms)
    if args.limit:
        matrix = matrix[: args.limit]

    total_est = 0.0
    print(f"models : {[m['id'] for m in models]}")
    print(f"items  : {[i['id'] for i in items]}")
    print(f"arms   : {arms}")
    print(f"runs   : {len(matrix)}")

    if args.dry_run:
        for e in matrix:
            print(f"  {e['item']['id']:<4} {e['model']['id']:<16} {e['arm']} r{e['rep']}")
        return 0

    if args.resume:
        if args.out:
            out_root = Path(args.out)
        else:
            base = ROOT / "runs"
            cands = sorted(d for d in base.iterdir() if d.is_dir()) if base.is_dir() else []
            if not cands:
                raise SystemExit("nothing to resume: no runs/ directory found")
            out_root = cands[-1]
        if not out_root.is_dir():
            raise SystemExit(f"--resume: {out_root} does not exist")
        print(f"resuming into {out_root}")
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_root = Path(args.out) if args.out else ROOT / "runs" / stamp
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "config.used.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    os.environ["PILOT_RUN_ROOT"] = str(out_root)
    driver = get_driver(cfg)
    sim = Simulator(driver, model=cfg["simulator"]["id"],
                    protocol=cfg["simulator"].get("protocol", "chat"),
                    temperature=cfg["simulator"].get("temperature", 0.3),
                    # MUST be forwarded. Simulator.__init__ defaults to 400 and
                    # a reasoning-first simulator spends that on thinking and
                    # returns EMPTY content -- which is precisely the 42%-silent
                    # failure this whole block exists to prevent. Before this
                    # line the config's max_tokens: 25000 was read, commented on,
                    # and never used.
                    max_tokens=cfg["simulator"].get("max_tokens", 25000),
                    session_prefix=cfg["simulator"].get("session_prefix", "sim"))

    rows, failures = [], []
    lock = threading.Lock()

    manifest_path = out_root / "manifest.csv"
    if args.resume and manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        done_ids = {r["run_id"] for r in rows}
        total_est = sum(float(r.get("cost_usd") or 0) for r in rows)
        before = len(matrix)
        matrix = [e for e in matrix if run_id_for(e) not in done_ids]
        print(f"resume: {len(done_ids)} runs already recorded, {len(matrix)} to go "
              f"(was {before})")
        if not matrix:
            print("nothing left to do.")
            return 0

    def _mk_tag(n, entry):
        return f"[{n}/{len(matrix)}] {entry['item']['id']} {entry['model']['id']} {entry['arm']} r{entry['rep']}"

    def _record(n, entry):
        """Run one cell and flush the manifest. Thread-safe bookkeeping."""
        nonlocal total_est
        tag = _mk_tag(n, entry)
        try:
            row = run_one(driver, sim, cfg, entry, out_root)
            with lock:
                rows.append(row)
                total_est += row["cost_usd"]
                # Flush every run, not every 10: otherwise a short run (or a
                # Ctrl+C) leaves no manifest at all and the batch looks lost.
                _write_manifest(out_root, rows)
                spent = total_est
            print(f"{tag}  ok  {row['input_tokens']}in/{row['output_tokens']}out  "
                  f"${row['cost_usd']:.4f}  asked={row['asked_questions']}", flush=True)
            return spent
        except Exception as e:                       # keep going, log it
            with lock:
                failures.append({"tag": tag, "error": str(e)})
            print(f"{tag}  FAILED: {e}", flush=True)
            return None

    workers = max(1, int(args.workers))
    if workers > 1:
        # Parallelism is what makes a ~10h serial job survivable overnight.
        # Each run has its own session/sandbox/run_dir, so cells are independent;
        # only the manifest bookkeeping takes the lock.
        print(f"workers: {workers}")
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_record, n, e) for n, e in enumerate(matrix, 1)]
            for f in as_completed(futs):
                spent = f.result()
                if args.budget and spent is not None and spent >= args.budget:
                    print(f"\nBUDGET STOP: ${spent:.2f} spent of the "
                          f"${args.budget:.2f} limit -- cancelling the rest.")
                    for other in futs:
                        other.cancel()
                    break
    else:
        for n, entry in enumerate(matrix, 1):
            spent = _record(n, entry)
            # Hard spending brake. Token cost per run is genuinely unpredictable
            # (the tool loop dominates), so an unattended batch needs a stop.
            # --resume continues from the same manifest.
            if args.budget and spent is not None and spent >= args.budget:
                print(f"\nBUDGET STOP: ${total_est:.2f} spent of the "
                      f"${args.budget:.2f} limit after {len(rows)} runs.")
                print("continue later with:  python src/run.py --resume --budget "
                      f"{args.budget:g}")
                break
        if len(rows) and len(rows) % 10 == 0:
            print(f"    ...running total ${total_est:.2f}")

    _write_manifest(out_root, rows)
    (out_root / "failures.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    print(f"\ndone: {len(rows)} ok, {len(failures)} failed, ${total_est:.2f} spent")
    print(f"outputs in {out_root}")
    # Quoted: the folder name may contain spaces (e.g. "pilot-harness (5)"), and
    # an unquoted path makes argparse split it and fail with "unrecognized arguments".
    print(f"next: python src/report.py --runs \"{out_root}\"")
    return 0 if not failures else 1


def _write_manifest(out_root: Path, rows: list[dict]) -> None:
    if not rows:
        return
    # Union of columns, not rows[0]'s keys: a resumed run may carry rows written
    # by an older build with fewer fields, and those rows must not be dropped.
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with (out_root / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
