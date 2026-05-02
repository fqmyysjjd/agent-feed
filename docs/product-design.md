# Product Design

Date: 2026-04-30

## Product Goal

Agent Feed helps developers install and maintain a repeatable AI development protocol in any repository so AI-assisted engineering work is more reliable, verifiable, and recoverable.

The product should answer:

1. What should an AI agent read first?
2. What is the current task boundary and stopping condition?
3. Where do reusable AI development rules live?
4. Where do user-maintained project-specific constraints live?
5. How are long-session conclusions preserved without turning chat into a transcript?
6. What checks prove that protocol assets and generated adapters are healthy?
7. How do Codex, Claude Code, and Cursor consume the same canonical protocol without duplicating rules?

## Target Users

1. Solo developers using multiple AI coding tools on the same repository.
2. Small teams trying to make AI-generated implementations, reviews, and fixes more predictable.
3. Project owners who want to extract implicit engineering rules into a reusable protocol.

## Product Positioning

Agent Feed is not:

1. A coding agent.
2. A spec-generation framework.
3. A replacement for AGENTS.md, CLAUDE.md, Cursor rules, or tool-native skills.
4. A compatibility matrix that copies every rule into every AI client folder.

Agent Feed is:

1. A protocol initializer.
2. A client-adapter generator.
3. A consistency checker.
4. A guided CLI for installing, syncing, checking, extending, and diagnosing AI development assets.

## User-Facing Outcome

A first-time project owner should be able to understand four things quickly:

1. What problem Agent Feed solves.
2. What files it installs and why those files exist.
3. How to initialize and verify a project safely.
4. Where to read the full protocol flow when they want the system-level explanation.

That is why the repository should keep `README.md` short, product-facing, and heavily linked into the deeper docs set instead of trying to explain every rule inline.

## Canonical Model

Generated repositories should treat this as the canonical tool-neutral source:

```text
AGENTS.md
.agents/
  rules/
  project/
  domain/
  session-state/
  skills/
  scripts/
  agents/
```

Client-specific files are adapters generated from the canonical source:

```text
CLAUDE.md
.claude/skills/
.cursor/rules/agent-feed.mdc
```

Codex does not need a generated project-local `.codex/skills` mirror because Codex can consume `AGENTS.md` and `.agents/skills` directly.

## MVP Contract

The next MVP should support:

```sh
agent-feed
agent-feed init [path]
agent-feed sync [path]
agent-feed index-skills [path]
agent-feed skill-hub [path]
agent-feed check [path]
agent-feed status [path]
agent-feed preview [path]
agent-feed upgrade [path]
agent-feed env status [path]
agent-feed env setup [path]
agent-feed env print
agent-feed env uninstall
agent-feed --version
agent-feed -v
```

Short aliases may be added:

```sh
agent-feed i
agent-feed c
agent-feed s
```

All path arguments are optional. When omitted, commands operate on the current directory.

## Interactive Experience

The CLI should provide polished interactive flows when running in a TTY:

1. Rich welcome panel and status tables.
2. Keyboard checkbox multi-select for clients:
   - Codex
   - Claude
   - Cursor
3. Keyboard checkbox multi-select for checks:
   - structure
   - skills
   - references
   - session
   - codex
   - claude
   - cursor
   - scripts
4. Clear write previews before init/sync.
5. Human-readable failure summaries with exact next commands.

The same commands must remain deterministic for scripts:

```sh
agent-feed env setup --dry-run
agent-feed init . --clients all -y
agent-feed check . --checks all --json
agent-feed sync . --clients claude,cursor --dry-run
```

## Product Principles

1. Keep `AGENTS.md` thin and canonical.
2. Keep reusable rules under `.agents/rules/`.
3. Keep user-maintained project constraints under `.agents/project/`.
4. Keep domain facts under `.agents/domain/`.
5. Keep session-state mutable, local, compact, and ignored by git.
6. Generate client adapters instead of duplicating source-of-truth content.
7. Refuse unsafe merges into existing AI instruction assets.
8. Validate before claiming the protocol is healthy.
9. Support both humans and automation: interactive prompts plus complete flags.
10. Require `.agents/project/README.md` as the index for project-specific customization.
11. Update installed protocols non-destructively: add missing files and update managed reusable assets, but do not delete local files or overwrite user-maintained project/domain constraints.
12. Keep external trust state in a user-level persistent home, not in the package installation directory or target project.
13. Treat public skill import as extension, not authority: curated hubs may add methods, but imported skills default to `trust: custom` and remain lower priority than project rules.

## Required Client Adapters

| Client | Adapter | Behavior |
| --- | --- | --- |
| Codex | none beyond canonical files | Check `AGENTS.md` and `.agents/skills`; do not create `.codex/skills` by default |
| Claude Code | `CLAUDE.md`, `.claude/skills/` | `CLAUDE.md` must contain `@AGENTS.md`, `.claude/skills`, and `.agents/`; skills mirror `.agents/skills` |
| Cursor | `.cursor/rules/agent-feed.mdc` | Always rule that points Cursor to `AGENTS.md` and `.agents/` |

## Mature Product Gaps

### CLI UX

1. Main flows now have interactive prompts, focused help output, status next steps, and readable preview diffs.
2. Errors use Rich panels and key status/check paths now print next actions, but command-specific remediation guidance can continue to improve.
3. Non-TTY behavior should stay deterministic and should never unexpectedly prompt.
4. `check`, `status`, `preview`, and `upgrade` need a user-facing boundary review because they now partially overlap.
5. `custom` verification must feel project-owned, so users should edit `.agents/project/verification-commands.sh` instead of patching the generated verifier directly.

### Adapter Correctness

1. Codex correctly uses canonical assets directly.
2. Claude `CLAUDE.md` is validated by required references instead of exact managed-template equality, while `.claude/skills` remains a generated mirror.
3. Exact pruning of stale generated adapter files should remain separate from non-destructive `upgrade`.

### Validation

1. Check categories are selectable.
2. Client checks are separated from canonical protocol checks.
3. Generated adapter repair belongs to `sync`; protocol refresh belongs to `upgrade`; diagnostics belong to `check` and `status`.
4. JSON output exists for `check` and `status`; other commands may need machine-readable output later.

### Upgrade

1. Installed projects include `.agents/agent-feed.json` metadata with the Agent Feed version, template name, project name, and verification profile.
2. `preview` shows init writes for new targets and full upgrade diffs for installed targets.
3. `upgrade` compares managed reusable assets against the current bundled template.
4. `upgrade` creates missing template files and updates managed reusable assets.
5. `upgrade` does not compare or overwrite existing `.agents/project/` and `.agents/domain/` files because those are user-maintained.
6. `upgrade` does not delete files; exact pruning remains a separate explicit operation such as `sync --force-generated`.
7. `status` and `upgrade` should default to a compact Changes summary; full diffs should be opt-in with a single `v` keypress in interactive terminals or `--diff` in scripts.

### Architecture

1. The current `cli.py` is too large.
2. Commands, adapters, prompts, templates, and checks should be separate modules.
3. Generated-file markers and `.agents/agent-feed.json` should define safe update boundaries.
4. Prompt protocol gaps around task classification, reuse-before-build, and session cleanup are now part of the reusable template rules.

### Command Boundary Review

Current command intent:

1. `check`: validates selected protocol and adapter health; exits non-zero on failures.
2. `status`: shows a compact installed-project Changes table for humans and keeps JSON health output for automation.
3. `preview`: shows init writes for new targets or full upgrade diffs for installed targets.
4. `upgrade`: applies non-destructive template refresh and selected adapter refresh.
5. `index-skills`: regenerates the skill index after manual, local, or imported skill changes and maintains accepted AI asset hashes.
6. `skill-hub`: searches curated public skill repositories, uses `GITHUB_TOKEN` or the user-level `settings.github_token` when available, previews selected skill files, installs selected skills as `trust: custom`, then indexes automatically.
7. `config set`: reapplies project-visible `.agents/agent-feed.json` settings to managed generated assets, skill metadata defaults, and configured client adapters without requiring a broader product decision.
8. `env uninstall`: removes user-level environment binding and optionally the user-level Agent Feed home.

Potential overlap:

1. `status` and `upgrade --dry-run` now share the compact Changes-table interaction.
2. `status --json` and `check --json` may overlap for automation.

`index-skills` is intentionally separate from `sync`: it updates the canonical `.agents/skills/README.md` index and the external `$AGENT_FEED_HOME/config.json` trust state, while `sync` updates generated client adapters.

`.agents/agent-feed.json` is the project-visible metadata and settings contract. User-level secrets and accepted hash state stay in `$AGENT_FEED_HOME/config.json`; project settings such as session-state limits, skill metadata defaults, and Claude reference checks stay in the repository and are applied with `agent-feed config set`.

Do not remove commands without a public CLI decision. The near-term fix is clearer help text and docs; consolidation is a product contract decision.

`doctor` was removed from the public/product contract because it duplicated
`check` without performing deterministic sync. Keeping the surface smaller is
more useful than exposing a second diagnostic command with unclear ownership.

## Documentation Surface

The public docs should form a simple ladder:

1. `README.md`: value proposition, first commands, trust model, team workflow, and doc map.
2. `docs/ai-development-protocol-flow.md`: end-to-end AI governance loop.
3. `docs/template-model.md`: generated structure, trust ownership, and adapter model.
4. `docs/cli-product-plan.md`: implementation-facing command behavior and UX notes.
5. `docs/open-source-readiness.md`: release and repo-readiness tracking, not first-screen onboarding.

## Recommended Milestones

1. M1: Product-grade CLI design, implemented prototype, and package build baseline.
2. M2: Command boundary hardening for `check/status/preview/upgrade/sync/skill-hub`.
3. M3: Session-state cleanup enforcement and better archival guidance.
4. M4: More language/profile support only after the command boundary is stable.
5. M5: Release packaging workflow and published documentation site.

Detailed implementation plan: `docs/cli-product-plan.md`.
