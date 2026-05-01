---
name: guidance-promoter
description: Use when user corrections, repeated AI failures, or session-state conclusions should be promoted into stable AI development guidance.
---

# Guidance Promoter

Use this skill to turn user corrections and repeated AI development failures into stable project guidance.

## Required Use

Use this skill when:

1. The user corrects how the AI should work in this repository.
2. The user says a rule, workflow, or conclusion should be remembered.
3. A repeated failure appears across multiple turns.
4. Session-state carry-forwards become stable enough to promote.
5. The user asks to improve `.agents`, AGENTS, rules, skills, or development protocol docs.

## Workflow

1. Identify what the user corrected.
2. State what AI failure or knowledge gap it reveals.
3. Decide whether the conclusion is stable or session-local.
4. Propose the target asset and exact change.
5. If the target is `.agents/skills/`, use `.agents/skills/skill-maintainer/SKILL.md`.
6. If the change is still session-local, update `.agents/session-state/<session_id>.json`.
7. Run the relevant design review gate before final handoff.
