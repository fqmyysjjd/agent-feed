# Changelog

All notable changes to Agent Feed are tracked here.

This project uses semantic versioning. Patch releases preserve the public command surface and generated-template contracts unless the changelog calls out a migration.

## Unreleased

### Added

- Added an `upgrade` downgrade guard so older Agent Feed CLIs cannot rewrite projects last managed by newer versions unless `--allow-downgrade` is passed.
- Added a Light Resume Checklist anchor in `.agents/rules/outcome-boundary.md` so AGENTS.md and `context-loading.md` can route same-session resumes to a single short block, and wired `context-loading.md` Light Resume steps to that anchor instead of re-reading the entire rule.
- Added a "How This Rule Relates To Engineering Planning" section to `.agents/rules/engineering-architecture.md` and matching "Position In The Stack" notes in `engineering-planning` and `project-development` skills to clarify the rule/skill/workflow division.
- Added a `custom → reviewed` skill promotion checklist to `.agents/skills/skill-maintainer/SKILL.md` and a corresponding routing note in `specialist-router/SKILL.md`, so the previously orphaned `trust: reviewed` level has an end-to-end flow.
- Added an extension-point note and example profile skeleton in `.agents/agents/README.md` so users know the layer is empty by default and when to add a profile.
- Added an explicit "domain vs project split" clarification to `.agents/project/README.md` and `.agents/domain/README.md` so future readers know the durable source-of-truth fact map lives in the domain layer while project-layer rows are stop-rule pointers.
- Added a fix-loop budget section to `.agents/rules/review-gates.md` capping review→fix loops at 2 rounds before stopping for human input.
- Added an optional `current_task.review_round` counter to `.agents/rules/session-state.md` so the Fix-Loop Budget in `.agents/rules/review-gates.md` is enforceable across context compression; `.agents/skills/project-review/SKILL.md` now updates the counter and stops before a third round unless explicitly justified.
- Added a Light Resume guard to `.agents/skills/project-development/SKILL.md` and `.agents/skills/project-fix/SKILL.md` Workflow step 1: when the session entered through a Light Resume from another task class, run the Full Startup read before continuing instead of silently assuming the Mandatory Gate files are loaded.
- Surfaced the trust-config file path after `init` and `upgrade` so users can find `$AGENT_FEED_HOME/config.json` without reading docs.
- Added a friendly hint when `agent-feed check` reports a missing `.agents/rules/engineering-architecture.md`, pointing to `agent-feed upgrade`.
- Added a `test_offline_commands_do_not_open_http_connections` smoke test that disables `httpx.Client` and asserts `init`, `check`, `sync`, `status`, and `preview` complete without opening any HTTP connection, while `upgrade` still completes when its best-effort version probe fails closed.

### Changed

- **Breaking**: `agent-feed skills remove` no longer accepts a target project path. The `--path` option and the legacy positional path form are removed; the command now operates on the current working directory only and rejects any path-like argument (`./demo`, `..`, absolute paths, `~/x`, or names containing `/`). `cd` into the project before running. This closes a typo class where `agent-feed skills remove demo-a ./demo-b -y` could silently delete the wrong skill.
- Compressed `AGENTS.md` Mandatory Gates from 22 entries to 11 grouped gates that each name the owning rule/skill, and replaced the duplicated full-startup reading list with a pointer to the canonical list in `.agents/rules/context-loading.md`.
- Clarified the AGENTS.md Mandatory Gates preamble: "mandatory" means non-bypassable when an entry's trigger fires, not always-read; the canonical full-startup reading list still lives in `.agents/rules/context-loading.md`.
- Collapsed `.agents/rules/context-loading.md` triple routing (Quick Trigger Map / Task Routing list / Mixed Task Routing) into a single layered routing table that names the owner, why, and tells the reader to layer matching rows.
- Reframed `.agents/README.md` to defer rule priority and Mandatory Gates to `AGENTS.md` instead of re-listing them; this README now indexes which rule files exist and how layers reference each other.
- Trimmed `.agents/skills/project-development/SKILL.md` Required Reading from 10 files to the 5 unique to this skill; gates already mandated by `AGENTS.md` (outcome-boundary, decision-gates, context-loading, session-state, testing-gates, engineering-architecture, change-risk-gates) are no longer re-listed.
- Removed the duplicate Architecture Card from `.agents/rules/engineering-architecture.md`; the Engineering Planning Card in `.agents/skills/engineering-planning/SKILL.md` is now the single per-task working artefact, and the rule layer keeps only invariants and Review Questions.
- Tightened `.agents/skills/project-architecture/SKILL.md` Required Use to read-only orientation and pointed write/refactor work at `project-development/SKILL.md`, eliminating the routing ambiguity between the two skills.
- Trimmed `.agents/project/README.md` so the AI maintenance contract has a single owning section instead of three overlapping ones.
- Reduced the Context Capsule format in `.agents/rules/session-state.md` to a delta on top of the Task Brief — stable fields (goal, stop condition, constraints, write set) are not repeated in every handoff.
- Unified the Fix-Loop Budget counter semantics across `.agents/rules/review-gates.md`, `.agents/rules/session-state.md`, and `.agents/skills/project-review/SKILL.md`: `current_task.review_round` now records the **number of completed review rounds** (absent = 0), incremented after a round finishes (not at its start), so the `>= 2` stop condition reliably yields two completed rounds rather than one.
- Reordered `.agents/skills/project-fix/SKILL.md` Workflow so symptom intake, reproduction, and root-cause location run before `engineering-planning` is invoked, and added an explicit step 12 routing through the Final Handoff Gate in `.agents/rules/session-state.md` so fix tasks no longer skip the handoff decision. Required Reading was deduped against the AGENTS.md Mandatory Gate files (matching the project-development skill).
- Realigned the Required Reading dedupe sentence in `.agents/skills/project-development/SKILL.md` and `.agents/skills/project-fix/SKILL.md` to point at the `.agents/rules/context-loading.md` Full Startup 6-file list (outcome-boundary, decision-gates, context-loading, session-state, testing-gates, engineering-architecture). `.agents/rules/review-gates.md` and `.agents/rules/change-risk-gates.md` are explicitly marked trigger-loaded so the AI no longer assumes them already in context and silently skips them.
- Limited `.agents/skills/project-review/SKILL.md` Fix-Loop Budget Tracking to Implementation gate reviews and Fix tasks; Pure Review tasks no longer write `current_task.review_round` to session-state.
- Updated `agent-feed skills remove` partial-failure UX so successfully removed skills still appear in the action plan even when one deletion fails.
- Loosened recall-index validation in `agent_feed.checks.validate_recall_index` and the inline `.agents/scripts/check-agent-assets.sh` Python so user-authored files under `.agents/project/` and `.agents/domain/` only need to be listed in the README index. The structured-table-row and `## Owns` / `## Read When` / `## Evidence` heading requirements now apply only to the standard template-shipped files (`architecture-boundaries.md`, `milestones.md`, `project-structure.md`, `concepts.md`, `contracts.md`, `source-of-truth.md`).
- Updated `.agents/project/architecture-boundaries.md` Non-Negotiable Boundary #4 and Stop Rule #4 to allow `agent-feed upgrade` to perform a best-effort, fail-closed version probe; the offline guarantee for `init`, `check`, `sync`, `status`, and `preview` is unchanged and now pinned by a smoke test.
- Reworked the inline Python in `.agents/scripts/check-agent-assets.sh` (and its template mirror) to delegate to `agent_feed.checks.validate_references_and_indexes` when the CLI is importable, falling back to the inline implementation only when it is not. Eliminates the drift risk that previously had the recall-index rules duplicated across `agent_feed.checks` and the shell script.

### Fixed

- `agent-feed check` no longer flags a recall index entry that is referenced only as prose; entries must now be table rows or list items containing the file name in backticks. Aligned the inline check inside `.agents/scripts/check-agent-assets.sh` with the same rule so the shell-driven verification matches the canonical Python check.
- Fixed PEP8 blank-line spacing in `agent_feed.checks` (`downgrade_warnings` / `configured_clients`) and migrated `installed_agent_feed_version` lookups to the canonical `agent_feed.upgrade.installed_version` helper.
- Logged the GitHub CLI token fallback path explicitly in `_preferred_github_token` so users can tell whether `gh auth token` was used or anonymous GitHub API access took over.
- Documented the `--allow-downgrade` exit-code-3 behavior and the recall-index English-term requirement in the usage guide.
- Added a `NPM_PACKAGE` sync comment in `agent_feed.install_source` to keep the npm registry name aligned with `npm/package.json#name`.
- Clarified at the top of `.agents/project/verification-commands.sh` that the file is only read when `verification_profile = "custom"` and is harmless for `python`/`node`/`docs` profiles.

## 1.1.6 - 2026-05-08

### Added

- Added a public trust model document explaining external hash storage, skill trust levels, custom-skill boundaries, and GitHub token lookup order.
- Added automatic `gh auth token` fallback for `agent-feed skill-hub` when `GITHUB_TOKEN` and saved `settings.github_token` are not available.
- Added direct regression coverage for asset trust drift, missing GitHub CLI fallback, and upgrade idempotency.
- Added multi-skill removal for `agent-feed skills remove`, including interactive checkbox selection when no names are passed.

### Changed

- Expanded the usage guide with `env print`, `env uninstall`, and GitHub CLI token setup guidance.
- Tightened the design review gate so document reviews must check user-goal fit, result support, and result-affecting gaps instead of only polish or next-step readiness.
- Documented `agent-feed skills remove <name> [name ...] --path /path/to/project` while keeping the older final path argument form compatible.

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
