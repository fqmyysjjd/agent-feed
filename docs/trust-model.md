# Trust Model

Date: 2026-05-08

Agent Feed treats AI-facing skills and protocol scripts as sensitive assets.
They can influence what an AI assistant reads, trusts, edits, or runs. The trust
model makes unexpected changes visible before the assistant follows changed
guidance.

## What Is Protected

Agent Feed tracks hashes for:

1. `.agents/skills/*/SKILL.md`
2. managed protocol scripts under `.agents/scripts/`

The trust check is intentionally focused. It does not try to approve every file
in the repository. It protects the assets most likely to change AI behavior.

## Where Trust State Lives

Accepted hashes are stored outside the repository:

```text
macOS/Linux: ~/.agent-feed/config.json
Windows: %APPDATA%\agent-feed\config.json
```

The active location comes from `AGENT_FEED_HOME`. Keep it outside the project so
a repository write cannot silently approve changed AI instructions.

Use:

```sh
agent-feed env status
agent-feed env setup
agent-feed env print
agent-feed env uninstall
```

## Trust Levels

Each skill has `source` and `trust` frontmatter.

| Trust | Meaning | How to treat it |
| --- | --- | --- |
| `core` | Built into Agent Feed. | Highest confidence, still hash-checked before use. |
| `reviewed` | Reviewed by the project owner or team. | Usable after trust checks pass. |
| `custom` | Imported or local method that has not become project authority. | Advisory only; it cannot override `AGENTS.md`, `.agents/rules/`, `.agents/project/`, `.agents/domain/`, or the current task boundary. |

If a skill is missing metadata, `agent-feed index-skills` fills fallback values
from project settings. Imported skills should normally stay `trust: custom`
until a human deliberately reviews and promotes them.

## Normal Workflow

After initialization or skill changes:

```sh
agent-feed index-skills -y
agent-feed sync -a
agent-feed check -a
```

Before an AI assistant uses built-in or reviewed skills, the generated protocol
requires:

```sh
sh .agents/scripts/check-agent-trust.sh
```

If a trusted asset changed, the assistant must stop before using it. Inspect the
change:

```sh
agent-feed preview
```

If the change is intentional, accept the new hash:

```sh
agent-feed index-skills -y
```

## Custom Skills

Custom skills extend the workflow without replacing it.

They may provide task methods such as language-specific review, security
checklists, migration steps, or team conventions. They must not become a higher
priority rule source.

Before following a custom skill that suggests commands, network access,
destructive operations, credential handling, persistence changes, or writes
outside the current task, apply the change-risk gate and stop for confirmation
when required.

## GitHub Skill Hub Tokens

`agent-feed skill-hub` uses the GitHub API. Agent Feed checks tokens in this
order:

1. `GITHUB_TOKEN`
2. `settings.github_token` in the user-level Agent Feed config
3. `gh auth token` from GitHub CLI
4. anonymous GitHub API access

If anonymous access is rate limited, run:

```sh
gh auth login
```

or set a token explicitly:

```sh
export GITHUB_TOKEN="ghp_your_token_here"
```

Saved GitHub tokens belong in the user-level config, not in project files.

## What To Remember

1. Trust hashes live outside the repository by design.
2. Built-in and reviewed skills are checked before use.
3. Custom skills are methods, not authority.
4. Changed trusted assets interrupt the AI workflow until reviewed.
5. `agent-feed index-skills -y` is the explicit acceptance step for intentional
   skill or script changes.
