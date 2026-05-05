# Architecture Boundaries

This file defines repository-specific architecture boundaries for Agent Feed.

Agent Feed is a local CLI and template package for installing AI engineering protocol assets into other repositories.

## Non-Negotiable Boundaries

1. `agent-feed` is the CLI entry point and must remain usable with standard Python packaging; npm is allowed only as a thin wrapper that delegates to the Python CLI.
2. `src/agent_feed/templates/standard/` is the canonical source for generated protocol assets.
3. Generated client folders such as `.codex/` and `.claude/` are mirrors, not canonical sources.
4. The installed CLI must not require network access for `init`, `check`, `sync`, `status`, `preview`, or `upgrade`.
5. The standard template must keep reusable rules separate from project-specific constraints.
6. The standard template must not hard-code Fast Agent runtime product constraints.
7. The root `.agents/` directory is for developing this CLI project; template `.agents/` files live under `src/agent_feed/templates/standard/`.

## Stop Rules

Stop and ask for confirmation when a task requires:

1. A new runtime dependency for the CLI.
2. A breaking CLI command or argument change.
3. A change to the template responsibility model.
4. A change that makes `init`, `check`, `sync`, `status`, `preview`, or `upgrade` require network access after installation.
5. A change that mixes project-specific product constraints into reusable rules.
