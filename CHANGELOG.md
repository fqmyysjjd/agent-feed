# Changelog

All notable changes to Agent Feed are tracked here.

This project is pre-1.0. Minor versions may still adjust command behavior, generated template structure, and verification gates while the protocol stabilizes.

## Unreleased

### Added

- GitHub Actions CI for tests, linting, type checking, package build, and CLI smoke checks.
- GitHub issue templates and pull request template.
- Contribution and security policies.
- Code of Conduct.
- Basic generated-output example for first-time repository visitors.

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
