"""Two interchangeable drivers behind one interface.

mode = "opencode"   -> drives the real OpenCode agent (CLI) as the harness.
                       The model gets OpenCode's system prompt and real fs/shell
                       tools, and actually writes files and runs commands. This is
                       the uniform harness the study calls for.
mode = "gateway"    -> calls the OpenCode Go REST gateway directly as a plain LLM.
                       No tools. Useful as a fallback if the CLI fights you.

Both expose the same method, so run.py and simulator.py do not care which is in use:

    complete(protocol, model, messages, system, temperature, max_tokens, session)
        -> {"text", "thinking", "usage", "stop_reason", "raw"}

>>> The OpenCode CLI flags below are the ones the `opencode run` interface is
>>> documented with. They are NOT verified on your machine. If a flag is wrong,
>>> `opencode run --help` is the source of truth and `config.json ->
>>> opencode.command` is the ONE place to fix it.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gateway import Gateway, GatewayError, usage_tokens

MODE_OPencode = "opencode"
MODE_GATEWAY = "gateway"


# ============================================================ opencode driver
WIN_SHIMS = (".cmd", ".bat", ".ps1")


def _resolve_opencode(name: str) -> tuple[str | None, str]:
    """Find a runnable opencode binary. Prefer a real executable over a Windows shim.

    On Windows an npm install puts `opencode.cmd` and `opencode.ps1` on PATH, and
    `subprocess.run(["opencode", ...])` raises WinError 2 / WinError 193 because
    CreateProcess cannot execute those shims. The native .exe normally sits next
    to them, so look for it before falling back to the shim.
    """
    expanded = str(Path(name).expanduser())
    if Path(expanded).is_file():
        return expanded, "explicit path from config"

    hit = shutil.which(name)
    if hit and not hit.lower().endswith(WIN_SHIMS):
        return hit, "PATH lookup (native executable)"

    if hit:  # a shim — hunt for the real binary beside it
        d = Path(hit).parent
        for cand in sorted(d.glob("opencode*.exe")):
            return str(cand), f"native exe beside the shim in {d}"
        # npm keeps the real binary under node_modules, not in the bin dir, so a
        # bare glob there misses it. Look in the usual places relative to the shim.
        for rel in ("node_modules/opencode-ai", "node_modules/opencode-ai/bin",
                    "node_modules/opencode-ai/dist",
                    "node_modules/opencode-ai/node_modules/.bin",
                    "../node_modules/opencode-ai", "../node_modules/opencode-ai/bin"):
            base = d / rel
            if base.is_dir():
                for cand in sorted(base.glob("opencode*.exe")):
                    return str(cand), f"native exe in {base}"
        return hit, f"PATH lookup (Windows shim {Path(hit).suffix})"

    if sys.platform == "win32":
        for ext in (".exe", ".cmd", ".bat", ".ps1"):
            cand = shutil.which(name + ext)
            if cand:
                return cand, f"PATH lookup ({ext})"
    return None, "not found on PATH"


def _wrap_argv(binary: str, args: list[str]) -> list[str]:
    """Wrap a Windows shim so CreateProcess can actually run it."""
    low = binary.lower()
    if low.endswith(".ps1"):
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", binary] + args
    if low.endswith(".cmd") or low.endswith(".bat"):
        return ["cmd.exe", "/c", binary] + args
    return [binary] + args


def _shell_safe(binary: str) -> bool:
    """True if the invocation goes through cmd.exe (which cannot take newlines)."""
    return binary.lower().endswith((".cmd", ".bat"))


class OpenCodeDriver:
    """Drives `opencode run` in a per-run working directory.

    Multi-turn is handled by OpenCode's own session state: we pass `-s <session>`
    and only send the NEW user message each turn. History lives in the session,
    which is exactly how a real agent conversation works.

    Consequence worth knowing: OpenCode injects its own "you are a coding agent"
    system prompt and gives the model real tools. That is the point of using it as
    the harness, and it is also why results generalise to agentic settings rather
    than bare chat. See README limitations.
    """

    def __init__(self, cfg: dict):
        oc = cfg.get("opencode", {})
        self.configured_binary = oc.get("binary", "opencode")
        self.binary, self.binary_how = _resolve_opencode(self.configured_binary)
        # `opencode run --help` (verified): -s/--session = "session id to continue",
        # i.e. it requires an EXISTING session. Passing a made-up id is exactly what
        # produced "session not found". So: turn 1 creates a session (no flag),
        # turn 2 continues the most recent one in that run's own directory (-c).
        self.command_new = oc.get("command_new") or [
            "run", "-m", "{model}", "--dir", "{workdir}",
            "--format", "json", "--thinking", "--auto", "{prompt}",
        ]
        self.command_continue = oc.get("command_continue") or [
            "run", "--continue", "--dir", "{workdir}",
            "--format", "json", "--thinking", "--auto", "{prompt}",
        ]
        self.model_prefix = oc.get("model_prefix", "opencode-go/")
        self.timeout = int(oc.get("timeout_s", 1800))
        self.stall_timeout = float(oc.get("stall_timeout_s", 300))
        self.json_output = bool(oc.get("json_output", True))
        self.auto_approve = bool(oc.get("auto_approve", True))
        self._session_dirs: dict[str, Path] = {}
        self._started: set[str] = set()

    def describe(self) -> str:
        """Human-readable resolution report — used by `run.py --probe`."""
        lines = [
            f"configured binary : {self.configured_binary!r}",
            f"resolved binary   : {self.binary!r}",
            f"resolved via      : {self.binary_how}",
            f"platform          : {sys.platform}",
            f"model prefix      : {self.model_prefix!r}",
            f"auto-approve      : {self.auto_approve}",
            f"turn 1 command    : {self.command_new}",
            f"turn 2+ command   : {self.command_continue}",
        ]
        if self.binary is None:
            lines.append(
                "\nNOT FOUND. Fix by either:\n"
                "  (a) set \"binary\" in config.json to the full path of the real\n"
                "      opencode executable (on Windows look in\n"
                "      %APPDATA%\\npm\\ or ...\\node_modules\\opencode-ai\\ for opencode.exe), or\n"
                "  (b) set \"mode\": \"gateway\" in config.json to use the verified REST path.")
        elif _shell_safe(self.binary):
            lines.append(
                "\nWARNING: this is a .cmd/.bat shim, so the prompt must go through\n"
                "cmd.exe and will be flattened to a single line. Prefer a native\n"
                "opencode.exe if one exists.")
        return "\n".join(lines)

    def demo_argv(self, model_id: str, turn: int = 1) -> list[str]:
        tmpl = self.command_new if turn == 1 else self.command_continue
        args = [tok.format(model=self.cli_model(model_id), session="probe",
                           workdir=".", prompt="<PROMPT>")
                for tok in tmpl]
        return _wrap_argv(self.binary or "opencode", args)

    def cli_model(self, model) -> str:
        model = _as_model(model)
        return model.get("cli_model") or (self.model_prefix + model["id"])

    def sandbox_for(self, session: str) -> Path | None:
        """The directory the agent actually wrote files into."""
        return self._session_dirs.get(session)

    def _workdir(self, session: str) -> Path:
        if session not in self._session_dirs:
            d = Path(os.environ.get("PILOT_RUN_ROOT", ".")) / "_opencode" / session
            d.mkdir(parents=True, exist_ok=True)
            self._session_dirs[session] = d
        return self._session_dirs[session]

    def complete(self, protocol, model, messages, system=None, temperature=0.2,
                 max_tokens=4000, session=None) -> dict:
        model = _as_model(model)
        session = session or ("pilot-" + str(time.time_ns()))
        if self.binary is None:
            raise GatewayError(
                "could not find a runnable opencode binary.\n" + self.describe())

        # Only the newest user turn is sent; the session holds the history.
        prompt_parts = []
        if system:
            prompt_parts.append(system)
        prompt_parts.append(messages[-1]["content"])
        prompt = "\n\n".join(prompt_parts)

        # cmd.exe treats newlines as command separators, so a shim invocation has
        # to carry the prompt on one line. A native binary keeps it intact.
        flattened = False
        if _shell_safe(self.binary):
            prompt = " ".join(prompt.split())
            flattened = True

        workdir = self._workdir(session)
        first_turn = session not in self._started
        tmpl = self.command_new if first_turn else self.command_continue
        args = [tok.format(model=self.cli_model(model), session=session,
                           workdir=str(workdir), prompt=prompt)
                for tok in tmpl]
        # --variant pins the reasoning effort, which the REST gateway never told
        # us. This is what makes the effort tier a controlled variable instead of
        # an unknown. Set "variant" per model in config.json (e.g. "max", "high").
        variant = model.get("variant")
        if variant:
            args += ["--variant", str(variant)]
        argv = _wrap_argv(self.binary, args)

        t0 = time.time()
        out_path = workdir / "last_stdout.txt"
        err_path = workdir / "last_stderr.txt"
        env = {**os.environ, "PILOT_RUN_SESSION": session}
        print(f"    -> {shlex.join(argv[:3])} ... {session}", flush=True)
        try:
            with out_path.open("w", encoding="utf-8") as out_f, \
                    err_path.open("w", encoding="utf-8") as err_f:
                # stdin MUST be devnull: an inherited terminal lets opencode sit
                # waiting on input (trust/permission/confirmation) indefinitely,
                # which looks exactly like a hang with no CPU and no API calls.
                proc = subprocess.Popen(argv, cwd=str(workdir), stdin=subprocess.DEVNULL,
                                        stdout=out_f, stderr=err_f, text=True, env=env)
                last_beat = 0.0
                last_size = -1
                last_growth = time.time()
                while proc.poll() is None:
                    time.sleep(2.0)
                    now = time.time()
                    elapsed = now - t0
                    if elapsed > self.timeout:
                        proc.kill(); proc.wait()
                        raise GatewayError(
                            f"opencode hit the {self.timeout:.0f}s wall-clock limit on "
                            f"{session}; partial output kept in {out_path}")

                    try:
                        size = out_path.stat().st_size
                    except OSError:
                        size = 0
                    if size != last_size:
                        last_size, last_growth = size, now

                    stalled_for = now - last_growth
                    if stalled_for > self.stall_timeout:
                        proc.kill(); proc.wait()
                        raise GatewayError(
                            f"opencode produced NO new output for "
                            f"{stalled_for:.0f}s on {session} (stall limit "
                            f"{self.stall_timeout:.0f}s) - killed. Partial output in "
                            f"{out_path}. This usually means it is waiting on stdin or a "
                            f"permission prompt; stdin is now forced to DEVNULL, so if "
                            f"this recurs run with mode='gateway' or add --print-logs.")

                    if elapsed - last_beat >= 15.0:
                        last_beat = elapsed
                        print(f"      .. {elapsed:5.0f}s  {self._peek_activity(out_path)}",
                              flush=True)
        except FileNotFoundError as e:
            raise GatewayError(
                f"opencode binary not found ({self.binary!r}): {e}. "
                f"Install it or set opencode.binary in config.json.") from e

        stdout_text = out_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = err_path.read_text(encoding="utf-8", errors="replace")

        if proc.returncode != 0:
            detail = (self._error_from_output(stdout_text)
                      or stderr_text.strip()[:500]
                      or stdout_text.strip()[:500] or "(no output)")
            raise GatewayError(
                f"opencode exited {proc.returncode} on session {session}\n"
                f"  argv: {shlex.join(argv[:6])} ...\n"
                f"  error: {detail}")

        # The CLI reports failures as {type:error} on stdout even when the exit
        # code is 0. Catch that so a broken run never looks like an empty answer.
        cli_error = self._error_from_output(stdout_text)
        if cli_error:
            raise GatewayError(f"opencode reported an error: {cli_error}")

        self._started.add(session)
        text, thinking, usage = self._parse(stdout_text)
        if flattened:
            print("      !! prompt was flattened to one line because the binary is a "
                  "cmd.exe shim - point opencode.binary at a real opencode.exe to keep "
                  "the prompt structure intact", flush=True)
        if not text.strip():
            print("      !! no text extracted from the CLI output - check "
                  f"{out_path} and adjust the parser", flush=True)
        return {
            "text": text,
            "thinking": thinking,
            "stop_reason": "end_turn",
            "usage": usage,
            "elapsed_s": round(time.time() - t0, 1),
            "prompt_flattened": flattened,
            "raw": {"role": "assistant", "content": text},
        }

    @staticmethod
    def _peek_activity(path: Path) -> str:
        """Read the tail of the live output file so we can say what it is doing."""
        try:
            chunk = path.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            return "(no output yet)"
        if not chunk.strip():
            return "(waiting for first event)"
        kinds: list[str] = []
        for line in chunk.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(d, dict):
                t = d.get("type")
                if t:
                    kinds.append(str(t))
                if d.get("tool"):
                    kinds.append(f"tool={d['tool']}")
        tail = kinds[-3:] if kinds else ["<unparsed output>"]
        return f"events: {' > '.join(tail)}   ({len(chunk)} chars buffered)"

    @staticmethod
    def _error_from_output(stdout: str) -> str:
        """Pull {type:"error"} objects out of --format json output.

        Observed shape: {"type":"error","sessionID":"ses_...","error":
        {"name":"UnknownError","data":{"message":"...","ref":"err_..."}}}
        """
        for line in (stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(d, dict) and d.get("type") == "error":
                err = d.get("error") or {}
                data = err.get("data") or {}
                msg = data.get("message") or err.get("message") or str(err)
                name = err.get("name") or "Error"
                ref = data.get("ref") or ""
                return f"{name}: {msg}" + (f" (ref {ref})" if ref else "")
        return ""

    def _parse(self, stdout: str) -> tuple[str, str, dict]:
        """Extract text/thinking/usage from `--format json` output.

        The CLI emits *events*, possibly as JSONL and possibly streamed with the
        same part repeated as it grows. We key parts by their id and keep the last
        version of each, then join in first-seen order. Falls back to raw text if
        nothing parses, so a response is never silently lost.
        """
        s = stdout.strip()
        if not s:
            return "", "", {}

        blobs: list = []
        try:
            d = json.loads(s)
            blobs.append(d)
        except json.JSONDecodeError:
            for line in s.splitlines():
                line = line.strip()
                if line.startswith("{") or line.startswith("["):
                    try:
                        blobs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        if not blobs:
            return s, "", {}

        parts: dict[str, tuple[str, str]] = {}
        order: list[str] = []
        usage: dict = {}
        cost = 0.0

        def walk(o):
            nonlocal usage, cost
            if isinstance(o, dict):
                t = str(o.get("type") or "")
                key = o.get("id") or o.get("partID") or o.get("partId")
                if t in ("text", "output_text") and isinstance(o.get("text"), str):
                    ident = key or f"text-{len(order)}"
                elif t in ("thinking", "reasoning") and (
                        isinstance(o.get("thinking"), str) or isinstance(o.get("text"), str)):
                    ident = key or f"think-{len(order)}"
                else:
                    ident = None
                if ident is not None:
                    body = o.get("text") or o.get("thinking") or ""
                    if ident not in parts:
                        order.append(ident)
                    parts[ident] = (t, body)

                # Usage shows up under several names depending on the event
                # ("usage", "tokens", per-step tallies). Take whatever we can find
                # instead of silently reporting 0 tokens and $0.00.
                for k in ("usage", "tokens", "tokenUsage", "token_usage"):
                    v = o.get(k)
                    if isinstance(v, dict):
                        usage.update({kk: vv for kk, vv in v.items()
                                      if isinstance(vv, (int, float))})
                for k in ("cost", "costUSD", "totalCost"):
                    v = o.get(k)
                    if isinstance(v, (int, float)):
                        cost = max(cost, float(v))
                for kk in ("input", "output", "reasoning", "prompt", "completion",
                           "input_tokens", "output_tokens", "prompt_tokens",
                           "completion_tokens", "cache_read", "cache_write"):
                    v = o.get(kk)
                    if isinstance(v, (int, float)) and kk not in usage:
                        usage[kk] = v

                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        for b in blobs:
            walk(b)

        if cost:
            usage.setdefault("cost", cost)

        text, thinking = [], []
        for ident in order:
            t, body = parts[ident]
            (thinking if t in ("thinking", "reasoning") else text).append(body)
        joined_text = "".join(text).strip()
        if not joined_text:
            return s, "".join(thinking).strip(), usage
        return joined_text, "".join(thinking).strip(), usage


def _separate_thinking(text, thinking):
    """Pull a leaked reasoning block out of the visible answer.

    Some models put their reasoning in `content` behind a  <think>  tag instead
    of the reasoning field. That pollutes grading: in the 2026-09-29 run 17% of
    assistant turns opened with raw chain-of-thought. Move it where it belongs.
    Handles both <think>...</think> and an unterminated <think> prefix.
    """
    t = (text or "").strip()
    if not t.startswith("<think>"):
        return text or "", thinking or ""
    body = t[len("<think>"):]
    end = body.find("</think>")
    if end == -1:
        return "", (thinking + "\n" + body).strip()
    inner, rest = body[:end].strip(), body[end + len("</think>"):].strip()
    return rest, (thinking + "\n" + inner).strip()


from tools import (ToolSandbox, extract_calls, parse_args, result_message,  # noqa: E402
                   schema_chat, schema_responses)


# ============================================================= gateway driver
class GatewayDriver:
    """OpenCode Go REST gateway, now with the same tool set as the OpenRouter driver.

    Tools were the missing piece: T6 (agentic) asks the model to inspect a
    workspace, and a plain chat call cannot see it — the model correctly reported
    "no file came through". Tool calling is supported on both protocols, but with
    DIFFERENT schema shapes (verified live): /chat/completions wants the nested
    `function` form, /responses wants it flat. src/tools.py holds both.

    Protocol per model matters: see src/gateway.py.
    """

    def __init__(self, cfg: dict):
        self.gw = Gateway()
        g = cfg.get("gateway", {})
        self.max_tool_turns = int(g.get("max_tool_turns", 40))
        root = Path(os.environ.get("PILOT_RUN_ROOT", ".")) / "_go"
        self.sandbox = ToolSandbox(root, int(g.get("max_file_chars", 24000)))

    def cli_model(self, model) -> str:
        model = _as_model(model)
        return model["id"]

    def sandbox_for(self, session: str) -> Path | None:
        """Where the agent wrote files, so run.py can copy artefacts out."""
        return self.sandbox.for_session(session) if self.sandbox.dirs else None

    def describe(self) -> list[str]:
        return [f"engine            : opencode-go",
                f"base              : {self.gw.base}",
                f"max_tool_turns    : {self.max_tool_turns}"]

    # -------------------------------------------------------------- complete
    def complete(self, protocol, model, messages, system=None, temperature=0.2,
                 max_tokens=4000, session=None, use_tools=True) -> dict:
        model = _as_model(model)
        proto = (protocol or model.get("protocol") or "chat").lower()
        session = session or "default"

        if proto not in ("chat", "responses") or not use_tools:
            out = self.gw.complete(protocol=proto, model=model["id"],
                                   messages=messages, system=system,
                                   temperature=temperature, max_tokens=max_tokens,
                                   session=session)
            out["elapsed_s"] = None
            return out

        usage = {"input_tokens": 0, "output_tokens": 0}
        thinking_bits, text, stop = [], "", "completed"
        raws = []

        if proto == "chat":
            convo = ([{"role": "system", "content": system}] if system else []) + list(messages)
            payload = {"model": model["id"], "messages": convo,
                       "temperature": temperature, "max_tokens": max_tokens,
                       "tools": schema_chat(), "tool_choice": "auto"}
        else:
            convo = ([{"role": "system", "content": system}] if system else []) + list(messages)
            payload = {"model": model["id"], "input": convo,
                       "temperature": temperature, "max_output_tokens": max_tokens,
                       "tools": schema_responses()}
            # Some responses-protocol models reject temperature outright
            # ("Unsupported parameter: 'temperature' is not supported with this
            # model"). Honor a per-model flag up front rather than burning a
            # failed call; the retry below is the safety net for models we have
            # not flagged yet.
            if model.get("supports_temperature") is False:
                payload.pop("temperature", None)

        def _post(p):
            path = "/chat/completions" if proto == "chat" else "/responses"
            try:
                return self.gw._post(path, p, session)
            except Exception as e:
                msg = str(e)
                if "temperature" in msg.lower() and "not supported" in msg.lower():
                    # Self-heal: drop it and remember so later turns don't retry.
                    p.pop("temperature", None)
                    model["supports_temperature"] = False
                    return self.gw._post(path, p, session)
                raise

        for turn in range(self.max_tool_turns + 1):
            data = _post(payload)
            raws.append(data)
            u = data.get("usage") or {}
            usage["input_tokens"] += int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
            usage["output_tokens"] += int(u.get("completion_tokens") or u.get("output_tokens") or 0)

            if proto == "chat":
                ch = (data.get("choices") or [{}])[0]
                msg = ch.get("message") or {}
                stop = ch.get("finish_reason") or stop
                rc = msg.get("reasoning_content") or msg.get("reasoning")
                if rc:
                    thinking_bits.append(rc if isinstance(rc, str) else json.dumps(rc))
                if msg.get("content"):
                    text = msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"])
            else:
                stop = data.get("status") or stop
                for o in data.get("output") or []:
                    if o.get("type") == "reasoning":
                        for s in o.get("summary") or []:
                            if isinstance(s, dict) and s.get("text"):
                                thinking_bits.append(s["text"])
                    elif o.get("type") == "message":
                        for c in o.get("content") or []:
                            if c.get("text"):
                                text = c["text"]

            # --- tool calls ------------------------------------------------
            # Some models omit the tool_call id altogether. Feeding a result
            # back with an empty tool_call_id gets rejected with
            # "tool_call_id must not be empty", which kills the whole run.
            # So assign ids HERE, before the echo and the results, and make
            # both sides use the same values.
            if proto == "chat":
                # This gateway rejects "name" on messages ("not supported by
                # this endpoint"), so strip it. And a message that only carries
                # tool_calls comes back with content:null -- dropping that key
                # breaks gateway.py's m["content"], so force it to exist.
                echo = {k: v for k, v in msg.items()
                        if v is not None and k != "name"}
                echo.setdefault("content", "")
                fixed = []
                for i, tc in enumerate(echo.get("tool_calls") or []):
                    tc = dict(tc)
                    fn = dict(tc.get("function") or {})
                    if not fn.get("name"):
                        continue                    # nothing to call
                    fn.setdefault("arguments", "{}")
                    tc["function"] = fn
                    tc.setdefault("id", "")
                    if not tc["id"]:
                        tc["id"] = f"call_{turn}_{i}"
                    fixed.append(tc)
                calls = [{"id": tc["id"], "name": tc["function"]["name"],
                          "arguments": tc["function"].get("arguments", "{}")}
                         for tc in fixed]
                if not calls or turn >= self.max_tool_turns:
                    break
                echo["tool_calls"] = fixed
                convo.append(echo)
            else:
                # Responses API requires the function_call items echoed verbatim.
                raw_calls = [o for o in (data.get("output") or [])
                             if o.get("type") == "function_call"]
                calls = []
                for i, o in enumerate(raw_calls):
                    cid = o.get("call_id") or o.get("id") or f"call_{turn}_{i}"
                    calls.append({"id": cid, "name": o.get("name", ""),
                                  "arguments": o.get("arguments", "{}")})
                if not calls or turn >= self.max_tool_turns:
                    break
                for c in calls:
                    convo.append({"type": "function_call", "call_id": c["id"],
                                  "name": c["name"], "arguments": c["arguments"]})

            for c in calls:
                result = self.sandbox.run(session, c["name"], parse_args(c["arguments"]))
                convo.append(result_message(proto, c, result))
            payload["messages" if proto == "chat" else "input"] = convo

        text, joined = _separate_thinking(text, "\n".join(thinking_bits).strip())
        return {"text": text, "thinking": joined,
                "usage": usage, "stop_reason": stop,
                "raw": raws[0] if len(raws) == 1 else raws,
                "elapsed_s": None,
                # Hand the conversation back so run.py can elicit a summary
                # when the model did all its work silently and never spoke.
                "messages": convo}


def _as_model(model) -> dict:
    """Accept either a model dict from config.json or a bare id string."""
    return {"id": model} if isinstance(model, str) else model


def get_driver(cfg: dict):
    mode = (cfg.get("mode") or MODE_OPencode).lower()
    if mode == MODE_OPencode:
        return OpenCodeDriver(cfg)
    if mode == MODE_GATEWAY:
        if (cfg.get("engine") or "").lower() == "openrouter":
            from openrouter import OpenRouterDriver
            return OpenRouterDriver(cfg)
        return GatewayDriver(cfg)
    raise GatewayError(f"unknown mode {mode!r} (use 'opencode' or 'gateway')")


__all__ = ["get_driver", "OpenCodeDriver", "GatewayDriver",
           "MODE_OPencode", "MODE_GATEWAY", "usage_tokens", "GatewayError"]
