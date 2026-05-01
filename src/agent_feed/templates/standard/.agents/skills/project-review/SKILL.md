---
name: project-review
description: Use when reviewing modified code, git diffs, commits, merges, PR-like changes, or implementation output.
---

# Project Review Skill

## Required Use

Use this skill for code, diff, commit, merge, or AI-generated implementation review.

Do not modify code during a review unless the user explicitly asks for fixes in the same task.

## Review Mode

Classify the review before acting:

1. `Pure review`: the user asked for review, diff review, commit review, or findings. Do not edit files. Return findings and residual risk only.
2. `Implementation gate`: the review is part of a task that already includes coding, refactor, fix, or tests. Findings may become follow-up fixes inside the same Task Brief.

For implementation gates, route P0/P1 findings and default-fix P2 findings through `.agents/skills/project-fix/SKILL.md`, then rerun relevant verification before final handoff.

If a finding requires an unconfirmed decision outside the current Task Brief, stop and apply `.agents/rules/decision-gates.md`.

## Required Reading

1. `.agents/rules/outcome-boundary.md`
2. `.agents/project/architecture-boundaries.md`
3. `.agents/rules/development-workflow.md`
4. `.agents/project/project-structure.md`
5. `.agents/rules/testing-gates.md`
6. `.agents/rules/review-gates.md`
7. `.agents/domain/contracts.md`

## Review Scope

Findings should prioritize correctness, contract drift, module ownership, tests, error handling, security/secret handling, and maintainability.

## Severity Model

1. `P0`: Data loss, secret leak, source-of-truth break, or irreversible corruption.
2. `P1`: Public API, contract, lifecycle, persistence, security, or recovery break.
3. `P2`: Module boundary, test coverage, traceability, or maintainability risk.
4. `P3`: Naming, local readability, or small cleanup issue.

## Output

Return findings first, ordered by severity. If no findings are found, say so explicitly and list residual risks or tests not run.
