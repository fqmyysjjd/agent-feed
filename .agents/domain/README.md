# Project Domain

This directory stores stable domain knowledge used by AI assistants while developing Agent Feed.

It describes the project being built, but it is still development context for AI-assisted work. It is not a user-facing product specification by itself.

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
