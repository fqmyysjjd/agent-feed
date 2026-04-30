# Development Workflow

Use this rule for implementation, refactor, test, and project-structure work.

## Start Checklist

Before editing, identify:

```md
Current task boundary:
Stopping condition:
Milestone or phase:
Task:
Owner module:
Write set:
Read-only docs:
Contracts touched:
Public API touched: yes/no
Store/persistence touched: yes/no
Migration touched: yes/no
Tests expected:
Test gate:
Comment/docstring impact:
Forbidden changes:
```

Do not start coding if `Current task boundary`, `Stopping condition`, `Owner module`, `Write set`, `Contracts touched`, `Test gate`, or `Comment/docstring impact` are unclear.

## Implementation Rules

1. Implement the smallest scoped change that satisfies the task.
2. Preserve public/internal boundaries and documented ownership.
3. Keep public contracts separate from internal implementation details.
4. Prefer existing project patterns over new abstractions.
5. Add or update tests for changed behavior, failure paths, boundaries, or invariants.
6. Update design docs only when a contract or boundary truly changes.

## Comment And Docstring Discipline

Write comments or docstrings when they explain:

1. Why a non-obvious boundary, invariant, fallback, or tradeoff exists.
2. Ownership or source-of-truth rules that future changes must preserve.
3. Failure, recovery, idempotency, redaction, security, or trace semantics.
4. Public API behavior, store/persistence contract behavior, or extension points.
5. A temporary limitation with explicit owner, reason, and follow-up path.

Do not write comments that repeat obvious code, describe clear mechanics, hide design gaps behind TODOs, or claim safety properties not enforced by code/tests.

## Verification Ladder

Apply `.agents/rules/testing-gates.md` before selecting or reporting verification.

Use the narrowest verification that can prove the current task boundary, then broaden when shared behavior is touched:

1. Documentation/protocol-only changes: verify links, references, naming rules, and required sync scripts.
2. Narrow implementation changes: run targeted tests for the changed behavior or owner module.
3. Public contracts, shared utilities, module ports, package config, or cross-module changes: run the full local code gate configured for this project.
4. Failed checks must be fixed or explicitly reported with residual risk.
5. Do not claim verification succeeded when a command was skipped, unavailable, or failed.

Use `sh .agents/scripts/verify-agent-dev.sh <scope>` when the scope matches the current task.

## Gap Handling

Proceed directly when a documented default exists and the choice is local, reversible, and not externally visible.

Ask the user when the choice changes user-visible behavior, public contracts, source-of-truth ownership, persistence, security, policy, audit, recovery, delivery scope, or dependency/tooling choices.
