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

1. Re-read `.agents/rules/outcome-boundary.md`.
2. Re-read only the rule or project/domain file directly needed for the next action.
3. Read additional files only if the task boundary changed, verification failed, or a new decision appeared.

If the light resume path reveals uncertainty about priority, source-of-truth, or the current stop condition, immediately fall back to the full startup read.

## Mandatory Entry

During full startup, read:

1. `.agents/rules/outcome-boundary.md`
2. `.agents/rules/decision-gates.md`
3. `.agents/rules/context-loading.md`
4. `.agents/rules/session-state.md`
5. `.agents/rules/testing-gates.md`
6. `.agents/README.md`
7. `.agents/skills/README.md`
8. `.agents/project/README.md`
9. `.agents/domain/README.md`
10. `.agents/skills/project-architecture/SKILL.md`
11. `.agents/skills/project-development/SKILL.md`

If `AGENTS.local.md` exists, read it before project-wide rules and let it override local workflow details that do not violate project boundaries.

Before continuing, recover the current task result boundary and Task Brief from `.agents/rules/outcome-boundary.md`.

If the conversation is long-running, has been context-compressed, or contains session-specific conclusions not yet promoted to stable docs, read `.agents/session-state/current.json` when no stable conversation id is available. Treat it as a multi-session registry, match the entry for this conversation, then read or update `.agents/session-state/<session_id>.json` according to `.agents/rules/session-state.md`.

## Task Routing

Use these routes:

1. Architecture, module ownership, runtime behavior, or requirement decisions:
   - `.agents/skills/project-architecture/SKILL.md`
2. Coding, refactor, tests, or project structure changes:
   - `.agents/skills/project-development/SKILL.md`
3. Bug fixes, regressions, failed tests, or review finding fixes:
   - `.agents/skills/project-fix/SKILL.md`
4. Code review, diff review, commit review, or merge review:
   - `.agents/skills/project-review/SKILL.md`
   - `.agents/rules/git-collaboration.md`
   - Check `.agents/skills/README.md` for specialized review skills that match the concrete risk.
5. Design document, plan, protocol, README, AGENTS, rule, domain, or skill review:
   - `.agents/skills/design-review/SKILL.md`
   - Use `.agents/skills/concept-review/SKILL.md` when the work introduces or changes concepts, vocabulary, naming, abstraction, or skill terminology.
6. User corrections, repeated AI development failures, or stable session-state promotion:
   - `.agents/skills/guidance-promoter/SKILL.md`
7. Creating, updating, reviewing, renaming, deleting, or syncing skills:
   - `.agents/skills/skill-maintainer/SKILL.md`
8. External research, current ecosystem validation, protocol/API facts, or web-sourced recommendations:
   - `.agents/rules/evidence-gates.md`
9. Project-level actions that write files, change environment state, use network access, touch databases, or perform destructive operations:
   - `.agents/rules/change-risk-gates.md`
10. Naming, concept, terminology, abstraction, or vocabulary drift review:
    - `.agents/skills/concept-review/SKILL.md`

## Mixed Task Routing

When a task matches multiple routes, apply every relevant gate instead of choosing only one.

Use this order:

1. Implementation or refactor plus docs/protocol changes:
   - use `.agents/skills/project-development/SKILL.md` first.
   - use `.agents/skills/project-review/SKILL.md` after code changes.
   - use `.agents/skills/design-review/SKILL.md` after README, AGENTS, rules, domain, project, skill, or planning document changes.
   - use `.agents/skills/skill-maintainer/SKILL.md` when `.agents/skills/` changed.
   - use `.agents/skills/concept-review/SKILL.md` when the change introduces or renames concepts, skills, protocols, public terms, or abstractions.
   - run the verification scopes required by `.agents/rules/testing-gates.md` and `.agents/rules/review-gates.md`.
2. Bug, failed check, regression, or review finding plus docs/protocol changes:
   - use `.agents/skills/project-fix/SKILL.md` first.
   - use `.agents/skills/project-review/SKILL.md` after the fix.
   - use `.agents/skills/design-review/SKILL.md` for changed documents or AI protocol assets.
   - use any matching specialized review or fix skill listed in `.agents/skills/README.md` when it directly addresses the risk.
3. Pure review requested by the user:
   - use only the relevant review skill.
   - do not modify files unless the user explicitly asks for fixes.
4. Protocol-only or documentation-only work:
   - use `.agents/skills/design-review/SKILL.md`.
   - use `.agents/skills/skill-maintainer/SKILL.md` if skills changed.
   - use `.agents/skills/concept-review/SKILL.md` if naming, concepts, or skill vocabulary changed.
   - run docs verification before final handoff.

The final handoff must list every gate that applied and every gate intentionally skipped with the reason.

## Context Budget

Prefer canonical summaries before deep files:

1. Rebuild the current task result boundary first.
2. Recover the active session handoff card if a session-state file exists.
3. Read `.agents/project/README.md`, then the specific project constraint files needed for repository-specific boundaries.
4. Read domain overview.
5. Read rule files for invariant constraints.
6. Read `.agents/skills/README.md` before selecting optional or custom skills.
7. Read one relevant design document.
8. Read implementation files only after owner module, stopping point, and write set are clear.
9. For implementation, fix, or test work, read testing gates before making or reporting verification claims.
