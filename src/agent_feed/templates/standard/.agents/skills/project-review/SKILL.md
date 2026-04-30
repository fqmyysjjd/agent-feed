---
name: project-review
description: Use when reviewing modified code, git diffs, commits, merges, PR-like changes, or implementation output.
---

# Project Review Skill

## Required Use

Use this skill for code, diff, commit, merge, or AI-generated implementation review.

Do not modify code during a review unless the user explicitly asks for fixes in the same task.

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
