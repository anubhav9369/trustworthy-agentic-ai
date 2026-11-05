"""Week 1: Inspectable plan generator (template version).

Takes a user goal and returns a plan in plan_schema.json.
No LLM call yet — the point this week is the *shape* of an
explainable plan: every step carries why / alternatives / risks,
so a human can approve or reject it before anything executes.
"""

import json
from pathlib import Path


def make_plan(goal: str) -> dict:
    return {
        "goal": goal,
        "steps": [
            {
                "id": "step-1",
                "action": "Restate the goal and list what success looks like.",
                "why": "Prevents the agent acting on a misread goal.",
                "alternatives_considered": [
                    "Act immediately on the literal request (rejected: no check for ambiguity)"
                ],
                "failure_points": ["Goal is ambiguous and the restatement is wrong"],
                "needs_permission": False,
            },
            {
                "id": "step-2",
                "action": "Draft the plan's actions, assumptions and constraints for human review.",
                "why": "The human sees the full reasoning before any side effect.",
                "alternatives_considered": [
                    "Execute the first action, then explain (rejected: side effects before approval)"
                ],
                "failure_points": ["A risky action is hidden inside a harmless-looking step"],
                "needs_permission": False,
            },
        ],
        "assumptions": ["The goal as written is complete and correct."],
        "constraints": [
            "No live-system writes, no private-data sharing, no external messages before approval."
        ],
        "risks": ["Acting on a misunderstood goal; over-trust in an unchecked plan."],
        "human_decision": {"status": "pending", "reviewer_note": ""},
    }


if __name__ == "__main__":
    plan = make_plan("Summarise this paper and email the summary to me")
    schema = json.loads((Path(__file__).parent / "plan_schema.json").read_text())
    # Light validation: required top-level keys present, every step explains itself.
    assert all(k in plan for k in schema["required"])
    assert all(
        all(k in s for k in ("id", "action", "why", "alternatives_considered", "failure_points"))
        for s in plan["steps"]
    )
    print(json.dumps(plan, indent=2))
    print("\nPlan is inspectable: every step has why / alternatives / risks.")
