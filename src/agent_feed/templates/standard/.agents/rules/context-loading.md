# Context Loading

AI-assisted development in this repository must start by identifying the task type and loading the smallest required context.

## Startup Strategy

Use a two-level startup strategy so AI development stays reliable without loading the full rule stack on every turn.

### Full Startup

Run the full startup read when any of these are true:

1. New session.
2. Context compression occurred or is suspected.
3. The AI cannot confidently recover the current task boundary.
4. The task shifts from casual discussion into design, implementation, fix, review, or protocol work.

### Light Resume

Use a light resume when all of these are true:

1. The same session is continuing without context compression.
2. The current task boundary is still clear.
3. No new protocol/design/contract decision has appeared.

Light resume steps:

1. Re-read the **Light Resume Checklist** anchor in `.agents/rules/outcome-boundary.md` (do not re-read the entire rule).
2. Re-read only the rule, project, domain, or skill file directly needed for the next action.
3. Read additional files only if the task boundary changed, verification failed, or a new decision appeared.

If the light resume path reveals uncertainty about priority, source-of-truth, or the current stop condition, immediately fall back to the full startup read.

## Mandatory Entry

During full startup, read:

1. `.agents/rules/outcome-boundary.md`
2. `.agents/rules/decision-gates.md`
3. `.agents/rules/context-loading.md`
4. `.agents/rules/session-state.md`
5. `.agents/rules/testing-gates.md`
6. `.agents/rules/engineering-architecture.md`
7. `.agents/README.md`
8. `.agents/skills/README.md`
9. `.agents/project/README.md`
10. `.agents/domain/README.md`
11. `.agents/skills/project-architecture/SKILL.md`
12. `.agents/skills/project-development/SKILL.md`

If `AGENTS.local.md` exists, read it before project-wide rules and let it override local workflow details that do not violate project boundaries.

If `.feed-backup/` exists, inspect the newest backup's `AI_MIGRATION_GUIDE.md` and `manifest.json` before project-specific development. Treat it as preserved legacy AI-instruction evidence, not as active rules. Migrate only repository-backed facts into `.agents/project/` and `.agents/domain/`, and stop for user confirmation when a legacy rule is decisive, conflicting, redundant-but-effectful, or unsupported by current repository evidence.

Before continuing, recover the current task result boundary and Task Brief from `.agents/rules/outcome-boundary.md`.

If the conversation is long-running, has been context-compressed, or contains session-specific conclusions not yet promoted to stable docs, read `.agents/session-state/current.json` when no stable conversation id is available. Treat it as a multi-session registry, match the entry for this conversation, then read or update `.agents/session-state/<session_id>.json` according to `.agents/rules/session-state.md`.

## Task Routing

This is the single routing map. When a task matches multiple rows, apply every matching row — they layer rather than replace each other.

| Trigger | Required owner | Why |
| --- | --- | --- |
| Architecture, module, runtime, requirement, contract, or ownership decision | `.agents/skills/project-architecture/SKILL.md` | Prevents the AI from inventing project structure or future-facing decisions. |
| Implementation, refactor, test, file creation, or project-structure change | `.agents/rules/engineering-architecture.md` → `.agents/skills/engineering-planning/SKILL.md` → `.agents/skills/project-development/SKILL.md` | Forces repository-evidence ownership, reuse, placement, write set, boundaries, and verification before edits. |
| Bug, regression, failed test, or review finding fix | `.agents/rules/engineering-architecture.md` when ownership/structure is involved → `.agents/skills/engineering-planning/SKILL.md` → `.agents/skills/project-fix/SKILL.md` | Keeps fixes rooted in the failing behavior and existing owner. |
| Code, diff, commit, or merge review | `.agents/skills/project-review/SKILL.md`, `.agents/rules/git-collaboration.md` | Keeps review read-only unless the user asks for fixes. |
| README, AGENTS, rule, project/domain doc, plan, or skill review | `.agents/skills/design-review/SKILL.md`, plus `.agents/skills/concept-review/SKILL.md` when wording or concepts changed | Checks whether the next development step can proceed without invented decisions. |
| Naming, vocabulary, concept, abstraction, or public terminology drift | `.agents/skills/concept-review/SKILL.md` | Catches term drift before it propagates. |
| `.agents/skills/` itself is added, renamed, removed, or rewritten | `.agents/skills/skill-maintainer/SKILL.md` | Keeps the skill index, frontmatter, and client mirrors consistent. |
| User corrections, repeated AI failures, or stable session-state promotion | `.agents/skills/guidance-promoter/SKILL.md` | Promotes recurring lessons into the right rule/skill layer. |
| Optional, imported, custom, or specialized skill may match the task, diff, failure, or review finding | `.agents/skills/specialist-router/SKILL.md` | Routes to specialist methods without letting them override core gates. |
| Network, dependency, environment, database, destructive, credential, deployment, or security-sensitive action | `.agents/rules/change-risk-gates.md` | Applies risk classes and non-negotiable safety lines before the action. |
| External facts, current ecosystem behavior, public standards, or web-sourced recommendations | `.agents/rules/evidence-gates.md` | Separates sourced facts from project inference. |
| Any changed surface needs verification | `.agents/rules/testing-gates.md` for evidence; `.agents/rules/review-gates.md` for review routing | Keeps verification claims grounded. |
| Long-running handoff, context compression risk, or final response | `.agents/rules/session-state.md` | Preserves active conclusions without turning session state into noisy memory. |

If a task matches several rows, run the primary execution row first, then layer review/concept/risk/evidence/session rows on top. If the user asked for pure review, stay read-only unless they also asked for fixes.

## Context Budget

Prefer canonical summaries before deep files:

1. Rebuild the current task result boundary first.
2. Recover the active session handoff card if a session-state file exists.
3. Read `.agents/project/README.md`, then the specific project constraint files needed for repository-specific boundaries.
4. Read `.agents/domain/README.md`, then only the domain file needed for the current decision.
5. Read the specific rule file that owns the current gate or invariant.
6. Read `.agents/skills/README.md` before selecting optional or custom skills.
7. Read one relevant design document only when it directly informs the next action.
8. Read implementation files only after owner module, stopping point, and write set are clear.
9. For implementation, fix, or test work, read `.agents/rules/testing-gates.md` before making or reporting verification claims.
