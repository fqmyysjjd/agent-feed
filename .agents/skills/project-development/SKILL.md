---
name: project-development
description: Use before implementation, refactor, tests, project-structure changes, or coding tasks.
source: agent-feed
trust: core
---

# Project Development Skill

## Required Use

Use this skill before writing or modifying code.

## Required Reading

1. `.agents/rules/context-loading.md`
2. `.agents/rules/outcome-boundary.md`
3. `.agents/rules/engineering-architecture.md`
4. `.agents/skills/engineering-planning/SKILL.md`
5. `.agents/project/architecture-boundaries.md`
6. `.agents/rules/development-workflow.md`
7. `.agents/rules/testing-gates.md`
8. `.agents/project/project-structure.md`
9. `.agents/rules/change-risk-gates.md`
10. `.agents/domain/contracts.md`

For milestone details, read `.agents/project/milestones.md`.

## Workflow

1. Recover the current task result boundary.
2. Apply `.agents/rules/engineering-architecture.md` when the work touches ownership, placement, dependency direction, abstraction, reuse, file creation, or project structure.
3. Use `.agents/skills/engineering-planning/SKILL.md` to decide owner, reuse, placement, write set, boundaries, and verification before editing.
4. Fill the start checklist from `.agents/rules/development-workflow.md`.
5. Confirm the design or task is concrete enough to implement without inventing missing decisions.
6. Implement the smallest scoped change.
7. Apply `.agents/rules/testing-gates.md` to choose verification evidence.
8. Use `.agents/skills/project-review/SKILL.md` for post-change review.
9. Stop when the declared task boundary is satisfied.
10. End through the Final Handoff Gate in `.agents/rules/session-state.md`.
