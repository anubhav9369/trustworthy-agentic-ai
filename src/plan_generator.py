"""Week 1: Inspectable plan generator (goal-driven version).

Takes a user goal and returns a plan in ``plan_schema.json`` — every step
carries why / alternatives / failure points, so a human can approve,
reject, or refine it before anything executes.

How it works (no LLM call yet — the shape comes first):
1. ``detect_intents`` reads the goal for intent keywords
   (retrieve, summarise, send, compare, draft, analyse).
2. Each intent contributes concrete steps from ``INTENT_STEPS``,
   each with its own rationale, alternatives, and failure points.
3. ``make_plan`` assembles the steps, derives assumptions, constraints
   and risks from the intents, and stamps ``human_decision: pending``.
4. ``validate_plan`` checks the result against the schema's contract
   (required keys, non-empty explanations, unique step ids).
5. ``human_review_summary`` renders a one-minute-readable review —
   the "approve in under a minute" test from docs/week-01-plan.md.

Next steps (Week 2+): replace the keyword intents with an LLM call,
add the human approve/reject/refine loop, then policy validation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "plan_schema.json"

# intent -> keywords that signal it, in priority order.
INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "retrieve": ("find", "search", "look up", "lookup", "fetch", "get the", "retrieve"),
    "summarise": ("summar", "tl;dr", "brief", "condense", "key points"),
    "send": ("send", "email", "mail", "message", "share with", "forward"),
    "compare": ("compare", "versus", "vs", "which is better", "difference between"),
    "draft": ("draft", "write", "compose", "prepare a", "create a document"),
    "analyse": ("analys", "analyse", "evaluate", "assess", "review", "check"),
}

# intent -> steps the agent would take, each explainable on its own.
# "needs_permission" is True when the step touches live systems,
# private data, or external actions.
INTENT_STEPS: dict[str, list[dict]] = {
    "retrieve": [
        {
            "action": "Identify the exact source(s) to read — name them, don't guess.",
            "why": "A wrong source means every later step reasons about the wrong material.",
            "alternatives_considered": [
                "Search the whole library and pick the top hit (rejected: top hit may be a near-miss)"
            ],
            "failure_points": ["The source does not exist or is not accessible"],
            "needs_permission": False,
        },
        {
            "action": "Read the source and record which passages support each claim.",
            "why": "Citations are the evidence trail the human checks during review.",
            "alternatives_considered": [
                "Quote from memory (rejected: uncited claims cannot be verified)"
            ],
            "failure_points": ["Key passage is missed; a quote is taken out of context"],
            "needs_permission": False,
        },
    ],
    "summarise": [
        {
            "action": "Condense the material into a short summary that keeps every cited claim.",
            "why": "The summary is only trustworthy if each claim still traces to a source.",
            "alternatives_considered": [
                "Compress aggressively and drop citations (rejected: unverifiable output)"
            ],
            "failure_points": ["A nuance is flattened into a false claim"],
            "needs_permission": False,
        },
    ],
    "send": [
        {
            "action": "Confirm the recipient and the exact message before sending anything.",
            "why": "Sending is irreversible — the human must see the recipient and text first.",
            "alternatives_considered": [
                "Send immediately after drafting (rejected: wrong recipient cannot be unsent)"
            ],
            "failure_points": ["Wrong recipient; message sent before the draft is approved"],
            "needs_permission": True,
        },
        {
            "action": "Send the approved message and record the delivery receipt.",
            "why": "The audit log needs proof the message went out as approved, not as drafted.",
            "alternatives_considered": [
                "Send without logging (rejected: no evidence for the audit trail)"
            ],
            "failure_points": ["Delivery fails silently; message differs from the approved draft"],
            "needs_permission": True,
        },
    ],
    "compare": [
        {
            "action": "List the comparison criteria and the evidence for each option.",
            "why": "A comparison without stated criteria hides the agent's bias.",
            "alternatives_considered": [
                "Give a single recommendation with no criteria (rejected: the human cannot challenge it)"
            ],
            "failure_points": ["Criteria favour one option by construction"],
            "needs_permission": False,
        },
    ],
    "draft": [
        {
            "action": "Draft the document from the retrieved material, keeping claims cited.",
            "why": "A draft built on uncited material inherits every hallucination risk.",
            "alternatives_considered": [
                "Draft from the model's general knowledge (rejected: no grounding in the source)"
            ],
            "failure_points": ["Draft invents details the source never states"],
            "needs_permission": False,
        },
    ],
    "analyse": [
        {
            "action": "State the evaluation criteria and score the material against each one.",
            "why": "Scores without criteria are opinions dressed as measurements.",
            "alternatives_considered": [
                "Give a single overall verdict (rejected: the human cannot see what was weighed)"
            ],
            "failure_points": ["Criteria are vague, so the score cannot be reproduced"],
            "needs_permission": False,
        },
    ],
}

GENERIC_STEP = {
    "action": "Break the goal into concrete sub-tasks and list them for review.",
    "why": "An unrecognised goal must not be executed as a guess — the human sees the split first.",
    "alternatives_considered": [
        "Act on a best-guess interpretation (rejected: silent misinterpretation)"
    ],
    "failure_points": ["The goal is ambiguous and the split is wrong"],
    "needs_permission": False,
}

# intent -> extra assumptions / constraints / risks the plan inherits.
INTENT_NOTES: dict[str, dict[str, list[str]]] = {
    "send": {
        "assumptions": ["The recipient named in the goal is the intended recipient."],
        "constraints": ["Nothing leaves the system (email/message) before human approval."],
        "risks": ["Message sent to the wrong person; content shared before approval."],
    },
    "retrieve": {
        "assumptions": ["The source named in the goal exists and is accessible."],
        "constraints": ["Only read sources the user has access to; do not fabricate citations."],
        "risks": ["Reasoning from the wrong source; citing a passage out of context."],
    },
    "summarise": {
        "assumptions": ["The material to summarise is supplied or already retrieved."],
        "constraints": ["Every claim in the summary must trace to a cited passage."],
        "risks": ["Nuance lost in compression; summary states more than the source supports."],
    },
    "compare": {
        "assumptions": ["The options to compare are named in the goal."],
        "constraints": ["State the criteria before scoring; never hide a criterion."],
        "risks": ["Criteria chosen to favour one option."],
    },
    "draft": {
        "assumptions": ["The draft's topic and audience are clear from the goal."],
        "constraints": ["Draft from retrieved material only; mark anything invented."],
        "risks": ["Draft invents details the source never states."],
    },
    "analyse": {
        "assumptions": ["The criteria for evaluation are stated or inferable from the goal."],
        "constraints": ["Publish the criteria with the scores."],
        "risks": ["Vague criteria make the score unreproducible."],
    },
}


def detect_intents(goal: str) -> list[str]:
    """Return the intents found in the goal, in priority order."""
    lowered = goal.lower()
    return [
        intent
        for intent, keywords in INTENT_KEYWORDS.items()
        if any(k in lowered for k in keywords)
    ]


def make_plan(goal: str) -> dict:
    """Build an InspectablePlan for a goal. Nothing executes here."""
    goal = goal.strip()
    if not goal:
        raise ValueError("goal must not be empty")
    intents = detect_intents(goal)

    steps: list[dict] = [
        {
            "id": "step-1",
            "action": "Restate the goal and list what success looks like.",
            "why": "Prevents the agent acting on a misread goal.",
            "alternatives_considered": [
                "Act immediately on the literal request (rejected: no check for ambiguity)"
            ],
            "failure_points": ["Goal is ambiguous and the restatement is wrong"],
            "needs_permission": False,
        }
    ]
    for intent in intents:
        for template in INTENT_STEPS[intent]:
            step = dict(template)
            step["id"] = f"step-{len(steps) + 1}"
            steps.append(step)
    if not intents:
        step = dict(GENERIC_STEP)
        step["id"] = f"step-{len(steps) + 1}"
        steps.append(step)
    steps.append(
        {
            "id": f"step-{len(steps) + 1}",
            "action": "Present the full plan to the human for approve / reject / refine.",
            "why": "No side effect happens until a human has seen the whole plan.",
            "alternatives_considered": [
                "Execute the plan, then report (rejected: side effects before approval)"
            ],
            "failure_points": ["Human approves without reading; a risky step is overlooked"],
            "needs_permission": False,
        }
    )

    assumptions = ["The goal as written is complete and correct."]
    constraints = [
        "No live-system writes, no private-data sharing, no external messages before approval."
    ]
    risks = ["Acting on a misunderstood goal; over-trust in an unchecked plan."]
    for intent in intents:
        notes = INTENT_NOTES[intent]
        assumptions += notes["assumptions"]
        constraints += notes["constraints"]
        risks += notes["risks"]

    return {
        "goal": goal,
        "steps": steps,
        "assumptions": assumptions,
        "constraints": constraints,
        "risks": risks,
        "human_decision": {"status": "pending", "reviewer_note": ""},
    }


def validate_plan(plan: dict) -> list[str]:
    """Check a plan against the InspectablePlan contract.

    Returns a list of problems; an empty list means the plan is valid.
    Mirrors the required keys of plan_schema.json without a jsonschema
    dependency, so it runs anywhere with the standard library.
    """
    problems: list[str] = []
    schema = json.loads(SCHEMA_PATH.read_text())
    for key in schema["required"]:
        if key not in plan:
            problems.append(f"missing required key: {key}")
    if "steps" in plan:
        if not plan["steps"]:
            problems.append("steps must contain at least one step")
        seen_ids = set()
        for i, step in enumerate(plan["steps"]):
            label = step.get("id", f"steps[{i}]")
            for key in ("id", "action", "why", "alternatives_considered", "failure_points"):
                if key not in step:
                    problems.append(f"{label}: missing {key}")
            if not step.get("why", "").strip():
                problems.append(f"{label}: 'why' must not be empty")
            if not step.get("alternatives_considered"):
                problems.append(f"{label}: must list at least one alternative considered")
            if not step.get("failure_points"):
                problems.append(f"{label}: must list at least one failure point")
            if step.get("id") in seen_ids:
                problems.append(f"duplicate step id: {step.get('id')}")
            seen_ids.add(step.get("id"))
    if plan.get("human_decision", {}).get("status") not in (
        "pending",
        "approved",
        "rejected",
        "needs_refinement",
    ):
        problems.append("human_decision.status must be one of pending/approved/rejected/needs_refinement")
    return problems


def human_review_summary(plan: dict) -> str:
    """One-minute-readable review: goal, steps with reasons, risks, decision."""
    lines = [f"GOAL: {plan['goal']}", ""]
    for step in plan["steps"]:
        perm = " [needs permission]" if step.get("needs_permission") else ""
        lines.append(f"{step['id']}. {step['action']}{perm}")
        lines.append(f"   Why: {step['why']}")
        lines.append(f"   Instead of: {'; '.join(step['alternatives_considered'])}")
        lines.append(f"   Could fail: {'; '.join(step['failure_points'])}")
    lines.append("")
    lines.append("Assumptions: " + "; ".join(plan["assumptions"]))
    lines.append("Constraints: " + "; ".join(plan["constraints"]))
    lines.append("Risks: " + "; ".join(plan["risks"]))
    lines.append("")
    lines.append(f"Decision: {plan['human_decision']['status']} — approve / reject / refine?")
    return "\n".join(lines)


if __name__ == "__main__":
    goal_text = " ".join(sys.argv[1:]) or "Summarise this paper and email the summary to me"
    plan = make_plan(goal_text)
    problems = validate_plan(plan)
    if problems:
        print("INVALID PLAN:")
        print("\n".join(f" - {p}" for p in problems))
        raise SystemExit(1)
    print(human_review_summary(plan))
    print("\nPlan is inspectable: every step has why / alternatives / risks.")
