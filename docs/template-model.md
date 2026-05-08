# Template Model

Date: 2026-04-30

## Canonical Source

Generated projects should treat `AGENTS.md` and `.agents/` as the canonical AI engineering source.

```text
AGENTS.md
.agents/
  README.md
  rules/
  project/
  domain/
  session-state/
  skills/
    README.md
  scripts/
  agents/
```

`AGENTS.md` is the thin entry contract. `.agents/` contains the reusable rules, project customization layer, domain knowledge, task workflows, local session-state policy, and protocol helper scripts that together form the workflow pipeline for AI-assisted development.

## Client Adapter Model

Tool-specific folders are generated adapters, not sources of truth. The product promise is one canonical workflow pipeline with thin client adapters, not duplicated rules per tool.

```text
CLAUDE.md
.claude/skills/
.cursor/rules/agent-feed.mdc
```

Codex does not require a project-local `.codex/skills` mirror by default. Codex should consume the canonical `AGENTS.md` and `.agents/skills` assets directly.

## Adapter Boundaries

### Codex

Canonical inputs:

1. `AGENTS.md`
2. `.agents/skills/`

Generated project-local adapter:

1. None by default.

Check behavior:

1. Verify `AGENTS.md` exists.
2. Verify `.agents/skills/*/SKILL.md` exists and skill names are valid.
3. Verify `.agents/skills/README.md` is current.
4. Do not require `.codex/skills`.

### Claude Code

Generated files:

1. `CLAUDE.md`
2. `.claude/skills/`

`CLAUDE.md` should be a thin adapter. Agent Feed generates this by default, but when a repository already owns `CLAUDE.md`, the file is accepted as long as it still contains the required references to `@AGENTS.md`, `.claude/skills/`, and `.agents/`.

```md
<!-- agent-feed:managed adapter=claude version=1 -->
@AGENTS.md

## Claude Code

Use `AGENTS.md` as the canonical project protocol.
Use `.claude/skills/` for Claude Code skill discovery.
Do not duplicate `.agents/rules/`; update the canonical files under `.agents/`.
```

`.claude/skills/` mirrors `.agents/skills/`.

## Skill Index And Public Skill Import

`.agents/skills/README.md` is generated from skill frontmatter and is the first stop for optional, custom, or imported skill discovery. The AI should route ambiguous, external, or specialized skill selection through `.agents/skills/specialist-router/SKILL.md` so candidate skills are selected from the index, inspected for trust/risk, and kept below the canonical protocol.

After manually adding, copying, importing, renaming, or editing a skill, run:

```sh
agent-feed index-skills
agent-feed skills list
agent-feed skills remove <name>
```

Then run client adapter sync when generated clients are configured.
If a user deletes a skill directory manually, `agent-feed index-skills` rebuilds
`.agents/skills/README.md` from the remaining `SKILL.md` files and prunes stale
trust entries.

Curated public skill import goes through:

```sh
agent-feed skill-hub
```

Imported skills stay lower-priority than the canonical protocol. When a skill is missing frontmatter, Agent Feed fills metadata from project settings; imported skills should default to `trust: custom` unless the user deliberately changes that state after review. The specialist router may use imported skills as methods, but it must return to Agent Feed's normal verification, review, and handoff gates.

Skill and managed-script sha256 values are kept in `$AGENT_FEED_HOME/config.json`, not in the project directory or user-facing skill index. By default, Agent Feed uses a user-level persistent home: `~/.agent-feed` on macOS/Linux and `%APPDATA%\agent-feed` on Windows. Use `agent-feed env setup` to create and persist that external home, `agent-feed env print` to print the shell command for manual configuration, or `agent-feed env uninstall --remove-home -y` to remove it. `status`, `preview`, and `check` read current files directly, so they can report drift without requiring a prior indexing step.

## Project Settings

`.agents/agent-feed.json` owns project-visible Agent Feed metadata and non-secret settings. Template rendering preserves existing settings during `upgrade`.

`agent-feed upgrade` compares installed project assets with the bundled
template and may also report a newer Agent Feed CLI version from the detected
installation source. The update notice is advisory and non-blocking; the command
must remain usable without network access.

Supported settings:

1. `settings.session_state.max_carry_forwards`: rendered into `.agents/session-state/schema.json` and used by session checks.
2. `settings.skills.default_import_source`: fallback `source` for skills missing that frontmatter.
3. `settings.skills.default_import_trust`: fallback `trust` for skills missing that frontmatter. Supported project-configurable values are `custom` and `reviewed`.
4. `settings.claude.required_snippets`: required references for a user-owned `CLAUDE.md`.

Change these values with `agent-feed config set KEY VALUE`; the command also regenerates affected managed assets, refreshes the skill index, updates external trust state, and runs the same health checks exposed by `agent-feed config check`. If user-level trust metadata contains project roots that no longer exist, run `agent-feed config prune` to remove those stale records without changing project files.

### Cursor

Generated file:

```text
.cursor/rules/agent-feed.mdc
```

The Cursor rule should be a thin always-on pointer:

```md
---
description: Agent Feed AI development protocol
alwaysApply: true
agentFeedManaged: true
agentFeedVersion: 1
---

@AGENTS.md

Start with `AGENTS.md`, then follow the referenced `.agents/` rules, project constraints, domain docs, and skills.
```

Do not generate `.cursorrules`; it is legacy.

## Generic Versus Project-Specific

Generic reusable protocol:

1. Outcome boundary.
2. Context loading.
3. Session-state lifecycle.
4. Development workflow.
5. Testing gates.
6. Review gates.
7. Evidence gates.
8. Change-risk gates.
9. Skill lifecycle rules.

Project customization layer:

1. Architecture boundaries.
2. Source layout.
3. Public API/contracts.
4. Persistence ownership.
5. Security and trace semantics.
6. Milestones and delivery route.
7. Custom verification commands.

`.agents/project/` is generated because it gives users a clear, editable lane for repository-specific constraints. Without this scaffold, users tend to place project-specific facts into reusable rules or leave them only in chat, which weakens cross-project reuse and context recovery.

The generated `.agents/project/README.md` is mandatory. It is the recall index
for project-specific constraints. It must explain the directory boundary, list
every project constraint file, describe the boundary each file owns, and state
when an AI agent should read it. AI agents should read the README first and then
load only the relevant indexed file instead of loading every project file by
default.

The generated `.agents/domain/README.md` follows the same model for stable
domain facts. It must index every `.agents/domain/*.md` file with enough
description and trigger detail for task-specific recall.

`sh .agents/scripts/verify-agent-dev.sh docs` checks that direct markdown files
under `.agents/project/` and `.agents/domain/` are listed in their corresponding
README indexes.

## Brownfield Migration

When `agent-feed init` finds existing AI instruction assets, it moves them into
`.feed-backup/<timestamp>/` before installing the canonical protocol. The backup
keeps the original directory structure and includes:

1. `manifest.json`: backed-up paths and migration policy.
2. `AI_MIGRATION_GUIDE.md`: instructions for AI-assisted migration.

The CLI does not try to semantically merge old instructions by itself. It only
preserves the evidence and creates a clear migration checkpoint. AI assistants
must inspect the backup before project-specific development, migrate supported
facts into `.agents/project/` or `.agents/domain/`, and stop for user
confirmation when a legacy rule is decisive, conflicting, redundant but
behavior-changing, or unsupported by repository evidence.

## Session-State Policy

Session-state is ignored by git by default. It is meant for active AI development sessions, not shared product memory.

Promote stable conclusions into rules, project constraints, domain docs, skills, design docs, or README when they become durable.

## Generated File Safety

Generated adapters should include managed markers.

Rules:

1. Managed adapter files may be updated by `agent-feed sync`.
2. Unmanaged client files must stop writes and ask for user action.
3. `--force-generated` may overwrite managed generated files only.
4. `AGENTS.md`, `.agents/rules/`, `.agents/project/`, and `.agents/domain/` are canonical and should not be auto-overwritten by sync.

The reusable rule layer also carries generic safety red lines in
`.agents/rules/change-risk-gates.md`. Project-specific safety rules may be
stricter, but they should not weaken the defaults for secrets,
auth/security checks, destructive actions, unexpected network or persistence
behavior, sensitive internal leakage, or verification integrity.

## Validation Contract

A generated project should pass:

```sh
agent-feed check . --checks all
sh .agents/scripts/verify-agent-dev.sh docs
```

before any AI protocol handoff claims success.

`init` stores `.agents/agent-feed.json` `verification_profile` and renders a stable
`.agents/scripts/verify-agent-dev.sh` entrypoint that reads that value at runtime:

1. `python`: Python projects; prefers `uv`, falls back to `python3`, then `python`.
2. `node`: Node projects; prefers `pnpm`, falls back to `npm`.
3. `custom`: uses `.agents/project/verification-commands.sh` as the user-maintained command hook and fails until `run_project_code_checks()` is configured.
4. `none`: protocol/docs verification only; code verification is intentionally unavailable.

The generated verifier `.agents/scripts/verify-agent-dev.sh` is the stable entrypoint. Project-owned commands belong in `.agents/project/verification-commands.sh` so template upgrades can refresh the verifier without overwriting local command policy.

## Context Loading Cost

The standard template uses a two-level context loading model:

1. Full startup for a new session, context compression, lost task boundary, or a shift into design/implementation/review/protocol work.
2. Light resume for same-session continuation when the task boundary is clear.

Light resume reloads `.agents/rules/outcome-boundary.md` and only the specific rule, project, domain, or skill file needed for the next action. If uncertainty appears, the AI must fall back to full startup. This keeps token cost controlled while preserving the reliability priority.

## Git Collaboration

The standard template includes `.agents/rules/git-collaboration.md` for team development:

1. Review `git status --short` and task-scoped `git diff` before handoff.
2. Stage, commit, or push only when the current user request explicitly asks for that git action.
3. Use short imperative commit messages such as `feat: add env setup flow`.
4. Stop on `.git` permission failures instead of using destructive workarounds.
