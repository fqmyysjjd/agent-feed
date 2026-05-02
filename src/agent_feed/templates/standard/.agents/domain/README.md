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

## Core Concepts

1. [Concepts](concepts.md): project target, non-goals, and core vocabulary.
2. [Contracts](contracts.md): public API, persistence contracts, module ports, and canonical contract docs.
3. [Source Of Truth](source-of-truth.md): durable facts and ownership rules.

## Use Cases

Read relevant domain files when:

1. Understanding project behavior.
2. Designing a new module capability.
3. Implementing cross-module behavior.
4. Reviewing architecture, code, or design documents.
5. Resolving a gap that may affect public API, persistence, audit, recovery, finalization, or source-of-truth ownership.
