# Outcome Boundary

This is the highest-priority working rule for AI-assisted development in this repository.

Every AI development task must serve a clear near-term result. Do not extend a design, plan, or implementation just because more can be said or built.

## Highest Priority Rule

Before reading deeply, writing documents, or changing code, identify the current task's expected stopping point.

The stopping point is not the final product vision. It is the nearest useful result the current task must reach.

## Required Task Frame

At the start of a new session, after context compression, or before continuing a long-running thread, recover or write this frame:

```md
## Current Task Boundary

| Item | Content |
| --- | --- |
| User goal | What the user is really trying to advance |
| Current step | How far this turn should go |
| Stopping condition | What condition ends this work |
| Out of scope | What is explicitly excluded |
| Development-ready standard | If design, what makes it ready for implementation |
| Blocker standard | What gap prevents implementation |
| Next action | What happens after the boundary is satisfied |
```

If the frame cannot be recovered, infer the smallest reasonable frame and state the assumption. Ask the user when `.agents/rules/decision-gates.md` says the missing boundary can affect future development results.

## Task Brief

For any implementation, fix, review, design, or AI-protocol change, turn the task frame into a compact Task Brief before making edits.

```md
## Task Brief

| Item | Content |
| --- | --- |
| Goal | What result this turn must produce |
| Stop | What condition ends the work |
| Out of scope | What is explicitly excluded |
| Read context | Rules, project constraints, domain docs, or files that must be read |
| Write set | Files/directories that may be changed |
| Contracts/boundaries | Contracts, ownership, public API, persistence, security, or trace boundaries involved |
| Verification gate | Commands, tests, checks, or review gates that prove the result |
| Next action | The next action after this boundary is satisfied |
```

Do not start editing if `Goal`, `Stop`, `Write set`, or `Verification gate` are unclear.

## Task Class Gate

Classify the task before choosing how much planning is needed:

1. `Direct action`: small local edit, command run, typo fix, narrow reference update, or obvious deterministic repair. Act directly after recovering the Task Brief.
2. `Implementation task`: code, tests, package metadata, generated template behavior, project structure, or public command behavior. Use `.agents/rules/development-workflow.md`.
3. `Design task`: architecture, module ownership, public contract, persistence, verification profile, adapter behavior, product scope, or multi-step implementation plan. Write only until the design is development-ready.
4. `Exploration/review task`: read-only analysis, code review, gap review, or feasibility check. Do not edit unless the user asks for fixes.
5. `Decision task`: any unconfirmed choice that can affect future development results. Apply `.agents/rules/decision-gates.md`.

For long or difficult tasks, produce a compact plan before editing when the next action would otherwise require guessing. Stop for user confirmation at the point where the plan introduces a new public behavior, source-of-truth boundary, dependency/tooling choice, adapter behavior, verification contract, or delivery scope.

If a new gap appears during design or implementation, do not silently absorb it into the current task. Continue only when the gap is local, reversible, and already covered by the Task Brief; otherwise pause, summarize the gap, provide concrete options, and ask for a decision.

## Design Readiness Standard

A design is ready for development only when it answers:

1. What behavior is being built.
2. Which module owns each responsibility.
3. Which public contracts, persistence contracts, domain objects, records, or ports are used or changed.
4. What documented owner is authoritative for each durable or externally visible fact.
5. What is explicitly out of scope.
6. What files or directories are likely write targets.
7. What tests or verification prove the result.
8. What unresolved decisions remain, if any.

If these are not answered, do not proceed to implementation.

## Anti-Drift Rules

1. Do not expand from a concrete task into a broader platform vision unless the user asks.
2. Do not add future-facing abstractions to make a document feel complete.
3. Do not continue writing after the stopping condition is met.
4. Do not treat a polished explanation as sufficient if the next development step still requires guessing.
5. Do not hide missing decisions inside implementation details.
6. Do not let context compression replace the task frame; rebuild it first.
7. Do not turn an unconfirmed gap into implementation; apply `.agents/rules/decision-gates.md` first.
