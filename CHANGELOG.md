# Changelog

All notable changes to Agent Feed are tracked here.

This project uses semantic versioning. Patch releases preserve the public command surface and generated-template contracts unless the changelog calls out a migration.

## Unreleased

### Added

- Added a public trust model document explaining external hash storage, skill trust levels, custom-skill boundaries, and GitHub token lookup order.
- Added automatic `gh auth token` fallback for `agent-feed skill-hub` when `GITHUB_TOKEN` and saved `settings.github_token` are not available.
- Added direct regression coverage for asset trust drift, missing GitHub CLI fallback, and upgrade idempotency.

### Changed

- Expanded the usage guide with `env print`, `env uninstall`, and GitHub CLI token setup guidance.
- Tightened the design review gate so document reviews must check user-goal fit, result support, and result-affecting gaps instead of only polish or next-step readiness.

## 1.1.5 - 2026-05-08

### Added

- Added install-source-aware update notices so `upgrade` can recommend npm,
  uv, pipx, or Homebrew update commands.
- Added the `specialist-router` skill for selecting optional, imported, custom,
  or specialized skills without letting them override the core protocol.

### Changed

- Tightened project/domain recall indexes and review guidance so custom
  repository rules can be loaded by trigger instead of by reading everything.
- Kept the npm package as a thin Python CLI wrapper instead of maintaining a
  second CLI implementation.

## 1.1.4 - 2026-05-05

### Fixed

- Reused the skill-hub GitHub token retry flow when selected skill downloads hit GitHub 403 or rate-limit responses after search succeeds.
- Normalized GitHub API download HTTP errors into the same user-friendly `GITHUB_TOKEN` and `settings.github_token` guidance used during skill search.

## 1.1.3 - 2026-05-05

### Changed

- Improved `agent-feed init` completion feedback so legacy AI instruction backups print the concrete `.feed-backup/<timestamp>` directory.
- Narrowed Agent Feed reference checks to active protocol assets and ignored `.feed-backup/` migration archives and repository history docs.
- Synced the packaged standard template script with the updated reference-check behavior.

## 1.1.2 - 2026-05-05

### Changed

- Synced Python package metadata, npm package metadata, and template `agent_feed_version` fields to the current `v1.1.2` release tag.
- Updated `scripts/sync-release-version.py` so future release-version syncs also update `.agents/agent-feed.json`.

## 1.1.0 - 2026-05-05

### Added

- Added a practical Agent Feed usage guide covering setup, first AI prompts, project/domain customization, skill management, upgrades, and troubleshooting.
- Added user-facing prompt examples for bootstrapping project/domain rules from templates, migrating legacy AI instructions from `.feed-backup/`, and keeping project/domain README indexes current.

### Changed

- Moved the usage guide to `docs/usage-guide.md` and made it prominent in the English and Chinese README hero sections.

## 1.0.1 - 2026-05-05

### Fixed

- Published the npm wrapper as `@yysjjd/agent-feed` because npm blocks the unscoped `agent-feed` package name as too similar to an existing package.
- Updated English and Chinese install instructions to use `npm install -g @yysjjd/agent-feed` while keeping the installed CLI command as `agent-feed`.
- Removed source-checkout development instructions from the user-facing Quick Start.

## 1.0.0 - 2026-05-03

### Added

- GitHub Actions CI for tests, linting, type checking, package build, and CLI smoke checks.
- GitHub Release publishing workflow for PyPI and npm.
- GitHub issue templates and pull request template.
- Contribution and security policies.
- Code of Conduct.
- Basic generated-output example for first-time repository visitors.
- TypeScript npm CLI implementation for `npm install -g agent-feed`.

### Changed

- README now explains the problem, scope, protocol flow, safety model, and current maturity more directly for open-source visitors.

## 0.1.1 - 2026-05-01

### Added

- `agent-feed init` for installing `AGENTS.md`, `.agents/` assets, and selected client adapters.
- `agent-feed check` for validating required assets, references, session-state JSON, skill metadata, and selected adapters.
- `agent-feed sync` for regenerating selected client adapters from canonical assets.
- `agent-feed upgrade` for non-destructive template refreshes.
- `agent-feed preview` for init write plans and installed-project upgrade diffs.
- `agent-feed status` for checking canonical assets and client adapter state.
- `agent-feed uninstall` for removing only managed/generated files.
- Python, Node, custom, and docs-only verification profiles.
- Skill index generation and drift detection.
- Claude Code and Cursor client adapters.

### Changed

- Renamed the package and command to `agent-feed`.
- Kept maintenance commands hidden from the public help surface.
- Moved agent helper scripts into `.agents/scripts/` in generated projects.
