# Live Protocol Example

This example shows the AI development protocol that is actively used to build this repository.

Unlike [Basic Generated Output](../basic-output.md), this is not a frozen copy of generated files. It points to the live root protocol files so readers can inspect the actual system Agent Feed is using while it is developed.

## Live Directory Shape

```txt
agent-feed/
  AGENTS.md
  CLAUDE.md
  .agents/
    README.md
    agent-feed.json
    agents/
      README.md
    domain/
      README.md
      concepts.md
      contracts.md
      source-of-truth.md
    project/
      README.md
      architecture-boundaries.md
      milestones.md
      project-structure.md
      verification-commands.sh
    rules/
      change-risk-gates.md
      context-loading.md
      decision-gates.md
      development-workflow.md
      evidence-gates.md
      git-collaboration.md
      outcome-boundary.md
      review-gates.md
      session-state.md
      testing-gates.md
    scripts/
      check-agent-assets.sh
      check-agent-trust.sh
      index-skills.sh
      sync-agent-assets.sh
      verify-agent-dev.sh
    session-state/
      README.md
      schema.json
    skills/
      README.md
      concept-review/
      design-review/
      guidance-promoter/
      project-architecture/
      project-development/
      project-fix/
      project-review/
      skill-maintainer/
```

## Entry Files

| File | Role | What it demonstrates |
| --- | --- | --- |
| [`../../AGENTS.md`](../../AGENTS.md) | Canonical AI entry contract | Startup policy, rule priority, responsibility boundaries, and mandatory gates. |
| [`../../CLAUDE.md`](../../CLAUDE.md) | Claude Code adapter | A thin generated adapter that delegates back to `AGENTS.md` instead of duplicating the protocol. |
| [`../../.agents/README.md`](../../.agents/README.md) | Protocol index | The layer map and maintenance contract for `.agents/`. |
| [`../../.agents/skills/README.md`](../../.agents/skills/README.md) | Skill index | How task-specific workflows are discovered by name, description, source, and trust level. |

## How The Live Protocol Starts

When an AI assistant begins real work in this repository, the entry path is:

```txt
AGENTS.md
  -> .agents/rules/outcome-boundary.md
  -> .agents/rules/decision-gates.md
  -> .agents/rules/context-loading.md
  -> .agents/rules/session-state.md
  -> .agents/rules/testing-gates.md
  -> .agents/README.md
  -> .agents/skills/README.md
  -> .agents/project/README.md
  -> .agents/domain/README.md
```

The important behavior is not the directory tree itself. The behavior is the loop:

1. Recover the current outcome boundary.
2. Decide whether the task is design, development, fix, review, or protocol work.
3. Load only the rules, project constraints, domain docs, and skills needed for that task.
4. Stop before unconfirmed choices become durable project behavior.
5. Verify the actual changed surface before reporting completion.

## Project Layer Example

The files under [`../../.agents/project/`](../../.agents/project/) are intentionally project-specific. They show how a repository customizes the reusable protocol without editing generic rules.

| File | Maintained fact |
| --- | --- |
| [`../../.agents/project/architecture-boundaries.md`](../../.agents/project/architecture-boundaries.md) | Agent Feed is a local CLI and template package; `src/agent_feed/templates/standard/` is the canonical generated template source; init/check/sync/status/preview must not require network. |
| [`../../.agents/project/project-structure.md`](../../.agents/project/project-structure.md) | Python CLI wiring belongs in `src/agent_feed/cli.py`; `npm/` only delegates to the Python CLI; generated template files belong under `src/agent_feed/templates/standard/`. |
| [`../../.agents/project/milestones.md`](../../.agents/project/milestones.md) | The local implementation phase and release-facing sequencing for this repository. |
| [`../../.agents/project/verification-commands.sh`](../../.agents/project/verification-commands.sh) | The project-owned custom verification hook when the project selects `verification_profile: custom`. |

This layer is the place for facts that would be wrong in another repository. For example, another project might put frontend code under `apps/web/`, require a database migration gate, or define a different ownership boundary for generated assets.

## Domain Layer Example

The files under [`../../.agents/domain/`](../../.agents/domain/) keep durable product and contract knowledge separate from workflow rules.

| File | Maintained fact |
| --- | --- |
| [`../../.agents/domain/concepts.md`](../../.agents/domain/concepts.md) | Agent Feed is a protocol installer, not an AI coding agent, spec framework, project manager, or runtime memory system. |
| [`../../.agents/domain/contracts.md`](../../.agents/domain/contracts.md) | Public CLI commands, generated template contract, upgrade behavior, and project settings ownership. |
| [`../../.agents/domain/source-of-truth.md`](../../.agents/domain/source-of-truth.md) | Which files own CLI behavior, generated template behavior, product intent, local AI rules, and generated client adapters. |

This layer is useful when the AI needs to understand the thing being built. In Agent Feed, it prevents CLI behavior, template responsibility, trust-state ownership, and adapter behavior from being invented from chat context.

## Skill Layer Example

The live skill index is [`../../.agents/skills/README.md`](../../.agents/skills/README.md). It maps a task to a workflow:

| Task | Typical skill |
| --- | --- |
| Architecture or module ownership decision | `project-architecture` |
| Implementation or refactor | `project-development` |
| Bug, failed test, or regression fix | `project-fix` |
| Diff or implementation review | `project-review` |
| README, protocol, AGENTS, rule, or skill review | `design-review` |
| Naming or concept drift review | `concept-review` |
| Skill creation, update, or index sync | `skill-maintainer` |

Skills are methods, not higher-priority rules. The current user request, Task Brief, `AGENTS.md`, `.agents/rules/`, `.agents/project/`, and `.agents/domain/` stay authoritative.

## Why This Example Exists

This example is meant to make the abstract protocol concrete:

1. `AGENTS.md` shows how the AI enters and prioritizes the system.
2. `.agents/rules/` shows reusable behavior gates.
3. `.agents/project/` shows what a real project customizes.
4. `.agents/domain/` shows how durable project knowledge is separated from workflow rules.
5. `.agents/skills/` shows how specific task methods are discovered without loading everything.

When adapting Agent Feed to another repository, copy the structure, not the Agent Feed-specific facts.
