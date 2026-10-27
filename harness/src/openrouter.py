"""OpenRouter driver — one API key, one endpoint, every model.

Why OpenRouter instead of six provider sign-ups:
  * one key, one bill, and `usage.include` returns the ACTUAL dollars a run
    cost — so manifest.csv can report money spent rather than our estimate
  * `GET /models` is public, so every slug can be verified (and priced) before
    the study runs. Nothing here is guessed.

Same contract as OpenCodeDriver / GatewayDriver, so run.py and simulator.py
are unchanged:

    complete(protocol, model, messages, system, temperature, max_tokens, session)
        -> {"text", "thinking", "usage", "stop_reason", "raw"}

Tool use is looped INSIDE complete(), the way `opencode run` does it, so an
agentic item runs to completion in a single call. The sandbox is per-session,
and sandbox_for() hands the run folder a path to copy artefacts out of —
keeping parity with the OpenCode mode.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from gateway import load_env_file

DEFAULT_BASE = "https://openrouter.ai/api/v1"
USER_AGENT = os.environ.get("PILOT_USER_AGENT", "pilot-harness/1.0")

# Deliberately minimal: enough to read the task workspace and write an
# artefact, and nothing that can shell out. Keeps the agentic arm bounded
# and reproducible across models.
TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files under a path in your working directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string",
                             "description": "Relative path; '.' is the root."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from your working directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file in your working directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path."},
                    "content": {"type": "string", "description": "Full file contents."}
                },
                "required": ["path", "content"],
            },
        },
    },
]


class OpenRouterError(RuntimeError):
    pass


def probe_models(slugs: list[str]) -> list[dict]:
    """Verify slugs against the live /models catalogue and return their prices.

    Public endpoint, no key needed. This is the anti-hallucination step for
    model selection: a slug that is not here does not exist.
    """
    req = urllib.request.Request(
        DEFAULT_BASE + "/models",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        catalogue = json.loads(r.read()).get("data", [])
    by_id = {m.get("id"): m for m in catalogue}
    out = []
    for slug in slugs:
        m = by_id.get(slug)
        if not m:
            out.append({"slug": slug, "found": False, "price_in": None,
                        "price_out": None, "context": None})
            continue
        p = m.get("pricing") or {}
        # /models reports USD per TOKEN; we store USD per MTok.
        try:
            pin = float(p.get("prompt", 0)) * 1e6
            pout = float(p.get("completion", 0)) * 1e6
        except (TypeError, ValueError):
            pin = pout = None
        out.append({"slug": slug, "found": True, "price_in": pin,
                    "price_out": pout, "context": m.get("context_length"),
                    "name": m.get("name")})
    return out


class OpenRouterDriver:
    engine = "openrouter"

    def __init__(self, cfg: dict):
        oc = cfg.get("openrouter", {})
        load_env_file("~/.hermes/.env", "~/.env", ".env")
        self.key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self.key:
            raise OpenRouterError(
                "OPENROUTER_API_KEY is not set. Put it in ~/.hermes/.env, ~/.env "
                "or ./.env (KEY=VALUE), or export it. Get one at "
                "https://openrouter.ai/settings/keys")
        self.base = (oc.get("base") or DEFAULT_BASE).rstrip("/")
        self.timeout = int(oc.get("timeout_s", 600))
        self.max_tool_turns = int(oc.get("max_tool_turns", 40))
        self.max_file_chars = int(oc.get("max_file_chars", 24000))
        self.sandboxes: dict[str, Path] = {}
        root = os.environ.get("PILOT_RUN_ROOT", ".")
        self._root = Path(root)

    # ------------------------------------------------------------- identity
    def cli_model(self, model) -> str:
        from harness import _as_model
        return _as_model(model).get("or_slug") or _as_model(model)["id"]

    def sandbox_for(self, session: str) -> Path | None:
        return self.sandboxes.get(session)

    def describe(self) -> list[str]:
        return [
            f"engine            : {self.engine}",
            f"base              : {self.base}",
            f"timeout_s         : {self.timeout}",
            f"max_tool_turns    : {self.max_tool_turns}",
            f"api key           : {'set (' + self.key[:6] + '...)' if self.key else 'MISSING'}",
        ]

    # ---------------------------------------------------------------- tools
    def _sandbox(self, session: str) -> Path:
        if session not in self.sandboxes:
            d = self._root / "_openrouter" / (session or "default")
            d.mkdir(parents=True, exist_ok=True)
            self.sandboxes[session] = d
        return self.sandboxes[session]

    def _resolve(self, session: str, rel: str) -> Path:
        """Resolve a model-supplied path, refusing anything outside the sandbox."""
        base = self._sandbox(session).resolve()
        target = (base / (rel or ".")).resolve()
        if target != base and base not in target.parents:
            raise OpenRouterError(f"path escapes the working directory: {rel!r}")
        return target

    def _run_tool(self, session: str, name: str, args: dict) -> str:
        try:
            if name == "list_dir":
                p = self._resolve(session, args.get("path", "."))
                if not p.exists():
                    return f"error: no such directory: {args.get('path')}"
                return "\n".join(sorted(
                    (c.name + "/" if c.is_dir() else c.name) for c in p.iterdir())) or "(empty)"
            if name == "read_file":
                p = self._resolve(session, args["path"])
                if not p.is_file():
                    return f"error: no such file: {args['path']}"
                txt = p.read_text(encoding="utf-8", errors="replace")
                if len(txt) > self.max_file_chars:
                    txt = txt[:self.max_file_chars] + "\n...[truncated]"
                return txt
            if name == "write_file":
                p = self._resolve(session, args["path"])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(args.get("content", ""), encoding="utf-8")
                return f"wrote {len(args.get('content',''))} chars to {args['path']}"
            return f"error: unknown tool {name}"
        except OpenRouterError as e:
            return f"error: {e}"
        except (OSError, KeyError) as e:
            return f"error: {e}"

    # ----------------------------------------------------------------- http
    def _post(self, payload: dict) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer " + self.key,
            "User-Agent": USER_AGENT,
            # OpenRouter asks for these; they label traffic in your dashboard.
            "HTTP-Referer": "https://github.com/pilot-harness",
            "X-Title": "LLM interview-vs-hallucination pilot",
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(self.base + "/chat/completions",
                                     data=body, headers=headers)
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:600]
                last = f"HTTP {e.code}: {detail}"
                if e.code in (408, 429, 500, 502, 503, 529) and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise OpenRouterError(last)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = f"network error: {e}"
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise OpenRouterError(last)
        raise OpenRouterError(last or "unreachable")

    # -------------------------------------------------------------- complete
    def complete(self, protocol, model, messages, system=None, temperature=0.2,
                 max_tokens=4000, session=None, use_tools=True) -> dict:
        """Run one conversational turn, looping tool calls to completion."""
        from harness import _as_model
        slug = self.cli_model(model)
        session = session or "default"

        convo: list[dict] = []
        if system:
            convo.append({"role": "system", "content": system})
        convo.extend(messages)

        payload = {
            "model": slug,
            "messages": convo,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Ask OpenRouter to report the real cost of the call back to us.
            "usage": {"include": True},
        }
        if use_tools:
            payload["tools"] = TOOL_SCHEMA
            payload["tool_choice"] = "auto"

        usage = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        thinking_bits: list[str] = []
        text = ""
        raws: list[dict] = []
        stop = "completed"

        for turn in range(self.max_tool_turns + 1):
            data = self._post(payload)
            raws.append(data)

            u = data.get("usage") or {}
            usage["input_tokens"] += int(u.get("prompt_tokens", 0))
            usage["output_tokens"] += int(u.get("completion_tokens", 0))
            try:
                usage["cost"] += float(u.get("cost", 0) or 0)
            except (TypeError, ValueError):
                pass

            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            stop = choice.get("finish_reason") or stop

            rc = msg.get("reasoning_content") or msg.get("reasoning")
            if rc:
                thinking_bits.append(rc if isinstance(rc, str) else json.dumps(rc))
            if msg.get("content"):
                text = msg["content"] if isinstance(msg["content"], str) \
                    else json.dumps(msg["content"])

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls or not use_tools or turn >= self.max_tool_turns:
                break

            # Echo the assistant turn back verbatim, then feed tool results.
            convo.append({k: v for k, v in msg.items() if v is not None})
            for tc in tool_calls:
                fn = (tc.get("function") or {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._run_tool(session, fn.get("name", ""), args)
                convo.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "content": result,
                })
            payload["messages"] = convo

        if turn >= self.max_tool_turns and not text:
            stop = "tool_turn_limit"
            text = "(stopped: tool turn limit reached)"

        return {
            "text": text,
            "thinking": "\n".join(thinking_bits).strip(),
            "usage": usage,
            "stop_reason": stop,
            "raw": raws if len(raws) > 1 else (raws[0] if raws else {}),
        }
