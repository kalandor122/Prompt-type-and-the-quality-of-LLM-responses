"""Shared tool layer: workspace access for any driver.

Kept here so the OpenRouter and OpenCode-Go drivers cannot drift apart — the
study needs the agentic item (T6) to behave identically whichever gateway is in
use, or "agentic" stops meaning anything.

Two schema shapes, both verified live against the OpenCode Go gateway on
2026-09-29:

  /chat/completions  -> {"type":"function","function":{"name":...,"parameters":{...}}}
  /responses         -> {"type":"function","name":...,"parameters":{...}}   (FLAT)

Deliberately three tools and nothing more: enough to read a workspace and write
an artefact, and nothing that can shell out. Keeps the agentic arm bounded and
identical across models.
"""
from __future__ import annotations

import json
from pathlib import Path

_TOOL_DEFS = [
    ("list_dir", "List files under a path in your working directory.",
     {"type": "object",
      "properties": {"path": {"type": "string",
                              "description": "Relative path; '.' is the root."}},
      "required": []}),
    ("read_file", "Read a text file from your working directory.",
     {"type": "object",
      "properties": {"path": {"type": "string", "description": "Relative path."}},
      "required": ["path"]}),
    ("write_file", "Create or overwrite a text file in your working directory.",
     {"type": "object",
      "properties": {"path": {"type": "string", "description": "Relative path."},
                     "content": {"type": "string", "description": "Full file contents."}},
      "required": ["path", "content"]}),
]


def schema_chat() -> list[dict]:
    """OpenAI chat-completions shape (nested under 'function')."""
    return [{"type": "function",
             "function": {"name": n, "description": d, "parameters": p}}
            for n, d, p in _TOOL_DEFS]


def schema_responses() -> list[dict]:
    """OpenAI Responses shape (flat: name/parameters at the top level).

    Verified: the nested shape is rejected with
    "Missing required parameter: 'tools[0].name'".
    """
    return [{"type": "function", "name": n, "description": d, "parameters": p}
            for n, d, p in _TOOL_DEFS]


class ToolSandbox:
    """Per-session working directory with path-escape protection."""

    def __init__(self, root: Path, max_file_chars: int = 24000):
        self.root = Path(root)
        self.max_file_chars = max_file_chars
        self.dirs: dict[str, Path] = {}

    def for_session(self, session: str) -> Path:
        if session not in self.dirs:
            d = self.root / (session or "default")
            d.mkdir(parents=True, exist_ok=True)
            self.dirs[session] = d
        return self.dirs[session]

    def _resolve(self, session: str, rel: str) -> Path:
        base = self.for_session(session).resolve()
        target = (base / (rel or ".")).resolve()
        if target != base and base not in target.parents:
            raise ValueError(f"path escapes the working directory: {rel!r}")
        return target

    def seed(self, session: str, src, exclude=("ground_truth.json",)) -> Path:
        """Copy a task workspace into the session sandbox.

        `exclude` is the ground-truth file the GRADER uses to score the run.
        Leaving it in would let the model read the answer — the single worst
        leak available in this study.
        """
        import shutil
        src = Path(src)
        dst = self.for_session(session)
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            if any(part in exclude for part in rel.parts):
                continue
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / rel)
        return dst

    def run(self, session: str, name: str, args: dict) -> str:
        try:
            if name == "list_dir":
                p = self._resolve(session, args.get("path", "."))
                if not p.exists():
                    return f"error: no such directory: {args.get('path')}"
                return "\n".join(sorted(
                    (c.name + "/" if c.is_dir() else c.name)
                    for c in p.iterdir())) or "(empty)"
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
                return f"wrote {len(args.get('content', ''))} chars to {args['path']}"
            return f"error: unknown tool {name}"
        except (ValueError, OSError, KeyError) as e:
            return f"error: {e}"


# --------------------------------------------------------------- extraction
def extract_calls(protocol: str, message: dict) -> list[dict]:
    """Normalise whatever the gateway returned into [{id, name, arguments}]."""
    calls = []
    if protocol == "responses":
        for o in (message.get("output") or []):
            if o.get("type") == "function_call":
                calls.append({"id": o.get("call_id") or o.get("id", ""),
                              "name": o.get("name", ""),
                              "arguments": o.get("arguments", "{}")})
    else:
        for tc in (message.get("tool_calls") or []):
            fn = tc.get("function") or {}
            calls.append({"id": tc.get("id", ""), "name": fn.get("name", ""),
                          "arguments": fn.get("arguments", "{}")})
    return calls


def result_message(protocol: str, call: dict, result: str) -> dict:
    """The right shape to feed a tool result back in."""
    if protocol == "responses":
        return {"type": "function_call_output", "call_id": _need_id(call),
                "output": result}
    return {"role": "tool", "tool_call_id": _need_id(call), "content": result}


def _need_id(call: dict) -> str:
    """Last line of defence: an empty tool_call_id kills the run with
    "tool_call_id must not be empty". Callers should have assigned one."""
    cid = (call.get("id") or "").strip()
    if not cid:
        raise ValueError(f"tool call {call.get('name')!r} has no id")
    return cid


def parse_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
