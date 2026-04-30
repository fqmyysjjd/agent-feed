---
name: skill-maintainer
description: Use when creating, updating, reviewing, renaming, deleting, or syncing .agents skills.
---

# Skill Maintainer

Use this skill to maintain `.agents/skills/` as a clean set of task-specific AI workflows.

## Required Use

Use this skill when creating, updating, reviewing, renaming, deleting, or syncing skills.

## Placement Decision

Before editing, classify the content:

1. `rules/`: invariant constraints, gates, required behavior.
2. `domain/`: stable project concepts and ownership knowledge.
3. `skills/`: repeatable task workflow with triggers and steps.
4. `agents/`: narrow sub-agent profile.
5. `session-state/`: session-local conclusion not yet stable.

Only create or update a skill when the content is a repeatable task workflow.

## Skill Requirements

Each skill must have frontmatter, a `name` matching its directory name, lowercase kebab-case with no more than three words, a specific `description`, Required Use, Required Reading, workflow or review procedure, output expectations, and guardrails.

## Maintenance Workflow

1. Recover the current task boundary.
2. Classify the requested change.
3. Check existing skills to avoid overlap.
4. Make the smallest skill change that satisfies the task.
5. Update indexes if needed.
6. Run `sh .agents/scripts/sync-agent-assets.sh`.
7. Run `sh .agents/scripts/verify-agent-dev.sh protocol`.
