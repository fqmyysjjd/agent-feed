---
name: design-review
description: Use when reviewing design documents, architecture plans, implementation routes, gap analyses, README, AGENTS, rules, domain docs, or skills.
---

# Design Review Skill

## Required Use

Use this skill after drafting or updating any design, protocol, planning, README, AGENTS, skill, rule, domain, or handoff-document change.

## Required Reading

1. `.agents/rules/outcome-boundary.md`
2. `.agents/domain/README.md`
3. `.agents/rules/context-loading.md`
4. `.agents/project/architecture-boundaries.md`
5. `.agents/rules/development-workflow.md`
6. `.agents/rules/review-gates.md`
7. `.agents/rules/evidence-gates.md` if external research is used.
8. The document being reviewed.

## Core Rule

Do not silently complete unresolved design gaps.

The review's highest-priority question is:

Can the next development step proceed from this design without inventing missing decisions?

If yes, state that the design is ready for the next development step and stop. If no, identify the blocking gaps and either close them in the document or ask for the required decision.

## Output

Return readiness judgment, current task boundary, findings or gaps, decision points requiring confirmation, safe next step, documents that should be updated, and whether the document can drive implementation.
