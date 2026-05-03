# Project Structure

This file defines repository-specific source layout and placement constraints for Agent Feed.

```txt
src/agent_feed/
  cli.py                    CLI command wiring
  adapters/                 Codex, Claude, and Cursor generated adapters
  checks.py                 protocol and adapter validation
  skill_index.py            skill index rendering and freshness checks
  console.py                Rich output helpers
  prompts.py                InquirerPy prompt helpers
  templates/standard/       canonical generated protocol template
docs/                       public protocol and template docs
tests/                      CLI smoke and behavior tests
.agents/                    AI engineering protocol for this repo
.agents/scripts/            generated repo-local protocol scripts
```

## Placement Rules

1. CLI command wiring belongs in `src/agent_feed/cli.py`; adapters, checks, prompts, and console output belong in focused modules.
2. Generated assets belong under `src/agent_feed/templates/standard/`.
3. Root `.agents/` guides development of this CLI repo; it is not the generated template source.
4. Codex consumes `AGENTS.md` and `.agents/skills` directly; Claude and Cursor adapters are generated from canonical assets.
5. Public protocol and template explanations belong in `docs/`; keep transient planning, market research, and README drafts out of the release docs.
6. Tests should exercise CLI behavior through public command functions or installed entry points.
7. Do not add network-dependent behavior to template initialization.
