# Trustworthy Agentic AI — Explainability + Human-in-the-Loop

PhD-prep prototype for **BRJP26100123: Building Trustworthy AI Systems through Explainability and Human-in-the-Loop Control**.

Supervisors: K Sandesh Kamath (BITS Pilani, Goa) · Nalin Asanka Gamagedara Arachchilage (RMIT, STEM)

## Problem in one line
Multimodal LLM/VLM agents can perceive, reason, plan and act — but no one can see *why* they chose an action, what they assumed, or what could go wrong, before they act.

## What this repo builds
A web-based prototype that:
1. Converts a user goal into a detailed, **inspectable plan** — intended actions, assumptions, constraints, risks.
2. Gives **proactive explanations** — why this action, what alternatives were considered, failure points — tracing reasoning across modalities.
3. **Validates** the plan against security, privacy, organisational and ethical policies, flagging conflicts for human review.
4. Lets a human **correct assumptions, refine constraints, approve or reject** — the agent iterates until safe, aligned and auditable.
5. Executes only after automated checks + human approval, in a **monitored, sandboxed environment with complete audit logging**.

## Research threads
- 460202 Autonomous agents and multiagent systems (50%)
- 460508 Information retrieval and web search (25%)
- 460808 Mixed initiative and human-in-the-loop (25%)
- 461103 Deep learning (25%)

## Weekly rhythm
- **Week 1 (5–11 Nov 2026): Inspectable plans** — plan schema + a plan generator that always shows rationale, alternatives and risks.
- **Week 2: Human-in-the-loop** — approve / reject / refine loop + audit log.
- **Week 3: Policy validation** — security / privacy / ethics checks that flag conflicts before execution.
- **Week 4: Multimodal tracing** — how a visual input changed the reasoning, in plain language.

Daily work here is small and real: one note, one schema change, or one function at a time. The repo is left working at the end of every day.
