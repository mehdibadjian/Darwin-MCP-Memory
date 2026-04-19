"""Sequential Thinking species — Cloud-less AI plan, Phase 4b.

Gives Gemma 2b a chain-of-thought scaffold for multi-step problems.
Accepts a problem string, emits a structured numbered plan.
Registered with short_description: "Break problem into numbered steps."
"""
from __future__ import annotations

import re
import textwrap
from typing import Optional


def sequential_thinking(
    problem: str,
    context: Optional[str] = None,
    max_steps: int = 8,
) -> dict:
    """Decompose *problem* into numbered reasoning steps.

    This is a deterministic scaffold — it does not call an LLM.
    It parses the problem into sub-questions using heuristic sentence
    splitting, wraps each in a numbered step, and returns a structured
    plan that the model can execute one step at a time.

    Args:
        problem:   The problem or task to decompose.
        context:   Optional background information to include in step 1.
        max_steps: Hard cap on the number of steps emitted (default 8).

    Returns:
        dict with keys:
            status  — "ok"
            problem — echoed input
            steps   — list of {"step": int, "action": str}
            hint    — guidance for the calling model
    """
    if not problem or not problem.strip():
        return {"status": "error", "problem": problem, "error": "problem must not be empty"}

    # Split on sentence boundaries and question marks.
    raw_sentences = re.split(r"(?<=[.?!])\s+", problem.strip())

    # Build steps: first step always sets up context.
    steps: list[dict] = []

    if context:
        steps.append({"step": 1, "action": f"Review context: {context.strip()}"})

    # Identify sub-questions/clauses within the problem.
    sub_questions = _extract_sub_questions(problem)

    if sub_questions:
        for i, sq in enumerate(sub_questions[:max_steps - len(steps) - 1], start=len(steps) + 1):
            steps.append({"step": i, "action": sq})
    else:
        # Fallback: treat each sentence as its own step.
        for i, sentence in enumerate(raw_sentences[:max_steps - len(steps) - 1], start=len(steps) + 1):
            s = sentence.strip()
            if s:
                steps.append({"step": i, "action": s})

    # Always end with a synthesis step.
    steps.append({
        "step": len(steps) + 1,
        "action": "Synthesise findings from previous steps into a final answer.",
    })

    return {
        "status": "ok",
        "problem": problem,
        "steps": steps,
        "hint": (
            "Execute each step in order. After completing a step, call this tool "
            "again with the next step's action as the new problem, or proceed to "
            "the synthesis step when all sub-problems are resolved."
        ),
    }


def _extract_sub_questions(text: str) -> list[str]:
    """Heuristically pull sub-questions and imperative clauses from text."""
    candidates = []

    # Split on conjunctions that often introduce sub-tasks.
    parts = re.split(r"\b(?:and then|then|also|additionally|finally|first|next|after that)\b", text, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip().strip(",").strip()
        if len(part) > 10:
            # Capitalise and ensure punctuation.
            part = part[0].upper() + part[1:]
            if not part.endswith((".", "?", "!")):
                part += "."
            candidates.append(part)

    return candidates if len(candidates) > 1 else []
