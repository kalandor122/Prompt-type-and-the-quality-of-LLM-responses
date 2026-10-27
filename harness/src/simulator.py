"""The simulated user.

Design rule (see pilot-terv-hu.md S3): the simulator gets ONLY the user's wants,
in user voice. It never sees the "what's missing" column, the rubric, the arm, or
which model is asking. It never invents a requirement — anything unmapped gets
"whatever you think is best", so the pre-registered list stays the only ground
truth and the IA count stays meaningful.
"""
from __future__ import annotations

from pathlib import Path

from harness import get_driver, usage_tokens   # noqa: E402  (any driver works)

SYSTEM_FILE = Path(__file__).resolve().parent.parent / "prompts" / "simulator_system.md"
CORRECT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "simulator_correct.md"
# Arm D corrects a PLAN, not a list of assumptions. The distinction matters:
# a plan names concrete intended ACTIONS, so the user can stop a wrong action
# before it happens rather than arguing about beliefs afterwards.
PLAN_FILE = Path(__file__).resolve().parent.parent / "prompts" / "simulator_plan.md"


def system_prompt() -> str:
    return SYSTEM_FILE.read_text(encoding="utf-8")


def correct_system_prompt() -> str:
    """Arm E: same simulated person, opposite instruction — fix what is wrong
    instead of only answering what was asked. Still sees ONLY the U-tagged
    wants, never the rubric or the hidden list, so the ground truth cannot leak.
    """
    return CORRECT_FILE.read_text(encoding="utf-8")


def plan_system_prompt() -> str:
    """Arm D: same simulated person, but correcting a PLAN rather than a list of
    beliefs. A plan names concrete intended actions, so the correction can block
    a wrong action before it happens. Also sees ONLY the U-tagged wants, so the
    ground truth cannot leak into the correction.
    """
    return PLAN_FILE.read_text(encoding="utf-8")


def build_wants_block(item: dict) -> str:
    """Hidden state, in user voice. U entries only."""
    lines = []
    for h in item["hidden"]:
        if h.get("tag") != "U":
            continue
        voice = h.get("want_voice") or h.get("want", "")
        lines.append(f"- {voice}")
    return "\n".join(lines) if lines else "(no stated preferences)"


def build_user_prompt(item: dict, task_prompt: str, assistant_message: str) -> str:
    return f"""THE REQUEST YOU SENT TO THE ASSISTANT (you typed this yourself):
{task_prompt}

WHAT YOU ACTUALLY WANT (your private preferences, do not read these out verbatim
unless asked directly):
{build_wants_block(item)}

THE ASSISTANT JUST SAID:
{assistant_message}

Reply to the assistant now, following your rules exactly. If the assistant asked
no question, reply with exactly:
No further information is available. Please complete the task.
"""


def build_correct_prompt(item: dict, task_prompt: str, assistant_message: str) -> str:
    return f"""THE REQUEST YOU SENT TO THE ASSISTANT (you typed this yourself):
{task_prompt}

WHAT YOU ACTUALLY WANT (your private preferences, do not read these out verbatim):
{build_wants_block(item)}

THE ASSISTANT JUST LISTED ITS ASSUMPTIONS ABOUT YOU:
{assistant_message}

Correct only what is wrong, following your rules exactly. If nothing is wrong,
reply with exactly:
That's all fine, go ahead.
"""


class Simulator:
    def __init__(self, driver, model: str, protocol: str, temperature: float = 0.3,
                 max_tokens: int = 400, session_prefix: str = "sim"):
        self.gw = driver
        self.model = model
        self.protocol = protocol
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.session_prefix = session_prefix

    def answer(self, item: dict, task_prompt: str, assistant_message: str,
               session_id: str, mode: str = "ask") -> dict:
        """mode='ask'   -> arm B: answer only what was asked.
           mode='correct' -> arm E: correct whatever contradicts the user's wants.
           mode='plan'  -> arm D: correct the plan the assistant intends to follow."""
        if mode == "plan":
            sys_prompt, build = plan_system_prompt(), build_correct_prompt
        elif mode == "correct":
            sys_prompt, build = correct_system_prompt(), build_correct_prompt
        else:
            sys_prompt, build = system_prompt(), build_user_prompt
        out = self.gw.complete(
            protocol=self.protocol,
            model=self.model,
            messages=[{"role": "user",
                       "content": build(item, task_prompt, assistant_message)}],
            system=sys_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            session=session_id,
        )
        tin, tout = usage_tokens(out["usage"])
        out["tokens"] = {"input": tin, "output": tout}
        return out
