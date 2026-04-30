---
name: project-development
description: Use before implementation, refactor, tests, project-structure changes, or coding tasks.
---

# Project Development Skill

## Required Use

Use this skill before writing or modifying code.

## Required Reading

1. `.agents/rules/context-loading.md`
2. `.agents/rules/outcome-boundary.md`
3. `.agents/project/architecture-boundaries.md`
4. `.agents/rules/development-workflow.md`
5. `.agents/rules/testing-gates.md`
6. `.agents/project/project-structure.md`
7. `.agents/rules/change-risk-gates.md`
8. `.agents/domain/contracts.md`

For milestone details, read `.agents/project/milestones.md`.

## Workflow

1. Recover the current task result boundary.
2. Fill the start checklist from `.agents/rules/development-workflow.md`.
3. Confirm the design or task is concrete enough to implement without inventing missing decisions.
4. Implement the smallest scoped change.
5. Apply `.agents/rules/testing-gates.md` to choose verification evidence.
6. Use `.agents/skills/project-review/SKILL.md` for post-change review.
7. Stop when the declared task boundary is satisfied.
8. End with the Context Capsule from `.agents/rules/review-gates.md`.
