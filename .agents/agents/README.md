# Agent Profiles

This directory stores reusable specialist agent profiles for delegated AI work.

These profiles are not mandatory startup context. Use them only when a task benefits from a narrow checker or worker.

## Use Rules

1. A profile must have a narrow responsibility.
2. A profile must name its required reading set.
3. A profile must produce actionable findings with file and line references when possible.
4. A profile must not change files unless explicitly assigned as a worker with a write set.
