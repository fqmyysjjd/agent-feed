# AI Development Engineering

`.agents/` is the project-level AI engineering system for developing this repository with AI coding agents.

These files guide AI assistants while they design, implement, review, and fix the codebase. They are not product runtime rules and should not be treated as user-facing behavior.

## Layer Responsibilities

1. `rules/`: reusable AI development constraints and gates.
2. `project/`: user-maintained project customization layer for current repository constraints.
3. `session-state/`: local JSON files for active long-running conversations.
4. `domain/`: stable project/domain knowledge.
5. `skills/`: task-specific workflows.
6. `.agents/scripts/`: protocol helper scripts for sync, validation, and verification.
7. `agents/`: narrow specialist profiles for delegated checks or worker tasks.

## Highest-Priority Rule

Always load `.agents/rules/outcome-boundary.md` and `.agents/rules/decision-gates.md` before continuing design, development, review, or fix work.

The current task boundary decides when to stop. Decision gates decide when unconfirmed choices require human confirmation. Other rules and skills serve those boundaries.

## Current Rules

1. `outcome-boundary.md`: near-term task result, Task Brief, stopping condition, and anti-drift rules.
2. `decision-gates.md`: human confirmation rules for unconfirmed choices that affect future development results.
3. `context-loading.md`: startup/context-compression loading order and task routing.
4. `session-state.md`: compact JSON state, conversation identity, continuity, and multi-session registry rules.
5. `testing-gates.md`: test selection, minimum coverage, failure handling, and verification evidence rules.
6. `evidence-gates.md`: external research sourcing, classification, and adoption rules.
7. `change-risk-gates.md`: project-level change risk classes and verification command rules.
8. `development-workflow.md`: coding start checklist, comment/docstring discipline, gap handling, and verification ladder.
9. `review-gates.md`: code/design review gates and Context Capsule format.

## Reference Direction

```txt
AGENTS.md
  -> rules/outcome-boundary.md
  -> rules/decision-gates.md
  -> rules/context-loading.md
  -> rules/session-state.md
  -> rules/testing-gates.md
  -> .agents/README.md
  -> project/*
  -> session-state/<session_id>.json when long-running session state exists
  -> domain/*
  -> skills/*
  -> .agents/scripts/*
  -> agents/* when delegation is useful
```

Rules may reference skills only for routing. Skills may reference rules, project constraints, and domain docs as required reading. Domain docs should avoid referencing skills unless explaining usage context.

`.agents/project/README.md` is the required index for the project customization layer. When a file under `.agents/project/` is added, removed, renamed, or materially changed, update that README in the same task.

## Consistency Check

After changing AI engineering protocol files, rule names, project constraint names, skill names, `.agents/` links, session-state JSON, or synced skill mirrors, update related index/README files and run:

```sh
sh .agents/scripts/verify-agent-dev.sh protocol
```
