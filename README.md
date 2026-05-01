# Agent Feed

Agent Feed is a CLI for installing and maintaining a reusable AI engineering protocol in software projects.

It is not an AI coding agent and not a spec-generation framework. It gives Codex, Claude Code, Cursor, and similar tools a shared project protocol:

1. `AGENTS.md` as the canonical repository entry contract.
2. `.agents/rules/` for reusable development gates.
3. `.agents/project/` for user-maintained project-specific constraints.
4. `.agents/domain/` for stable project knowledge.
5. `.agents/session-state/` for long-running conversation continuity.
6. `.agents/skills/` for task-specific agent workflows.
7. `.agents/scripts/` for agent-facing sync and verification helpers.
8. Generated client adapters for Claude and Cursor.

## Install

After release:

```sh
uv tool install agent-feed
# or
pipx install agent-feed
```

Before release, run it from this checkout:

```sh
uv run agent-feed welcome
```

## Quick Start

```sh
cd /path/to/project
agent-feed init --interactive
agent-feed check
agent-feed status
```

All path arguments are optional. When omitted, commands operate on the current directory.

## Commands

```sh
agent-feed
agent-feed welcome
agent-feed --version
agent-feed init [path] [--project-name NAME] [--clients codex,claude,cursor|all|none] [--profile python|node|custom|none]
agent-feed update [path] [--clients codex,claude,cursor|all|none] [--profile python|node|custom|none] [--dry-run]
agent-feed upgrade [path] [--clients codex,claude,cursor|all|none] [--profile python|node|custom|none] [--dry-run]
agent-feed sync [path] [--clients codex,claude,cursor|all|none]
agent-feed check [path] [--checks structure,skills,references,session,scripts,codex,claude,cursor|all]
agent-feed status [path] [--json]
agent-feed doctor [path] [--fix]
agent-feed preview [path] [--clients codex,claude,cursor|all|none] [--profile python|node|custom|none]
agent-feed uninstall [path] [--dry-run] [--yes]
```

`agent-feed --version` prints both the executable path and imported package path. Use it
when a globally installed command appears stale compared with the current checkout.

Short aliases:

```sh
agent-feed i
agent-feed s
agent-feed c
```

Compatibility alias:

```sh
agent-feed sync-skills
```

## Client Adapters

Agent Feed keeps `AGENTS.md` and `.agents/` canonical.

| Client | Generated adapter | Behavior |
| --- | --- | --- |
| Codex | none | Codex uses `AGENTS.md` and `.agents/skills` directly |
| Claude Code | `CLAUDE.md`, `.claude/skills/` | `CLAUDE.md` imports `@AGENTS.md`; skills mirror `.agents/skills` |
| Cursor | `.cursor/rules/agent-feed.mdc` | Always rule points Cursor to `AGENTS.md` and `.agents/` |

`--project-name` is a display name inserted into generated templates, mainly the `AGENTS.md` heading. It does not need to match the Python package name, Git repository name, or folder name. When omitted, Agent Feed uses the target folder name.

`--profile` selects the generated project code gate:

| Profile | Intended project | Code verification |
| --- | --- | --- |
| `python` | Python projects | prefers `uv`, falls back to `python3`, then `python`; runs `pytest`, plus `ruff`/`mypy` when installed |
| `node` | Node projects | prefers `pnpm`, falls back to `npm`; runs `test`, plus `lint`/`typecheck`/`build` scripts when present |
| `custom` | Any project with custom commands | Fails until `.agents/scripts/verify-agent-dev.sh` is edited |
| `none` | AI docs/assets only repositories | No code gate configured |

`init` intentionally fails when the target already contains `AGENTS.md` or non-empty `.agents`. It also refuses to overwrite unmanaged selected client adapters. This keeps entrypoints, rules, skills, project constraints, session-state boundaries, and client-specific files clean instead of merging unknown existing assets.

`preview` shows the init write plan for projects that do not yet have Agent Feed installed. When the target already has `AGENTS.md` and `.agents/`, it switches to update mode and prints diffs against the bundled template. This makes version drift visible before writing.

`update` refreshes an installed protocol from the bundled template without deleting local files. It updates managed reusable assets, creates missing template files, and skips existing user-maintained `.agents/project/` and `.agents/domain/` files. `upgrade` is an alias for `update`.

`sync` regenerates selected client adapters from canonical assets. Use `--force-generated` only for managed generated files.

`uninstall` removes only files Agent Feed can identify as managed or generated. It prints the removal plan first, skips unmanaged user files, and requires `--yes` in non-interactive shells. Use `--dry-run` before deleting:

```sh
agent-feed uninstall . --dry-run
agent-feed uninstall . --yes
```

## Product Positioning

Agent Feed's target role is an AI engineering protocol initializer and adapter manager: the reliability layer between project knowledge and AI execution.

1. Outcome boundary before deep work.
2. Human decision gates before unconfirmed contract changes.
3. Task Brief before edits.
4. Session-state continuity across context compression.
5. Verification gates tied to the task boundary.
6. Tool-native adapters without duplicating source-of-truth rules.
7. Project-specific constraint placeholders without mixing them into reusable rules.

## Current State

This is a working prototype:

1. The CLI can initialize a target project with protocol assets.
2. It can generate Claude and Cursor adapters.
3. It can validate required files, structure, `.agents` references, session-state JSON shape, skill names, scripts, and selected client adapters.
4. It supports interactive init, check, and sync selection.
5. It refuses unsafe initialization over existing `AGENTS.md`, `.agents`, or unmanaged selected client adapters.
6. It can generate Python, Node, custom, or docs-only verification profiles.
7. It can preview and apply non-destructive updates for installed protocol assets.

Not yet mature:

1. Brownfield migration/adoption for projects that already have AI instruction assets.
2. Monorepo verification profiles.
3. CI integration.
4. Release packaging workflow and published documentation site.
