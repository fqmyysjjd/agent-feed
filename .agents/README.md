# AI Development Engineering

`.agents/` is the project-level AI engineering system for developing this repository with AI coding agents.

These files guide AI assistants while they design, implement, review, and fix the codebase. They are not product runtime rules and should not be treated as user-facing behavior.

## Layer Responsibilities

1. `agent-feed.json`: installed Agent Feed template metadata and non-secret project settings used by preview, upgrade, and config set.
2. `rules/`: reusable AI development constraints and gates.
3. `project/`: user-maintained project customization layer for current repository constraints.
4. `session-state/`: local JSON files for active long-running conversations.
5. `domain/`: stable project/domain knowledge.
6. `skills/`: task-specific workflows, indexed by `.agents/skills/README.md`.
7. `.agents/scripts/`: protocol helper scripts for index sync, client adapter sync, validation, and verification.
8. `agents/`: narrow specialist profiles for delegated checks or worker tasks.

## Highest-Priority Rule

Always load `.agents/rules/outcome-boundary.md` and `.agents/rules/decision-gates.md` before continuing design, development, review, or fix work.

The current task boundary decides when to stop. Decision gates decide when unconfirmed choices require human confirmation. Other rules and skills serve those boundaries.

## Current Rules

1. `outcome-boundary.md`: near-term task result, Task Brief, task class gate, stopping condition, and anti-drift rules.
2. `decision-gates.md`: human confirmation rules for unconfirmed choices that affect future development results.
3. `context-loading.md`: startup/context-compression loading order and task routing.
4. `session-state.md`: final handoff gate, Context Capsule format, compact JSON handoff cards, carry-forward cleanup, and optional multi-session pointer rules.
5. `testing-gates.md`: test selection, minimum coverage, failure handling, and verification evidence rules.
6. `evidence-gates.md`: external research sourcing, classification, and adoption rules.
7. `change-risk-gates.md`: project-level change risk classes and verification command rules.
8. `development-workflow.md`: Task Brief implementation addendum, reuse-before-build discipline, comment/docstring discipline, gap handling, and verification ladder.
9. `review-gates.md`: code/design review gates and final handoff routing into session-state.
10. `git-collaboration.md`: git diff, staging, commit, merge, and review handoff rules.

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
  -> skills/README.md
  -> skills/*
  -> .agents/scripts/*
  -> agents/* when delegation is useful
```

Rules may reference skills only for routing. Skills may reference rules, project constraints, and domain docs as required reading. Domain docs should avoid referencing skills unless explaining usage context.

`.agents/skills/README.md` is the required generated index for skills. When a skill is added, removed, renamed, or its frontmatter changes, run `agent-feed index-skills` or `sh .agents/scripts/index-skills.sh`, then sync configured client adapters.

Custom or imported skills are allowed when they serve the current result, but they remain lower priority than the current user request, the Task Brief, `AGENTS.md`, `.agents/rules/`, `.agents/project/`, and `.agents/domain/`. If a custom skill suggests risky commands, network access, destructive changes, or writes outside the Task Brief, inspect the action first and apply `.agents/rules/change-risk-gates.md`.

Before using built-in or reviewed skills, run `sh .agents/scripts/check-agent-trust.sh`. `AGENT_FEED_HOME` must be set, and trusted AI asset hashes are stored in `$AGENT_FEED_HOME/config.json` outside the current project. If the trust gate reports changed `.agents/skills/*/SKILL.md` or `.agents/scripts/*` hashes, the highest-priority Agent Feed rule requires stopping before those files are used. Tell the user the concrete changed Agent Feed files, inspect with `agent-feed preview`, and accept intentional changes only with `agent-feed index-skills -y`.

`.agents/agent-feed.json` may define non-secret project settings such as session-state carry-forward limits, default metadata for newly imported skills, required Claude adapter references, and the active verification profile. Change these values with `agent-feed config set` so affected managed assets and external trust state are refreshed in the same step. Do not store tokens or accepted hashes in project-local settings.

`.agents/project/README.md` is the required index for the project customization layer. When a file under `.agents/project/` is added, removed, renamed, or materially changed, update that README in the same task.

## Consistency Check

After changing AI engineering protocol files, rule names, project constraint names, skill names, `.agents/` links, session-state JSON, or synced skill mirrors, update related index/README files and run:

```sh
sh .agents/scripts/verify-agent-dev.sh docs
```
