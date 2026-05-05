# Project Domain

This directory stores stable domain knowledge used by AI assistants while developing {{PROJECT_NAME}}.

It describes the project being built, but it is still development context for AI-assisted work. It is not a user-facing product specification by itself.

## Personalization Bootstrap

If this directory still contains scaffold text when domain, contract, persistence, API, or source-of-truth work begins, infer the domain guidance from the repository's existing docs and code before continuing.

Initialization flow:

1. Read product docs, README files, source entrypoints, tests, schemas, and integration boundaries.
2. Draft concrete concepts, contracts, and source-of-truth ownership.
3. Replace scaffold-only sections with repository-backed facts whenever the evidence is clear.
4. Call out uncertain assumptions instead of presenting guesses as fact.
5. Stop for user confirmation only when the missing decision could affect future development results under `.agents/rules/decision-gates.md`.

After initialization, review the relevant domain documents whenever a feature, API, persistence model, ownership boundary, audit trail, or recovery path changes.

For template-only repositories that are not yet tied to a concrete user project, keep the generic scaffold content. As soon as the repository has enough project-specific docs or code to support evidence-based inference, replace scaffold guidance with concrete domain facts.

## AI Maintenance Loop

Before domain-affecting work:

1. Read this index, then the domain file that owns the affected concept, contract, or source-of-truth.
2. If the file is still generic, infer supported facts from README, product docs, API docs, schemas, tests, source entrypoints, and integration boundaries.
3. Record evidence paths for every durable claim.
4. Mark uncertain facts as assumptions and stop only when `.agents/rules/decision-gates.md` requires a decision.

After domain-affecting work:

1. Re-check whether concepts, contracts, or source-of-truth ownership changed.
2. Update stale domain guidance in the same task when repository evidence proves the new fact.
3. Keep domain docs compact and operational, not product-marketing prose.
4. Run `sh .agents/scripts/verify-agent-dev.sh docs` when domain guidance changes.

## Core Concepts

1. [Concepts](concepts.md): project target, non-goals, and core vocabulary.
2. [Contracts](contracts.md): public API, persistence contracts, module ports, and canonical contract docs.
3. [Source Of Truth](source-of-truth.md): durable facts and ownership rules.

## Custom Domain Entry

Human-maintained domain rules become active through this README. AI agents must
read this README as the recall index for `.agents/domain/`, then choose the most
relevant indexed files by matching the current task against each file's
description and trigger. Do not load every domain file by default.

If a user adds or changes a domain file under `.agents/domain/`, the same change
must update the "Core Concepts" index above or another explicit index section
with the file path, owned domain boundary, and read trigger. A file under
`.agents/domain/` that is not listed here is preserved as repository content,
but it is not a reliable routing entry for future AI sessions.

## Use Cases

Read relevant domain files when:

1. Understanding project behavior.
2. Designing a new module capability.
3. Implementing cross-module behavior.
4. Reviewing architecture, code, or design documents.
5. Resolving a gap that may affect public API, persistence, audit, recovery, finalization, or source-of-truth ownership.
