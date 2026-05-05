# Changelog

All notable changes to Agent Feed are tracked here.

This project uses semantic versioning. Patch releases preserve the public command surface and generated-template contracts unless the changelog calls out a migration.

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
