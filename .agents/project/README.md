# Project Constraints

`.agents/project/` is the user-maintained project customization layer for this repository.

Reusable rules under `.agents/rules/` may reference project constraints when they need architecture, source layout, trace, security, dependency, or delivery boundaries. This directory is where the project owner records repository-specific constraints instead of mixing them into generic rules.

Agent Feed initializes this directory so AI agents always have a stable place to find project-specific guidance. The generated files are starting points, not final truth. AI assistants should replace placeholders with repository-backed facts as soon as the project has enough docs or code to support them.

## AI Maintenance Loop

This README is the recall index for `.agents/project/`. Read it first; load
only the indexed file that owns the affected boundary. A file that is not
listed below is preserved as repository content but is not a reliable routing
entry for future AI sessions.

Before project-specific development:

1. If a file still contains scaffold-only text, infer supported facts from
   README, docs, source layout, tests, package/build config, and public
   entrypoints. Record facts with evidence paths.
2. Mark uncertain items as assumptions and stop only when
   `.agents/rules/decision-gates.md` requires a human decision.
3. For template-only repositories with no concrete user project, keep the
   generic scaffold until evidence-based inference is possible.

After project-specific development:

1. Re-check the project/domain file that owns the changed surface and update
   stale guidance in the same task when the diff proves the new fact.
2. Keep the file concise enough that a future AI turn can load it before
   coding.
3. Run `sh .agents/scripts/verify-agent-dev.sh docs` when project/domain
   guidance changes.

## Boundary

Use this directory for:

1. Current repository architecture boundaries.
2. Current repository source-tree ownership and placement rules.
3. Current repository trace, logging, audit, and secret-safety constraints.
4. Current repository milestone or delivery constraints.
5. Current repository custom verification commands.
6. Evidence paths that prove the constraint.

Do not use this directory for generic AI development workflow rules, session-local conclusions, or task-specific skills.

**Project vs domain split.** The project layer owns repository *constraints and stop rules* (architecture, placement, security, delivery). The detailed *fact ownership map* — which file or module is canonical for each durable fact — lives in `.agents/domain/source-of-truth.md`. When a project-layer row mentions "source of truth", treat it as a pointer to the domain map, not a competing list.

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
| `release-publishing.md` | Release version and publishing automation constraints for PyPI, npm, and Homebrew. | Before release workflow, version metadata, package name, registry, trusted publisher, provenance, or tap update changes. | `.github/workflows/publish.yml`, package metadata, release scripts, README install commands, and registry constraints. |

## Verification Hook

| File | Owns | Read when | Evidence expectation |
| --- | --- | --- | --- |
| `verification-commands.sh` | Project-specific custom code verification commands. | Read or edit only when `.agents/agent-feed.json` sets `verification_profile` to `custom`. | Project package/build/test files and commands that prove the custom verification profile. |
