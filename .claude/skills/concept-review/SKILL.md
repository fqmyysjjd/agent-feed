---
name: concept-review
description: Use when reviewing naming, vocabulary drift, invented concepts, misleading abstractions, or unclear domain language.
source: agent-feed
trust: core
---

# Concept Review Skill

Use this skill to keep AI-assisted work from introducing unnecessary concepts, misleading names, or vocabulary drift.

## Required Use

Use this skill when:

1. A review includes naming, terminology, abstraction, module boundaries, or user-facing concept changes.
2. A diff introduces new nouns, categories, layers, services, records, statuses, protocols, or workflow names.
3. The user questions whether wording, naming, or abstraction is necessary.
4. A task imports, creates, or modifies external/custom skills whose terminology could override project language.

## Required Reading

1. `.agents/rules/outcome-boundary.md`
2. `.agents/skills/README.md`
3. `.agents/project/README.md`
4. `.agents/domain/README.md`
5. The files, diff, plan, or skill being reviewed.

## Review Procedure

1. Identify the baseline vocabulary from project/domain source-of-truth files.
2. List new or changed terms in the current work.
3. For each term, check whether it maps to an existing project concept, contract, or user-visible behavior.
4. Flag invented concepts that hide a simpler action, duplicate existing language, imply unsupported behavior, or move project-specific meaning into reusable rules.
5. Prefer the plainest accurate name that a future maintainer can understand without translating it back to the implementation.

## Guardrails

1. Do not rename stable public, persistence, API, CLI, or domain contracts without applying `.agents/rules/decision-gates.md`.
2. Do not block useful domain terms just because they are new; require evidence that the term owns a durable behavior or boundary.
3. Do not treat style preference as a finding unless it creates ambiguity, drift, or maintenance cost.

## Output

Return concept findings with the affected term, why it is risky, the source-of-truth it conflicts with or lacks, and the smallest safer wording or boundary.
