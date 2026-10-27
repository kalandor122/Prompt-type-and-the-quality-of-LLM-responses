"""OpenCode Go gateway client — protocol-aware.

Verified against the live gateway on 2026-09-27:

  model            /messages (Anthropic)   /chat/completions   /responses
  qwen3.7-plus            OK                     OK               -
  deepseek-v4-pro         OK                     OK               -
  glm-5.3-flash        ModelProtocolUnsupported   OK               -
  mimo-v2.6-pro        ModelProtocolUnsupported   OK               -
  gpt-6-luna          ModelProtocolUnsupported  ModelProtocolUnsupported  OK

Required headers on EVERY request:
  Authorization: Bearer <key>
  User-Agent: <our own name>          # a generic SDK/HTTP UA gets Cloudflare 1010
  x-opencode-session: <stable id>     # one per conversation; missing -> HTTP 400

Multi-turn works on all three protocols; assistant turns are echoed back in the
protocol's own shape. Reasoning models return thinking blocks (Anthropic
`thinking` / OpenAI `reasoning_content` / Responses `reasoning`); we echo them
back, which the gateway expects for reasoning models.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_BASE = os.environ.get("OPENCODE_GO_BASE", "https://opencode.ai/zen/go/v1")
USER_AGENT = os.environ.get("PILOT_USER_AGENT", "pilot-harness/1.0")

# Protocols we know how to speak.
PROT_CHAT = "chat"        # POST /chat/completions  (OpenAI shape)
PROT_RESPONSES = "responses"  # POST /responses       (OpenAI Responses shape)
PROT_MESSAGES = "messages"    # POST /messages        (Anthropic shape)


def load_env_file(*paths: str) -> list[str]:
    """Read KEY=VALUE lines into os.environ without overwriting real exports.

    The README promises the key can simply live in ~/.hermes/.env. Make that true
    instead of requiring an `export` first — otherwise the harness dies with
    "OPENCODE_GO_API_KEY is not set" on any machine that only has the file.
    """
    loaded = []
    for path in paths:
        try:
            text = Path(path).expanduser().read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
                loaded.append(key)
    return loaded


class GatewayError(RuntimeError):
    pass


class Gateway:
    def __init__(self, api_key: str | None = None, base: str = DEFAULT_BASE,
                 user_agent: str = USER_AGENT, timeout: int = 300):
        if api_key is None:
            load_env_file("~/.hermes/.env", "~/.env", ".env")
        self.key = api_key or os.environ.get("OPENCODE_GO_API_KEY")
        if not self.key:
            raise GatewayError(
                "OPENCODE_GO_API_KEY is not set. Checked the environment and "
                "~/.hermes/.env, ~/.env and ./.env. Put the key in one of those "
                "or export it.")
        self.base = base.rstrip("/")
        self.ua = user_agent
        self.timeout = timeout

    # ------------------------------------------------------------------ http
    def _post(self, path: str, payload: dict, session: str) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.ua,
            "x-opencode-session": session,
            "Authorization": "Bearer " + self.key,
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(self.base + path, data=body, headers=headers)

        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:600]
                last = f"HTTP {e.code} on {path}: {detail}"
                if e.code in (408, 429, 500, 502, 503, 529) and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise GatewayError(last)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = f"network error on {path}: {e}"
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise GatewayError(last)
        raise GatewayError(last or "unreachable")

    # -------------------------------------------------------------- protocol
    def complete(self, protocol: str, model: str, messages: list[dict],
                 system: str | None = None, temperature: float = 0.2,
                 max_tokens: int = 4000, session: str | None = None) -> dict:
        """Send a conversation. Returns a normalised dict plus `raw` for passback.

        `messages` is a list of {"role": "user"|"assistant", "content": str,
        "thinking": str (optional, assistant only)}.
        """
        session = session or ("pilot-" + uuid.uuid4().hex[:16])
        fn = {PROT_CHAT: self._chat, PROT_RESPONSES: self._responses,
              PROT_MESSAGES: self._messages}.get(protocol)
        if fn is None:
            raise GatewayError(f"unknown protocol: {protocol!r}")
        try:
            return fn(model, messages, system, temperature, max_tokens, session)
        except GatewayError as e:
            # Some models reject sampling params outright (e.g. gpt-6-luna on
            # /responses: "Unsupported parameter: 'temperature' is not supported
            # with this model"). Retry once with them stripped rather than
            # hardcoding a per-model table we would then have to maintain.
            if "Unsupported parameter" in str(e) and temperature is not None:
                return fn(model, messages, system, None, max_tokens, session)
            raise

    # ------------------------------------------------------------ openai chat
    def _chat(self, model, messages, system, temperature, max_tokens, session) -> dict:
        wire = []
        if system:
            wire.append({"role": "system", "content": system})
        for m in messages:
            item = {"role": m["role"], "content": m["content"]}
            if m["role"] == "assistant" and m.get("thinking"):
                item["reasoning_content"] = m["thinking"]
            wire.append(item)
        d = self._post("/chat/completions", {
            "model": model, "messages": wire, "max_tokens": max_tokens,
            **({"temperature": temperature} if temperature is not None else {}),
        }, session)
        msg = d["choices"][0]["message"]
        return {
            "text": msg.get("content") or "",
            "thinking": msg.get("reasoning_content") or "",
            "stop_reason": d["choices"][0].get("finish_reason"),
            "usage": d.get("usage") or {},
            "raw": {"role": "assistant", "content": msg.get("content") or "",
                    "thinking": msg.get("reasoning_content") or ""},
        }

    # ------------------------------------------------------- openai responses
    def _responses(self, model, messages, system, temperature, max_tokens, session) -> dict:
        wire = []
        for m in messages:
            kind = "input_text" if m["role"] == "user" else "output_text"
            wire.append({"role": m["role"],
                         "content": [{"type": kind, "text": m["content"]}]})
        payload = {
            "model": model, "input": wire, "max_output_tokens": max_tokens,
            "store": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if system:
            payload["instructions"] = system
        d = self._post("/responses", payload, session)

        text, thinking = [], []
        for o in d.get("output", []):
            t = o.get("type")
            if t == "message":
                for c in o.get("content", []):
                    if c.get("type") == "output_text":
                        text.append(c.get("text", ""))
            elif t == "reasoning":
                thinking.append(o.get("summary") or "")
        return {
            "text": "".join(text),
            "thinking": "".join(thinking),
            "stop_reason": d.get("status"),
            "usage": d.get("usage") or {},
            "raw": {"role": "assistant", "content": [{"type": "output_text",
                                                     "text": "".join(text)}]},
        }

    # --------------------------------------------------------- anthropic-ish
    def _messages(self, model, messages, system, temperature, max_tokens, session) -> dict:
        wire = []
        for m in messages:
            item = {"role": m["role"], "type": "message"}
            if m["role"] == "assistant" and m.get("thinking"):
                item["content"] = [
                    {"type": "thinking", "thinking": m["thinking"],
                     "signature": m.get("signature", "")},
                    {"type": "text", "text": m["content"]},
                ]
            else:
                item["content"] = m["content"]
            wire.append(item)
        payload = {"model": model, "messages": wire, "max_tokens": max_tokens}
        if temperature is not None:
            payload["temperature"] = temperature
        if system:
            payload["system"] = system
        d = self._post("/messages", payload, session)

        text, thinking, blocks = [], [], d.get("content", [])
        for b in blocks:
            if b.get("type") == "text":
                text.append(b.get("text", ""))
            elif b.get("type") == "thinking":
                thinking.append(b.get("thinking", ""))
        return {
            "text": "".join(text),
            "thinking": "".join(thinking),
            "stop_reason": d.get("stop_reason"),
            "usage": d.get("usage") or {},
            "raw": {"role": "assistant", "type": "message", "content": blocks},
        }


def usage_tokens(usage: dict) -> tuple[int, int]:
    """Normalise every usage shape we have seen to (input, output).

    Handles the three REST protocols plus whatever `opencode --format json`
    emits (input/output, prompt/completion, tokens:{input,output,reasoning}).
    Reasoning tokens count as output.
    """
    if not usage:
        return (0, 0)

    def num(*keys):
        for k in keys:
            v = usage.get(k)
            if isinstance(v, (int, float)):
                return int(v)
        return 0

    tin = num("prompt_tokens", "input_tokens", "input", "prompt")
    tout = num("completion_tokens", "output_tokens", "output", "completion")
    tout += num("reasoning_tokens", "reasoning")
    # nested cache figures are already inside input for most providers; only add
    # them when nothing else was reported
    if tin == 0 and tout == 0:
        tin = num("cache_read", "cache_write", "cached_tokens")
    return (tin, tout)


def usage_cost(usage: dict) -> float | None:
    """Return a provider-reported cost if the events carried one."""
    for k in ("cost", "costUSD", "totalCost", "cost_usd"):
        v = usage.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None
