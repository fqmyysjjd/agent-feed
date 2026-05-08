# Project Constraints

`.agents/project/` is the user-maintained project customization layer for this repository.

Reusable rules under `.agents/rules/` may reference project constraints when they need architecture, source layout, trace, security, dependency, or delivery boundaries. This directory is where the project owner records repository-specific constraints instead of mixing them into generic rules.

Agent Feed initializes this directory so AI agents always have a stable place to find project-specific guidance. The generated files are starting points, not final truth. AI assistants should replace placeholders with repository-backed facts as soon as the project has enough docs or code to support them.

## Personalization Bootstrap

If project-specific work starts while files in `.agents/project/` or `.agents/domain/` still contain scaffold placeholders, the AI assistant must infer project constraints from the repository's existing docs and code before continuing.

Initialization flow:

1. Read current docs, source layout, build/test config, public entrypoints, and durable contract owners.
2. Draft concrete project/domain guidance in `.agents/project/` and `.agents/domain/`.
3. Replace scaffold-only sections with repository-backed facts whenever the evidence is clear.
4. Call out uncertain assumptions instead of presenting guesses as fact.
5. Stop for user confirmation only when the missing decision could affect future development results under `.agents/rules/decision-gates.md`.

After initialization, whenever a feature, architecture boundary, verification command, source layout, persistence model, security rule, or public contract changes, review the related `.agents/project/` and `.agents/domain/` files and update them when they no longer match the repository.

For template-only repositories that are not yet tied to a concrete user project, keep the generic scaffold content. As soon as the repository has enough project-specific docs or code to support evidence-based inference, replace scaffold guidance with concrete project/domain facts.

## AI Maintenance Loop

Before project-specific development:

1. Read this index, then only the project file that owns the affected boundary.
2. If the file still contains scaffold-only text, infer supported facts from README, docs, source layout, tests, package/build config, and public entrypoints.
3. Record facts with evidence paths instead of generic advice.
4. Mark uncertain items as assumptions and stop only when `.agents/rules/decision-gates.md` requires a human decision.

After project-specific development:

1. Re-check the project/domain file that owns the changed surface.
2. Update stale guidance in the same task when the diff proves the new fact.
3. Keep the file concise enough that a future AI turn can load it before coding.
4. Run `sh .agents/scripts/verify-agent-dev.sh docs` when project/domain guidance changes.

## Custom Rule Entry

Human-maintained project rules become active through this README. AI agents
must read this README as the recall index for `.agents/project/`, then choose
the most relevant indexed files by matching the current task against each
file's description and trigger. Do not load every project file by default.

If a user adds or changes a project-specific rule under `.agents/project/`, the
same change must update the "Current Project Constraints" index below with:

1. The file path.
2. The decision boundary it owns.
3. The trigger that tells an AI agent when to read it.
4. The evidence expectation that keeps the rule repository-backed.

AI agents must read this README before project-specific work and then read the
indexed file for the affected boundary. A file under `.agents/project/` that is
not listed here is preserved as repository content, but it is not a reliable
routing entry for future AI sessions.

## Boundary

Use this directory for:

1. Current repository architecture boundaries.
2. Current repository source-tree ownership and placement rules.
3. Current repository trace, logging, audit, and secret-safety constraints.
4. Current repository milestone or delivery constraints.
5. Current repository custom verification commands.
6. Evidence paths that prove the constraint.

Do not use this directory for generic AI development workflow rules, session-local conclusions, or task-specific skills.

## Maintenance Contract

1. `README.md` is the required index for every file in `.agents/project/`.
2. When a project constraint file is added, removed, renamed, or materially changed, update this README in the same task.
3. Each listed file must explain what decision boundary it owns, when an AI agent should read it, and what evidence should support changes.
4. Each direct markdown file under `.agents/project/` must include `## Owns`, `## Read When`, and `## Evidence` sections.
5. Keep reusable AI workflow rules in `.agents/rules/`; keep task procedures in `.agents/skills/`.
6. If a project constraint becomes generic and reusable across projects, promote it to `.agents/rules/` through the decision gate.

## Current Project Constraints

| File | Owns | Read when | Evidence expectation |
| --- | --- | --- | --- |
| `architecture-boundaries.md` | Repository architecture boundaries and stop rules. | Before module ownership, dependency, adapter, template responsibility, or network/offline behavior decisions. | README, package metadata, source layout, generated template paths, tests, and docs that prove the boundary. |
| `project-structure.md` | Source layout, placement rules, and generated-template ownership. | Before adding, moving, importing, generating, or deleting files. | Source tree, package config, adapters, generated assets, tests, and documented owners. |
| `milestones.md` | Implementation milestone or phase route. | Before planning scope, sequencing, or release-facing work. | Roadmap docs, release docs, tests, CLI behavior, and current implementation state. |

## Verification Hook

| File | Owns | Read when | Evidence expectation |
| --- | --- | --- | --- |
| `verification-commands.sh` | Project-specific custom code verification commands. | Read or edit only when `.agents/agent-feed.json` sets `verification_profile` to `custom`. | Project package/build/test files and commands that prove the custom verification profile. |
