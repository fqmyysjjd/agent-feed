# AI Protocol Usage Guide

Date: 2026-05-05

This guide explains how to use and maintain the AI development protocol that
Agent Feed installs into a repository.

It is written for repository owners and team members who want the AI assistant
to follow stable project rules without turning every session into a large prompt
dump.

## What Agent Feed Installs

After `agent-feed init`, the repository gets a canonical AI protocol surface:

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
truth. Tool-specific files such as `CLAUDE.md` and Cursor rules are adapters
that point back to that source.

## The Normal Usage Loop

1. Install the protocol:

   ```sh
   agent-feed init
   ```

2. Verify the repository:

   ```sh
   agent-feed check -a
   agent-feed status
   ```

3. Open your AI coding assistant in the repository.

4. Start with a concrete task prompt:

   ```text
   First, review the development guidelines for the project, and then, start to carry out our tasks:

   1. [Describe the concrete result you want]
   ```

5. Let the AI follow the protocol:

   ```text
   AGENTS.md
     -> outcome boundary
     -> context loading
     -> project/domain index lookup
     -> skill routing
     -> decision gates
     -> implementation or review
     -> verification
     -> final handoff
   ```

6. Re-run verification after protocol or custom-rule changes:

   ```sh
   agent-feed check -a
   sh .agents/scripts/verify-agent-dev.sh docs
   ```

## What Each Layer Owns

| Layer | Owner | Purpose |
| --- | --- | --- |
| `AGENTS.md` | Agent Feed | Entry contract, priority order, mandatory gates, and routing. |
| `.agents/rules/` | Agent Feed | Reusable workflow rules such as task boundaries, decision gates, testing, review, git behavior, and handoff. |
| `.agents/project/` | You | Repository-specific engineering constraints such as architecture, source layout, verification commands, release process, dependency limits, and security rules. |
| `.agents/domain/` | You | Stable domain knowledge such as concepts, public contracts, business rules, durable facts, and source-of-truth ownership. |
| `.agents/skills/` | Agent Feed / You | Task-specific methods for architecture, implementation, fixes, reviews, imported skills, or team-specific workflows. |
| `.agents/session-state/` | Local AI session | Short-lived handoff state for active conclusions after long sessions or context compression. |
| `.agents/scripts/` | Agent Feed | Verification, trust checks, skill indexing, and adapter sync. |
| `CLAUDE.md`, `.cursor/rules/` | Generated adapters | Thin pointers that route tools back to `AGENTS.md` and `.agents/`. |

## How AI Reads Custom Project And Domain Rules

Agent Feed does not make the AI read every project or domain file on every
task. That would be expensive and would make small tasks noisy.

Instead, Agent Feed uses index recall:

```text
Task starts
  -> read .agents/project/README.md when project constraints may matter
  -> read .agents/domain/README.md when domain facts or contracts may matter
  -> choose the most relevant indexed file by description and trigger
  -> read only that file
```

This makes custom rules discoverable without forcing full-context loading.

## Maintaining `.agents/project/`

Use `.agents/project/` for rules about how this repository is engineered.

Good examples:

1. Architecture boundaries.
2. Source tree ownership.
3. Verification commands.
4. Release process.
5. Security or secret-handling rules.
6. Dependency rules.
7. Generated file ownership.

Do not use `.agents/project/` for reusable AI behavior that should apply across
all repositories. Put reusable behavior in `.agents/rules/` only after a
deliberate protocol change.

### Add A Project Rule

1. Create a focused file:

   ```text
   .agents/project/release-publishing.md
   ```

2. Give it a clear structure:

   ```md
   # Release Publishing

   This file defines repository-specific release and package publishing constraints.

   ## Read When

   Read this file before release workflow, version metadata, package name,
   registry, provenance, trusted publisher, or Homebrew tap changes.

   ## Rules

   1. GitHub Release tags are the release version source of truth.
   2. PyPI package name remains `agent-feed`.
   3. npm package name remains `@yysjjd/agent-feed`.

   ## Stop Rules

   Stop and ask before changing package names or publishing order.
   ```

3. Register it in `.agents/project/README.md`:

   ```md
   4. `release-publishing.md`: owns release version and publishing automation
      constraints for PyPI, npm, and Homebrew; read before release workflow,
      version metadata, package name, registry, or tap update changes.
   ```

4. Verify the index:

   ```sh
   sh .agents/scripts/verify-agent-dev.sh docs
   ```

If a `.agents/project/*.md` file is not listed in `.agents/project/README.md`,
it is not a reliable AI recall entry. The docs verification gate catches this.

## Maintaining `.agents/domain/`

Use `.agents/domain/` for stable project knowledge and durable facts.

Good examples:

1. Core concepts and vocabulary.
2. Public API and contract ownership.
3. Persistence ownership.
4. Business rules.
5. Source-of-truth documents.
6. Recovery, audit, or finalization semantics.

Do not put temporary decisions, task notes, or speculative ideas in
`.agents/domain/`. Use session-state or a design document until the fact becomes
stable.

### Add A Domain Rule

1. Create a focused file:

   ```text
   .agents/domain/<your-domain-contracts>.md
   ```

2. Explain when the AI should read it:

   ```md
   # Billing Contracts

   This file owns billing domain contracts and source-of-truth boundaries.

   ## Read When

   Read this file before changing billing plans, invoice generation, payment
   state transitions, refund handling, or externally visible billing fields.
   ```

3. Register it in `.agents/domain/README.md`:

   ```md
   4. [Billing Contracts](billing-contracts.md): billing contracts, payment
      state transitions, and invoice ownership; read before billing behavior or
      public billing field changes.
   ```

4. Verify:

   ```sh
   sh .agents/scripts/verify-agent-dev.sh docs
   ```

If a `.agents/domain/*.md` file is not listed in `.agents/domain/README.md`, it
is not a reliable AI recall entry. The docs verification gate catches this.

## Maintaining Skills

Use `.agents/skills/` for task methods, not authoritative project rules.

Skills are useful for:

1. A review method.
2. A fix workflow.
3. A design critique method.
4. A language-specific workflow.
5. A public skill imported from `skill-hub`.

After adding, editing, renaming, importing, or deleting a skill, run:

```sh
agent-feed index-skills
agent-feed sync -a
sh .agents/scripts/verify-agent-dev.sh docs
```

Custom or imported skills are lower priority than:

1. The current user request.
2. `AGENTS.md`.
3. `.agents/rules/`.
4. `.agents/project/`.
5. `.agents/domain/`.

If a custom skill suggests risky commands, network access, credential handling,
destructive operations, or writes outside the current task boundary, the AI must
inspect the action and apply the change-risk gate before proceeding.

## Maintaining Verification

Agent Feed creates a stable verifier:

```sh
sh .agents/scripts/verify-agent-dev.sh docs
sh .agents/scripts/verify-agent-dev.sh code
sh .agents/scripts/verify-agent-dev.sh full
```

The active verification profile is stored in `.agents/agent-feed.json`.

If the profile is `custom`, project-owned commands belong in:

```text
.agents/project/verification-commands.sh
```

When custom verification is not configured, the code gate fails and tells the
user to fill in the real commands. This prevents the AI from claiming code
verification passed when the repository has no configured test path.

## Updating The Protocol Safely

When you change AI protocol files, use this checklist:

1. Identify the owner layer before editing.
2. Update README indexes when adding, renaming, or removing files.
3. Keep project-specific facts out of `.agents/rules/`.
4. Keep temporary conclusions out of `.agents/domain/`.
5. Run:

   ```sh
   sh .agents/scripts/verify-agent-dev.sh docs
   agent-feed check -a
   ```

6. If trusted built-in skills or scripts changed intentionally, accept the new
   hash:

   ```sh
   agent-feed index-skills -y
   ```

Trusted hashes are stored outside the project in `$AGENT_FEED_HOME/config.json`.
Do not copy that trust state into the repository.

## When To Ask The AI To Maintain The Protocol

Use direct prompts when a change should update project guidance:

```text
This change affects our release process. After implementation, update the
related `.agents/project/` rule and keep the README index current.
```

```text
This changes a domain contract. Check `.agents/domain/README.md`, read the
relevant contract file, and update stale domain guidance if the code proves a
new fact.
```

```text
I added a custom rule under `.agents/project/`. Check whether the README index
has enough description and trigger detail for future AI recall.
```

## Common Mistakes

| Mistake | Result | Fix |
| --- | --- | --- |
| Adding a new `.agents/project/<name>.md` file without indexing it | Future AI sessions may not read it. | Add it to `.agents/project/README.md` with description and trigger. |
| Putting project facts into `.agents/rules/` | Reusable protocol becomes polluted with one-project constraints. | Move facts into `.agents/project/`. |
| Putting temporary task notes into `.agents/domain/` | Domain docs become noisy and misleading. | Use session-state or a design doc until stable. |
| Editing skills without indexing | Skill discovery and trust metadata drift. | Run `agent-feed index-skills`. |
| Claiming verification without configured tests | AI can report false completion. | Configure `.agents/project/verification-commands.sh` or use the right profile. |
| Changing managed scripts without accepting trust state | Trust gate blocks use. | Inspect, then run `agent-feed index-skills -y` if intentional. |

## Minimal Maintenance Checklist

For every AI-protocol or custom-rule change:

1. Did the file go into the right layer?
2. Is the file indexed by the correct README?
3. Does the index describe when to read the file?
4. Did you avoid full-context loading as the default?
5. Did you run docs verification?
6. Did you update user-facing docs if the workflow changed?
