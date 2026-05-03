# Contracts

Contracts are the strongest anti-hallucination boundary in AI-assisted development.

## Public CLI Contract

The current public commands are:

1. `agent-feed init [path] [--project-name NAME] [--clients CLIENTS] [--profile PROFILE] [--env-home PATH] [--force-generated] [--dry-run]`
2. `agent-feed check [path] [--checks CHECKS] [--clients CLIENTS] [--json]`
3. `agent-feed sync [path] [--clients CLIENTS] [--force-generated] [--dry-run]`
4. `agent-feed upgrade [path] [--project-name NAME] [--clients CLIENTS] [--dry-run]`
5. `agent-feed status [path]`
6. `agent-feed preview [path] [--project-name NAME] [--clients CLIENTS] [--profile PROFILE]`
7. `agent-feed uninstall [path] [--dry-run] [-y]`
8. `agent-feed index-skills [path] [--dry-run] [-y]`
9. `agent-feed config get [KEY] [--path PATH] [--json]`
10. `agent-feed config check [--path PATH] [--json]`
11. `agent-feed config set KEY VALUE [--path PATH] [--dry-run]`
12. `agent-feed skill-hub [path] [--keyword KEYWORD] [--dry-run]`
13. `agent-feed env status [path]`
14. `agent-feed env setup [path] [--home PATH] [--shell SHELL] [--force] [--dry-run]`
15. `agent-feed env print [--home PATH] [--shell SHELL]`
16. `agent-feed env uninstall [--home PATH] [--shell SHELL] [--remove-home] [--dry-run] [-y]`
17. `agent-feed --version`

`agent-feed version` may exist only as a hidden compatibility alias and should not be documented as the public command.

`agent-feed doctor` and short aliases may exist as hidden helper commands but should not be documented as the primary public command set.

## Template Contract

The standard template must generate:

1. `AGENTS.md`
2. `.agents/rules/`
3. `.agents/agent-feed.json`
4. `.agents/project/`
5. `.agents/domain/`
6. `.agents/session-state/`
7. `.agents/skills/`
8. `.agents/skills/README.md` as the generated skill index
9. `.agents/agents/`
10. `CLAUDE.md` when Claude is selected
11. `.claude/skills` when Claude is selected
12. `.cursor/rules/agent-feed.mdc` when Cursor is selected
13. `.agents/scripts/check-agent-assets.sh`
14. `.agents/scripts/index-skills.sh`
15. `.agents/scripts/check-agent-trust.sh`
16. `.agents/scripts/sync-agent-assets.sh`
17. `.agents/scripts/verify-agent-dev.sh`
18. `.agents/project/README.md` as the required project customization index
19. Existing `.agents` collision protection during `init`

## Upgrade Contract

`agent-feed upgrade` and `agent-feed preview` must compare an installed project with the current bundled standard template.

1. `preview` shows upgrade diffs when the target already has Agent Feed installed.
2. `upgrade` writes changed managed protocol files and missing template files.
3. `upgrade` does not delete local files.
4. `upgrade` does not overwrite existing files under `.agents/project/` or `.agents/domain/`; those are user-maintained.
5. Claude skill adapter updates are non-destructive during `upgrade`; stale generated files are not pruned. Use `sync --force-generated` when exact adapter pruning is required.

## Project Settings Contract

`.agents/agent-feed.json` owns project-visible Agent Feed metadata and non-secret settings. `$AGENT_FEED_HOME/config.json` owns user-level secrets and accepted AI asset hashes.

`agent-feed config check` must validate the project-visible config shape, the user-level config shape, and stale user-level project roots without modifying files.

`agent-feed config set` must preserve that boundary while updating one project-visible config value, reapplying the affected settings-driven output such as session-state schema limits, skill metadata defaults, skill index content, verification profile behavior, and configured client adapter checks, then running the same config health check.

## Contract Change Rule

If a task changes CLI commands, generated file layout, template responsibility boundaries, or validation behavior, update `README.md`, the relevant public docs under `docs/` (usually `docs/template-model.md` and `docs/ai-development-protocol-flow.md`), and tests in the same task.
