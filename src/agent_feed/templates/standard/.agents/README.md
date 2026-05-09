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

## Priority And Gates

Rule priority and Mandatory Gates are owned by `AGENTS.md`. This README does not restate them — read `AGENTS.md` for the canonical ordering.

This README only indexes which rule files exist under `rules/`, what each owns, and how layers reference each other.

## Current Rules

| File | Owns |
| --- | --- |
| `outcome-boundary.md` | Near-term task result, Task Brief, task class gate, stopping condition, anti-drift rules, and the Light Resume Checklist anchor. |
| `decision-gates.md` | Human confirmation rules for unconfirmed choices that affect future development results. |
| `context-loading.md` | Startup/context-compression loading order and the single task routing map. |
| `session-state.md` | Final handoff gate, Context Capsule format, compact JSON handoff cards, carry-forward cleanup, and multi-session pointer rules. |
| `testing-gates.md` | Test selection, minimum coverage, failure handling, and verification evidence rules. |
| `evidence-gates.md` | External research sourcing, classification, and adoption rules. |
| `change-risk-gates.md` | Project-level change risk classes, non-negotiable safety lines, and verification command rules. |
| `engineering-architecture.md` | Repository-agnostic ownership, placement, dependency-direction, abstraction, and reuse gate. |
| `development-workflow.md` | Task Brief implementation addendum, reuse-before-build discipline, comment/docstring discipline, gap handling, and verification ladder. |
| `review-gates.md` | Code/design review gates and final handoff routing into session-state. |
| `git-collaboration.md` | Git diff, staging, commit, merge, and review handoff rules. |

## Reference Direction

The arrows below describe *file-level* reference relationships (who may import what), not gate priority — gate priority lives in `AGENTS.md`.

```txt
AGENTS.md
  -> rules/*           (canonical reusable constraints)
  -> .agents/README.md (this index)
  -> project/*         (repository-specific constraints; indexed by project/README.md)
  -> domain/*          (stable domain knowledge; indexed by domain/README.md)
  -> skills/README.md
  -> skills/*          (task workflows)
  -> session-state/<session_id>.json   when long-running session state exists
  -> scripts/*
  -> agents/*          when delegation is useful
```

Rules may reference skills only for routing. Skills may reference rules, project constraints, and domain docs as required reading. Domain docs should avoid referencing skills unless explaining usage context.

`.agents/skills/README.md` is the required generated index for skills. When a skill is added, removed, renamed, or its frontmatter changes, run `agent-feed index-skills` or `sh .agents/scripts/index-skills.sh`, then sync configured client adapters.

Custom or imported skills are allowed when they serve the current result, but they remain lower priority than the current user request, the Task Brief, `AGENTS.md`, `.agents/rules/`, `.agents/project/`, and `.agents/domain/`. Use `.agents/skills/specialist-router/SKILL.md` to select optional, imported, custom, or specialized skills from the index. If a custom skill suggests risky commands, network access, destructive changes, or writes outside the Task Brief, inspect the action first and apply `.agents/rules/change-risk-gates.md`.

Before using built-in or reviewed skills, run `sh .agents/scripts/check-agent-trust.sh`. `AGENT_FEED_HOME` must be set, and trusted AI asset hashes are stored in `$AGENT_FEED_HOME/config.json` outside the current project. If the trust gate reports changed `.agents/skills/*/SKILL.md` or `.agents/scripts/*` hashes, the highest-priority Agent Feed rule requires stopping before those files are used. Tell the user the concrete changed Agent Feed files, inspect with `agent-feed preview`, and accept intentional changes only with `agent-feed index-skills -y`.

`.agents/agent-feed.json` may define non-secret project settings such as session-state carry-forward limits, default metadata for newly imported skills, required Claude adapter references, and the active verification profile. Change these values with `agent-feed config set` so affected managed assets and external trust state are refreshed in the same step. Do not store tokens or accepted hashes in project-local settings.

`.agents/project/README.md` is the required index for the project customization layer. When a file under `.agents/project/` is added, removed, renamed, or materially changed, update that README in the same task.

## Consistency Check

After changing AI engineering protocol files, rule names, project constraint names, skill names, `.agents/` links, session-state JSON, or synced skill mirrors, update related index/README files and run:

```sh
sh .agents/scripts/verify-agent-dev.sh docs
```
