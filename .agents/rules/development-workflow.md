# Development Workflow

Use this rule for implementation, refactor, test, and project-structure work.

Do not begin implementation only from a user-proposed approach or partial solution. First recover the task boundary, inspect the relevant project context and code, and verify that the approach fits the desired result and project constraints.

## Implementation Addendum

Before editing code, tests, package metadata, project structure, or implementation-facing docs, first complete the Task Brief in `.agents/rules/outcome-boundary.md`.

Then add only the implementation-specific details below:

```md
Milestone or phase:
Task type: implementation / refactor / test / project-structure / implementation-doc
Owner module:
Read-only docs:
Public API touched: yes/no
Store/persistence touched: yes/no
Migration touched: yes/no
Tests expected:
Comment/docstring impact:
Forbidden changes:
```

Do not duplicate or contradict the Task Brief. `Goal`, `Stop`, `Write set`, `Contracts/boundaries`, and `Verification gate` are owned by `.agents/rules/outcome-boundary.md`.

Do not start implementation work if the Task Brief is missing, or if `Owner module`, `Task type`, `Tests expected`, or `Comment/docstring impact` are unclear.

If implementation reveals a new write target, contract boundary, verification gate, or out-of-scope change, stop and update the Task Brief or apply `.agents/rules/decision-gates.md` before continuing.

## Reuse Before Build

Before writing non-trivial implementation code:

1. Search the current repository for an existing owner, helper, adapter, test fixture, parser, validator, command pattern, or script that already solves the problem.
2. Trace upstream callers and downstream consumers before replacing or duplicating behavior.
3. Prefer standard library, already-installed dependencies, and established project patterns over new local abstractions.
4. For complex generic domains such as parsing, diffing, schema validation, CLI prompting, testing, formatting, protocol handling, or runtime orchestration, check whether a proven library or existing project dependency should be used instead of hand-writing the logic.
5. If choosing an external dependency would affect package surface, install behavior, license risk, runtime behavior, network use, or future maintenance, stop and apply `.agents/rules/decision-gates.md`.
6. Use web research for external library choices when current ecosystem reliability, popularity, maintenance, or API facts matter. Do not present web-derived claims without source and date.

Only build from scratch when reuse is unavailable, unsafe, heavier than the task requires, or incompatible with the project boundary. Record that reasoning briefly when the choice is not obvious.

## Implementation Rules

1. Implement the smallest scoped change that satisfies the task.
2. Reuse existing code, dependency, or project pattern when it is a better fit than new code.
3. Preserve public/internal boundaries and documented ownership.
4. Keep public contracts separate from internal implementation details.
5. Prefer existing project patterns over new abstractions.
6. Add or update tests for changed behavior, failure paths, boundaries, or invariants.
7. Update design docs only when a contract or boundary truly changes.

## Comment And Docstring Discipline

Write comments or docstrings when they explain:

1. Why a non-obvious boundary, invariant, fallback, or tradeoff exists.
2. Ownership or source-of-truth rules that future changes must preserve.
3. Failure, recovery, idempotency, redaction, security, or trace semantics.
4. Public API behavior, store/persistence contract behavior, or extension points.
5. A temporary limitation with explicit owner, reason, and follow-up path.

Do not write comments that repeat obvious code, describe clear mechanics, hide design gaps behind TODOs, or claim safety properties not enforced by code/tests.

## Verification Ownership

`.agents/rules/testing-gates.md` owns verification scope selection, failure handling, and evidence rules.

Before editing or reporting completion:

1. Decide what evidence is needed for the current Task Brief.
2. Route that decision through `.agents/rules/testing-gates.md`.
3. Do not claim verification succeeded when a command was skipped, unavailable, or failed.

## Gap Handling

Proceed directly when a documented default exists and the choice is local, reversible, and not externally visible.

Ask the user when the choice changes user-visible behavior, public contracts, source-of-truth ownership, persistence, security, policy, audit, recovery, delivery scope, or dependency/tooling choices.
