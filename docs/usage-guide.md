# Agent Feed Usage Guide

Date: 2026-05-05

This guide explains how to use Agent Feed in a real repository: install it,
initialize a project, start AI-assisted development, customize project rules,
manage skills, verify the setup, and keep the workflow healthy over time.

Use this guide when you want to answer practical questions such as:

1. How do I add Agent Feed to a repository?
2. What should I run after initialization?
3. What should I tell Claude Code, Cursor, Codex, or another AI coding tool?
4. Where do my own project rules belong?
5. How do I import or remove skills?
6. How do I check, upgrade, sync, or uninstall the generated assets?

For the internal protocol model and design rationale, read
[AI Development Protocol Flow](ai-development-protocol-flow.md) and
[Template Model](template-model.md).

## Quick Path

Install Agent Feed:

```sh
brew install fqmyysjjd/tap/agent-feed
# or
uv tool install agent-feed
# or
pipx install agent-feed
# or
npm install -g @yysjjd/agent-feed
```

Initialize a repository:

```sh
cd /path/to/your/project
agent-feed init
agent-feed check -a
agent-feed status
```

Start your AI coding assistant in the repository and use a concrete task
prompt:

```text
First, review the development guidelines for the project, and then, start to carry out our tasks:

1. [Describe the concrete result you want]
```

That is the normal loop. Agent Feed installs the workflow, your AI assistant
reads the repository-owned rules, and verification commands give you evidence
before the assistant claims the work is done.

## What Agent Feed Adds

After `agent-feed init`, your repository gets a canonical AI development
surface:

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
CLAUDE.md
.claude/skills/
.cursor/rules/agent-feed.mdc
```

The important rule is simple: `AGENTS.md` and `.agents/` are the source of
truth. Tool-specific files such as `CLAUDE.md` and Cursor rules are thin
adapters that point back to that source.

If your repository already has AI instructions, `agent-feed init` backs them up
into `.feed-backup/<timestamp>/` before installing the new protocol. The backup
includes a migration guide so your AI assistant can preserve decisive legacy
rules into `.agents/project/` or `.agents/domain/` instead of losing them.

## Choose A Verification Profile

Agent Feed asks for a verification profile during initialization. The profile
controls what the AI should run before it claims code work is verified.

| Profile | Use when |
| --- | --- |
| `python` | The repository is primarily a Python project. |
| `node` | The repository is primarily a Node.js project. |
| `custom` | You want to define your own commands. |
| `none` | The repository has no code verification path yet. |

For non-interactive initialization, pass the profile explicitly:

```sh
agent-feed init --profile python -y
```

Later, change the profile with:

```sh
agent-feed config set verification_profile custom
```

If you use `custom`, fill in:

```text
.agents/project/verification-commands.sh
```

Agent Feed intentionally fails the code verification gate when custom commands
are missing. This prevents the AI from saying code verification passed when the
repository has no real test, lint, or build command configured.

## Daily Workflow

Use this cycle for normal AI-assisted development:

1. Start from a concrete task, not a broad instruction.
2. Let the AI read `AGENTS.md` and the relevant `.agents/` files.
3. Ask the AI to stop and confirm when it hits architecture, contract,
   verification, security, source-of-truth, or scope decisions.
4. Let the AI implement or review within the declared task boundary.
5. Run verification before accepting "done".
6. Use `agent-feed status` or `agent-feed check -a` when you suspect drift.

A useful prompt shape:

```text
First, review the development guidelines for the project.

Task:
[One concrete result]

Constraints:
[Important scope, files, behavior, or verification expectations]
```

Avoid pasting all rules into chat. The point of Agent Feed is that the
repository owns the workflow, and the AI loads the relevant files from the
repository.

## Make AI Efficient With Project And Domain Rules

Agent Feed becomes more useful when `.agents/project/` and `.agents/domain/`
describe your real repository instead of staying as generic templates.

Think of the two directories this way:

| Directory | What it should contain | Typical examples |
| --- | --- | --- |
| `.agents/project/` | How this repository is engineered. | Architecture boundaries, source layout, verification commands, release rules, dependency limits, security rules. |
| `.agents/domain/` | What this repository means. | Product concepts, public contracts, business rules, data ownership, source-of-truth documents. |

The goal is not to make the AI read everything. The goal is to keep a clear
index so the AI can read the right project or domain rule at the right time.

### Start A New AI Session

Use this prompt when opening a new session in a repository that already has
Agent Feed installed:

```text
First, follow `AGENTS.md`.

Recover the current task boundary, read `.agents/project/README.md` and
`.agents/domain/README.md` as indexes, then load only the project/domain files
that match this task.

Task:
[Describe the concrete result I want]

Before editing, tell me the task boundary, the files you need to read, and the
verification you expect to run.
```

This helps the AI avoid two bad extremes: reading the whole repository before a
small task, or skipping project-specific rules that matter.

### Bootstrap Project And Domain From Templates

Right after `agent-feed init`, the generated project/domain files may still be
template-like. Ask the AI to replace placeholders with repository-backed facts:

```text
The `.agents/project/` and `.agents/domain/` files may still be generic
templates.

Inspect the README, docs, source layout, package/build files, tests, public
entrypoints, and any existing architecture or product docs. Then update
`.agents/project/` with repository-specific engineering rules and
`.agents/domain/` with stable domain concepts, contracts, and source-of-truth
facts.

Only write facts supported by repository evidence. Mark uncertain assumptions
instead of guessing. Update `.agents/project/README.md` and
`.agents/domain/README.md` so every custom file has `Owns`, `Read when`, and
`Evidence expectation` index fields. Run the docs verification gate afterward.
```

Good output from the AI should include:

1. Concrete project rules, not generic advice.
2. Evidence paths such as README sections, package files, source files, tests,
   or docs.
3. Clear uncertainty notes when a decision is not proven.
4. Updated README indexes for project and domain files, including `Owns`, `Read
   when`, and `Evidence expectation`.
5. Verification evidence.

### Migrate Old AI Instructions From `.feed-backup/`

If your project had previous AI instructions, `agent-feed init` moves them into
`.feed-backup/<timestamp>/`.

Use this prompt to migrate only the useful parts:

```text
Inspect the newest `.feed-backup/` directory, especially `AI_MIGRATION_GUIDE.md`
and `manifest.json`.

Compare the old AI instructions with the current repository docs and code.
Migrate every decisive project-specific rule into `.agents/project/` and every
stable domain or contract rule into `.agents/domain/`.

Do not blindly copy generic prompts, stale rules, duplicated Agent Feed
workflow, or rules that conflict with the new protocol. If an old rule is
decisive but conflicts with Agent Feed, overlaps in a way that could change the
AI development loop, or lacks enough repository evidence, stop and ask me.

After migration, update the project/domain README indexes with `Owns`, `Read
when`, and `Evidence expectation` fields, then run docs verification.
```

This keeps old useful knowledge while preventing a new repository protocol from
being polluted by stale prompts.

### Add A Custom Project Rule

Use this prompt when you want the AI to add or update a repository-specific
engineering rule:

```text
This change affects a project-specific engineering rule.

Create or update the right file under `.agents/project/`. Keep it focused on
repository-specific facts, include evidence paths, and define when an AI should
read it.

Then update `.agents/project/README.md` with:
1. the file path,
2. the decision boundary it owns,
3. the trigger that tells future AI sessions when to read it,
4. the evidence expectation that keeps the rule repository-backed.

Run `sh .agents/scripts/verify-agent-dev.sh docs`.
```

Good trigger wording is specific:

```md
Read before changing release workflows, version metadata, package names,
registries, trusted publishers, or Homebrew tap updates.
```

Weak trigger wording is too vague:

```md
Read when working on the project.
```

### Add A Custom Domain Rule

Use this prompt when a change affects product concepts, contracts, business
rules, or durable source-of-truth ownership:

```text
This change affects stable domain knowledge.

Check `.agents/domain/README.md`, then create or update the relevant domain
file. Keep temporary notes out of domain docs. Only record stable concepts,
contracts, business rules, ownership, or source-of-truth facts supported by the
repository.

Update `.agents/domain/README.md` with the file path, owned domain boundary,
read trigger, and evidence expectation. Run docs verification afterward.
```

Example index entry:

```md
| File | Owns | Read when | Evidence expectation |
| --- | --- | --- | --- |
| `billing-contracts.md` | Billing contracts, payment state transitions, and invoice ownership. | Before billing behavior or public billing field changes. | Billing API docs, schema/migration files, tests, and source modules. |
```

### Ask The AI To Keep Indexes Current

When you manually add or edit a project/domain file, ask the AI to verify the
index:

```text
I changed files under `.agents/project/` or `.agents/domain/`.

Check whether each direct markdown file is listed in the corresponding README.
For every listed file, make sure the index explains the owned boundary, read
trigger, and evidence expectation clearly enough for a future AI session to
choose it without loading every file.

If an index entry is missing or vague, update it. Then run
`sh .agents/scripts/verify-agent-dev.sh docs`.
```

### Keep Rules Short And Useful

Project and domain files should be concise enough for the AI to load during a
real coding task.

Prefer this structure:

```md
# [Rule Name]

## Owns

This file owns [specific boundary].

## Read When

Read this before [specific trigger].

## Rules

1. [Repository-backed rule.]
2. [Repository-backed rule.]

## Evidence

1. `[path]`: [what it proves].

## Stop And Ask

Stop before [decision that should not be invented].
```

Avoid:

1. Generic AI advice that belongs in `.agents/rules/`.
2. Temporary task notes.
3. Long transcripts.
4. Rules without evidence.
5. Index entries that say only "read when relevant".
6. Project/domain markdown files without `## Owns`, `## Read When`, and
   `## Evidence`.

## Common Commands

| Goal | Command |
| --- | --- |
| Initialize the current project | `agent-feed init` |
| Preview writes before initialization or upgrade | `agent-feed preview` |
| Check structure, config, skills, references, session state, scripts, and adapters | `agent-feed check -a` |
| See current drift and next recommended action | `agent-feed status` |
| Sync client adapters after protocol or skill changes | `agent-feed sync -a` |
| Regenerate the skill index | `agent-feed index-skills` |
| Browse and import public skills | `agent-feed skill-hub` |
| List installed skills | `agent-feed skills list` |
| Remove an installed skill | `agent-feed skills remove <name>` |
| Validate user-level config and project config | `agent-feed config check` |
| Remove stale user-level project records | `agent-feed config prune` |
| Upgrade Agent Feed-managed assets | `agent-feed upgrade` |
| Remove Agent Feed-managed assets | `agent-feed uninstall` |

Run `agent-feed --help` or `agent-feed <command> --help` for the full command
reference.

## Configure Agent Feed Home

Agent Feed stores trusted AI asset hashes outside the project so a repository
write cannot silently approve changed managed skills or scripts.

The default location is:

```text
macOS/Linux: ~/.agent-feed
Windows: %APPDATA%\agent-feed
```

Check the environment:

```sh
agent-feed env status
```

Create and persist it:

```sh
agent-feed env setup
```

If initialization detects that `AGENT_FEED_HOME` is missing, it can set it up
for you. If setup fails, run `agent-feed env setup` manually and then retry the
original command.

## Use Skills

Skills are task-specific methods. They are useful for review workflows, fix
workflows, language-specific methods, design critique, or team-specific
procedures.

Browse curated public skills:

```sh
agent-feed skill-hub
```

If GitHub rate limits anonymous requests, use a token:

```sh
export GITHUB_TOKEN="ghp_your_token_here"
agent-feed skill-hub
```

You can also save the token in the user-level Agent Feed config under
`settings.github_token`.

After adding, editing, importing, or deleting skills, run:

```sh
agent-feed index-skills
agent-feed sync -a
agent-feed check -a
```

List and remove installed skills:

```sh
agent-feed skills list
agent-feed skills remove <name>
```

Custom or imported skills are lower priority than the current user request,
`AGENTS.md`, `.agents/rules/`, `.agents/project/`, and `.agents/domain/`. They
can guide a task, but they cannot override the repository's source of truth.

When a task may benefit from a specialized or imported skill, the AI should use
`.agents/skills/specialist-router/SKILL.md`. That router reads the skill index,
chooses only the skills that match the current task, checks `source` and
`trust`, applies risk gates for commands or risky actions, and then returns to
the normal Agent Feed verification and review loop.

Use this prompt when you want the AI to consider imported skills without giving
them control of the whole task:

```text
Check `.agents/skills/README.md` and use `specialist-router` to see whether any
custom or imported skill directly helps this task.

Only use skills that fit the current Task Brief. Treat custom skills as advisory
methods, apply change-risk gates before commands or risky actions, and keep
`AGENTS.md`, `.agents/rules/`, `.agents/project/`, and `.agents/domain/` higher
priority.
```

## Upgrade, Sync, And Uninstall

Use `upgrade` when Agent Feed itself has new managed assets:

```sh
agent-feed upgrade
```

`upgrade` also checks the detected install source for a newer Agent Feed CLI
version when network access is available. If you installed with npm, it checks
npm and recommends `npm install -g @yysjjd/agent-feed@latest`. If you installed
with uv, pipx, or Homebrew, it recommends the matching update command for that
source. This update notice is non-blocking; project asset upgrades still work
offline.

Agent Feed does not overwrite user-maintained `.agents/project/` or
`.agents/domain/` content just because the template changed. Those files are
your repository-specific layer.

Use `sync` when canonical assets changed and generated client adapters need to
be refreshed:

```sh
agent-feed sync -a
```

Use `uninstall` when you want to remove Agent Feed-managed assets from a
repository:

```sh
agent-feed uninstall
```

Uninstall removes managed assets without deleting unmanaged user files.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `AGENT_FEED_HOME` is missing | Run `agent-feed env setup`, then retry the original command. |
| `check` reports stale project records | Run `agent-feed config prune`, then `agent-feed config check`. |
| Custom verification is not configured | Edit `.agents/project/verification-commands.sh`, then run `sh .agents/scripts/verify-agent-dev.sh code`. |
| A skill or script trust check fails | Inspect the changed files. If the change is intentional, run `agent-feed index-skills -y`. |
| Claude or Cursor files look stale | Run `agent-feed sync -a`. |
| A manually added project/domain rule is not being used | Add the file to `.agents/project/README.md` or `.agents/domain/README.md` with a clear read trigger. |
| `skill-hub` is rate limited | Set `GITHUB_TOKEN` or save `settings.github_token` in the user-level config. |
| You want to see what would change before writing | Run `agent-feed preview` or use `--dry-run` on supported commands. |

## What To Remember

1. `AGENTS.md` and `.agents/` are the canonical AI development source.
2. `CLAUDE.md`, `.claude/skills/`, and Cursor rules are generated adapters.
3. Put repository-specific engineering rules in `.agents/project/`.
4. Put stable domain facts and contracts in `.agents/domain/`.
5. Put task methods and imported workflows in `.agents/skills/`.
6. Keep project/domain README indexes current so future AI sessions can recall
   the right custom rule without reading every file.
7. Run `agent-feed check -a` after meaningful protocol, rule, skill, or adapter
   changes.
