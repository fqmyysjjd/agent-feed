# Project Domain

This directory stores stable domain knowledge used by AI assistants while developing Agent Feed.

It describes the project being built, but it is still development context for AI-assisted work. It is not a user-facing product specification by itself.

**Domain vs project split.** This layer owns *stable domain knowledge* — concepts, contracts, and the durable source-of-truth fact map. The project layer (`.agents/project/`) owns *repository constraints and stop rules*. When a project-layer constraint references a durable source of truth, follow the pointer back to `source-of-truth.md` here.

## Core Concepts

| File | Owns | Read when | Evidence expectation |
| --- | --- | --- | --- |
| `concepts.md` | Project target, non-goals, and core vocabulary. | Before product positioning, README language, user-facing feature names, protocol terminology, skill naming, or docs that define what Agent Feed is or is not. | README, protocol docs, template docs, skill index, and existing user-facing terminology. |
| `contracts.md` | Public CLI command families, generated template contracts, upgrade/preview behavior, project settings ownership, and contract-change rules. | Before CLI command, generated layout, template boundary, config ownership, validation, upgrade/preview, or public command-family documentation changes. | CLI source, generated template files, checks, tests, and public template docs. |
| `source-of-truth.md` | Durable source-of-truth mapping for CLI behavior, generated templates, product positioning, local AI rules, client adapters, and recovery behavior. | Before moving canonical ownership, changing generated asset recovery, adapter generation, product/doc ownership, or durable fact placement. | CLI source, template source, README/docs, root AGENTS/.agents, and generated adapters. |

## Custom Domain Entry

Human-maintained domain rules become active through this README. AI agents must
read this README as the recall index for `.agents/domain/`, then choose the most
relevant indexed files by matching the current task against each file's
description and trigger. Do not load every domain file by default.

If a user adds or changes a domain file under `.agents/domain/`, the same change
must update the "Core Concepts" index above or another explicit index section
with the file path, owned domain boundary, read trigger, and evidence
expectation. A file under
`.agents/domain/` that is not listed here is preserved as repository content,
but it is not a reliable routing entry for future AI sessions.

## Use Cases

Read relevant domain files when:

1. Understanding project behavior.
2. Designing a new module capability.
3. Implementing cross-module behavior.
4. Reviewing architecture, code, or design documents.
5. Resolving a gap that may affect public API, persistence, audit, recovery, finalization, or source-of-truth ownership.
