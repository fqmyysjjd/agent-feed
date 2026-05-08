# Source Of Truth

Define durable fact ownership for Agent Feed.

## Owns

This file owns durable source-of-truth mapping for CLI behavior, generated
templates, product positioning, local AI development rules, client adapters,
and recovery behavior.

## Read When

Read this before moving canonical ownership, changing generated asset recovery,
changing adapter generation, changing product/documentation ownership, or
deciding whether a fact belongs in source code, docs, `.agents/project/`,
`.agents/domain/`, or generated adapters.

## Evidence

1. `src/agent_feed/cli.py`: Python CLI behavior owner.
2. `src/agent_feed/templates/standard/`: generated template owner.
3. `README.md` and `docs/`: public product and protocol docs.
4. `AGENTS.md` and `.agents/`: local AI development rules for this repo.
5. `CLAUDE.md`, `.claude/skills`, and `.cursor/rules/agent-feed.mdc`: generated client adapters.

## Ownership

1. CLI command behavior:
   - Python runtime: `src/agent_feed/cli.py`
   - Python tests under `tests/`
   - npm wrapper under `npm/` may only delegate to the Python runtime
2. Generated protocol template:
   - `src/agent_feed/templates/standard/`
3. Product intent and market positioning:
   - `README.md`
   - `docs/ai-development-protocol-flow.md`
   - `docs/template-model.md`
4. Local AI development rules for this repo:
   - root `AGENTS.md`
   - root `.agents/`
   - root `.agents/scripts/`
5. Generated client adapters:
   - `CLAUDE.md`
   - `.claude/skills`
   - `.cursor/rules/agent-feed.mdc`
   - generated from `AGENTS.md` and `.agents/`

## Recovery Principle

If generated files drift, recover from the canonical source:

1. For product templates, regenerate from `src/agent_feed/templates/standard/`.
2. For root client adapters, run `sh .agents/scripts/sync-agent-assets.sh`.
3. For long-running AI session conclusions, use `.agents/session-state/`.
