# Agent Profiles

This directory is an **extension point for specialist sub-agent profiles**. Agent Feed ships it empty by default — there are no built-in profiles. Add a profile here only when you have a recurring narrow checker or worker that the main AI workflow keeps re-deriving.

If this directory contains only this README, treat the layer as inactive: the `agents/*` row in `AGENTS.md` Responsibility Boundary still applies, but no profile load is required during startup.

## When To Add A Profile

Add a profile only when **all** of these hold:

1. The same narrow checking or worker behavior has been performed manually at least twice in this repository.
2. The behavior is too specific for a `.agents/skills/` workflow (it would not help most tasks) but recurs often enough to deserve a stable named profile.
3. The profile's responsibility, required reading, and output format can be written in under one screen.

If the behavior fits a general task workflow, write it as a `skills/` skill instead.

## Profile Requirements

When you do add a profile (`.agents/agents/<name>.md`):

1. The profile must have a narrow responsibility (one checker or one worker, not both).
2. The profile must name its required reading set.
3. The profile must produce actionable findings with file and line references when possible.
4. The profile must not change files unless explicitly assigned as a worker with a written-down write set.

## Example Profile Skeleton

```md
---
name: contract-drift-checker
trust: custom
---

# Contract Drift Checker

## Responsibility

Compare current CLI surface against `.agents/domain/contracts.md` and report drift.

## Required Reading

1. `.agents/domain/contracts.md`
2. `src/agent_feed/cli.py`

## Output

A bullet list of drifted commands/options with file:line evidence. Do not edit files.
```
