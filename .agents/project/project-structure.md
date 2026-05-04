# Project Structure

This file defines repository-specific source layout and placement constraints for Agent Feed.

```txt
src/python/agent_feed/      Python CLI, checks, prompts, adapters, trust, and settings logic
src/node/src/               TypeScript Node CLI source
src/templates/standard/     canonical generated protocol template shared by both runtimes
tests/python/               Python CLI smoke and behavior tests
tests/node/                 TypeScript Node CLI tests
package.json                npm package contract
tsconfig.json               TypeScript build contract
docs/                       public protocol and template docs
.agents/                    AI engineering protocol for this repo
.agents/scripts/            generated repo-local protocol scripts
```

## Placement Rules

1. Python CLI command wiring belongs in `src/python/agent_feed/cli.py`; adapters, checks, prompts, and console output belong in focused modules.
2. Node CLI command wiring belongs in `src/node/src/`; keep runtime-specific implementation there instead of mixing it into Python modules.
3. Generated protocol assets belong under `src/templates/standard/` and are shared by both runtimes.
4. Root `.agents/` guides development of this CLI repo; it is not the generated template source.
5. Codex consumes `AGENTS.md` and `.agents/skills` directly; Claude and Cursor adapters are generated from canonical assets.
6. Public protocol and template explanations belong in `docs/`; keep transient planning, market research, and README drafts out of the release docs.
7. Tests should exercise CLI behavior through public command functions or installed entry points for the relevant runtime.
8. Do not add network-dependent behavior to template initialization.
