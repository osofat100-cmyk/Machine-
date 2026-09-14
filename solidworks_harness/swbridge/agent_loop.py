"""The agent loop.

One prompt in, a saved SolidWorks assembly out. The SDK's tool runner
drives the request -> execute -> feed-result-back cycle; everything
interesting is in the tool surface (`tools.py`) and the system prompt
below.

    python -m swbridge.agent_loop \
        --prompt "A 6-DOF robot arm, 500mm reach, aluminium" \
        --out C:/work/arm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anthropic

from . import tools as T
from .connection import Session, SolidWorksUnavailable

MODEL = "claude-opus-5"

SYSTEM = """You are driving SolidWorks through a tool API to build a \
mechanical assembly.

Work in this order, and do not skip the checks:

1. PLAN FIRST. Before touching a tool, write out the part list, the
   overall dimensions, and which datum each part is built on. Decide the
   joint axes up front. Changing your mind about a datum halfway through
   costs far more than thinking about it now.

2. ONE PART AT A TIME. Build it, rebuild_and_check it, check_constraints
   on it, save it. Only then start the next one. A part left broken
   poisons every assembly mate that later refers to it.

3. SKETCHES MUST BE FULLY CONSTRAINED. finish_sketch tells you the
   status. If it comes back under_constrained, add the missing
   dimensions before you extrude. An under-constrained sketch extrudes
   perfectly well and then moves when anything near it changes -- this
   is the single most common way a generated model turns out to be
   worthless, because it looks finished and is not.

4. LOOK AT IT. Call take_screenshot after each part and at every
   assembly stage, and actually read the image. A great many defects are
   geometrically legal and obviously wrong on sight: a gripper whose
   jaws open outward, a boss on the wrong face, a link assembled inside
   its own housing. No rebuild check will ever catch these.

5. MATE DELIBERATELY. Each joint gets exactly the mates it needs to
   leave one degree of freedom -- a concentric plus a coincident for a
   revolute joint, nothing more. Over-mating produces an assembly that
   refuses to move; under-mating produces one that flops. After mating a
   joint, screenshot it and confirm the axis is the one you intended.

6. WHEN A TOOL RETURNS AN ERROR, READ IT. The messages say what is
   actually wrong. Do not retry the same call unchanged, and do not
   build on top of a failed feature.

Units are millimetres and degrees everywhere in this API.

Finish by saving every part and the assembly, then report the part
count, any sketch still under-constrained, and anything you could not
make work."""


def run(prompt: str, out_dir: str, max_tokens: int = 64000,
        effort: str = "high", visible: bool = True) -> str:
    """Drive SolidWorks from a single natural-language prompt."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    session = Session.attach(visible=visible)
    T.bind(session)

    client = anthropic.Anthropic()
    task = (
        f"{prompt}\n\n"
        f"Save every part and the assembly under {out}. "
        f"Write screenshots to {out / 'shots'}."
    )

    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=max_tokens,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        tools=T.ALL_TOOLS,
        messages=[{"role": "user", "content": task}],
    )

    final = None
    for message in runner:
        final = message
        for block in message.content:
            if block.type == "text" and block.text.strip():
                print(block.text)
            elif block.type == "tool_use":
                print(f"  -> {block.name}({_brief(block.input)})")

    if final is not None and final.stop_reason == "refusal":
        return f"stopped: {final.stop_details}"
    return _last_text(final) if final else "(no response)"


def _brief(payload: dict, limit: int = 90) -> str:
    s = ", ".join(f"{k}={v!r}" for k, v in payload.items())
    return s if len(s) <= limit else s[:limit] + "..."


def _last_text(message) -> str:
    return "\n".join(b.text for b in message.content if b.type == "text")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Drive SolidWorks from a prompt.")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--effort", default="high",
                    choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--headless-ui", action="store_true",
                    help="hide the SolidWorks window (it still runs)")
    args = ap.parse_args(argv)

    try:
        print(run(args.prompt, args.out, effort=args.effort,
                  visible=not args.headless_ui))
    except SolidWorksUnavailable as exc:
        print(f"cannot reach SolidWorks: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
