"""Capability fingerprint.

Run BEFORE and AFTER the study window, on every model. Two purposes:

  1. Drift detector — the run window spans 2-4 weeks because of Go's rate caps,
     and models get silently updated underneath you.
  2. Your own capability number — the gateway exposes no reasoning-effort tier,
     so the Artificial Analysis index may not describe what you actually served.
     If the AA mapping looks shaky, this is the H4 x-axis instead.

  python src/fingerprint.py                 # all models in config.json
  python src/fingerprint.py --out fp_before.json
  python src/fingerprint.py --compare fp_before.json fp_after.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from gateway import Gateway, usage_tokens   # noqa: E402

# Fixed expected answers. Kept trivial and objective on purpose: we are measuring
# consistency and willingness to answer, not knowledge difficulty.
EXPECTED = {
    "What is the capital of Australia? Answer with the city name only.": "canberra",
    "In what year did the Berlin Wall fall? Answer with the year only.": "1989",
    "What is the derivative of x^3 with respect to x? Answer with the expression only.": "3x^2",
    "Who wrote 'Pride and Prejudice'? Answer with the surname only.": "austen",
    "What is the chemical symbol for gold? Answer with the symbol only.": "au",
}


def norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def run_fingerprint(gw: Gateway, cfg: dict) -> dict:
    out = {"created": datetime.now(timezone.utc).isoformat(),
           "temperature": cfg.get("temperature", 0.2), "models": {}}
    for m in cfg["models"]:
        results, tokens = [], 0
        for q, want in EXPECTED.items():
            r = gw.complete(protocol=m["protocol"], model=m["id"],
                            messages=[{"role": "user", "content": q}],
                            temperature=cfg.get("temperature", 0.2),
                            max_tokens=200,
                            session="fingerprint-" + m["id"])
            got = norm(r["text"])
            tin, tout = usage_tokens(r["usage"])
            tokens += tin + tout
            results.append({"q": q, "expected": want, "raw": r["text"][:200],
                            "match": norm(want) in got})
        score = sum(1 for x in results if x["match"]) / len(results)
        out["models"][m["id"]] = {"label": m["label"], "aa_index": m.get("aa_index"),
                                  "effort_tier": m.get("effort_tier", "unknown"),
                                  "fingerprint_score": score,
                                  "answer_lengths": [len(x["raw"]) for x in results],
                                  "tokens": tokens, "results": results}
        print(f"  {m['id']:<16} fingerprint={score:.2f}  tokens={tokens}")
    return out


def compare(a: dict, b: dict) -> None:
    print(f"before: {a.get('created')}\nafter:  {b.get('created')}\n")
    for mid, mb in b["models"].items():
        ma = a["models"].get(mid)
        if not ma:
            print(f"  {mid:<16} MISSING in before")
            continue
        drift = ma["fingerprint_score"] != mb["fingerprint_score"]
        print(f"  {mid:<16} {ma['fingerprint_score']:.2f} -> {mb['fingerprint_score']:.2f}"
              f"  {'DRIFT' if drift else 'stable'}")
        if drift:
            for x, y in zip(ma["results"], mb["results"]):
                if x["match"] != y["match"]:
                    print(f"      changed: {x['q'][:60]}  {x['raw'][:40]!r} -> {y['raw'][:40]!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = ap.parse_args()

    if args.compare:
        compare(json.loads(Path(args.compare[0]).read_text()),
                json.loads(Path(args.compare[1]).read_text()))
        return 0

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    gw = Gateway()
    data = run_fingerprint(gw, cfg)
    dest = Path(args.out) if args.out else ROOT / "runs" / "fingerprint.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwritten to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
