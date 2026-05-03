# Source Of Truth

Define durable fact ownership for Agent Feed.

## Ownership

1. CLI command behavior:
   - `src/agent_feed/cli.py`
   - tests under `tests/`
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
