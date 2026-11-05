# Week 1 — Inspectable Plans (5–11 Nov 2026)

**Goal:** No plan leaves the system without a human being able to read *why*.

## Learn this week
- Explainable AI for agents: plan-then-execute vs act-then-explain.
- What makes a plan inspectable: goal, steps, assumptions, constraints, risks, alternatives.
- Sandesh Kamath's angle: explainability for image / multimodal models — a visual input should be traceable to a decision.
- Nalin Arachchilage's angle: agents with live-system access need permission checks before they act, not after.

## Build this week
1. `src/plan_schema.json` — the contract every plan must satisfy.
2. `src/plan_generator.py` — takes a goal, returns a plan in that schema (template first, LLM later).
3. `research/2026-11-05-four-gaps.md` — the four systemic gaps from the proposal, in plain words.

## Done when
- A goal like "summarise this paper and email the summary" produces a plan a non-expert can approve or reject in under a minute.
- Every step has a reason, an alternative, and a risk — no black-box step.

## Anubhav's day
Pick any one day this week to do your own piece — e.g. rewrite one plan example in your words, or review the schema and flag what's missing. Jarvis handles the other days.
