# Project Structure

This file defines repository-specific source layout and placement constraints for Agent Feed.

## Owns

This file owns source layout, file placement, generated-template placement,
adapter placement, and test placement constraints for Agent Feed.

## Read When

Read this before adding, moving, importing, generating, deleting, or relocating
files, modules, tests, docs, protocol assets, or client adapters.

## Evidence

1. `src/agent_feed/`: Python package and CLI modules.
2. `src/agent_feed/templates/standard/`: canonical generated template assets.
3. `npm/`: npm wrapper package files.
4. `tests/`: public CLI and behavior tests.
5. `docs/`: public user and protocol documentation.

```txt
src/agent_feed/             Python CLI, checks, prompts, adapters, trust, settings, and templates
npm/                        thin npm wrapper that delegates to the Python CLI
tests/                      Python CLI smoke and behavior tests
package.json                npm wrapper package contract
docs/                       public protocol and template docs
.agents/                    AI engineering protocol for this repo
.agents/scripts/            generated repo-local protocol scripts
```

## Placement Rules

1. Python CLI command wiring belongs in `src/agent_feed/cli.py`; adapters, checks, prompts, and console output belong in focused modules.
2. npm code belongs in `npm/` and must remain a thin packaging wrapper. It must not reimplement Agent Feed CLI behavior.
3. Generated protocol assets belong under `src/agent_feed/templates/standard/`.
4. Root `.agents/` guides development of this CLI repo; it is not the generated template source.
5. Codex consumes `AGENTS.md` and `.agents/skills` directly; Claude and Cursor adapters are generated from canonical assets.
6. Public protocol and template explanations belong in `docs/`; keep transient planning, market research, and README drafts out of the release docs.
7. Tests should exercise CLI behavior through public command functions or installed Python entry points.
8. Do not add network-dependent behavior to template initialization.
