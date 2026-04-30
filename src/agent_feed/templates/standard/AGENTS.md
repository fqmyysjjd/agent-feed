# {{PROJECT_NAME}} AI Development Instructions

`AGENTS.md` is the repository-level entry contract for AI-assisted development.

It defines how an AI assistant should enter the project, resolve rule priority, route work to the right `.agents/` asset, and stop when the requested result is reached. It is not a product specification, user-facing behavior rule, or a place for detailed workflows.

## Mandatory Startup

At the start of a new session, after context compression, or before implementation work, read:

1. `.agents/rules/outcome-boundary.md`
2. `.agents/rules/decision-gates.md`
3. `.agents/rules/context-loading.md`
4. `.agents/rules/session-state.md`
5. `.agents/rules/testing-gates.md`
6. `.agents/README.md`
7. `.agents/project/README.md`
8. `.agents/domain/README.md`
9. `.agents/skills/project-architecture/SKILL.md`
10. `.agents/skills/project-development/SKILL.md`

Before continuing any design, implementation, review, or fix task, recover the current task result boundary and Task Brief from `.agents/rules/outcome-boundary.md`.

For long-running or multi-turn work, read or update `.agents/session-state/<session_id>.json` according to `.agents/rules/session-state.md` when active conclusions could be diluted by context compression.

## Rule Priority

Apply guidance in this order:

1. Current user request and confirmed task boundary, after reconciling them with non-negotiable project constraints.
2. `.agents/rules/outcome-boundary.md`.
3. `.agents/rules/decision-gates.md` for unconfirmed choices that affect future results.
4. `.agents/rules/context-loading.md` and `.agents/rules/session-state.md`.
5. `.agents/rules/testing-gates.md` for verification and test evidence.
6. Other stable rules under `.agents/rules/`.
7. User-maintained repository-specific constraints indexed by `.agents/project/README.md`.
8. Stable domain context under `.agents/domain/`.
9. Task workflows under `.agents/skills/`.
10. Protocol helper scripts under `.agents/scripts/`.
11. Optional specialist profiles under `.agents/agents/`.

If project docs conflict, prefer the higher-priority layer and use `.agents/skills/guidance-promoter/SKILL.md` to repair stale lower-priority guidance.

## Responsibility Boundary

Use each AI engineering layer for one purpose:

1. `AGENTS.md`: principle-level entry, priority, routing, and mandatory gates.
2. `.agents/rules/`: reusable constraints, gates, templates, and checklists.
3. `.agents/project/`: user-maintained project customization layer for current repository constraints such as architecture, source layout, trace, security, delivery, or dependency boundaries.
4. `.agents/session-state/`: local mutable JSON state for active session conclusions.
5. `.agents/domain/`: stable project domain knowledge and ownership context.
6. `.agents/skills/`: task-specific executable workflows.
7. `.agents/scripts/`: protocol helper scripts used by AI agents for sync and verification.
8. `.agents/agents/`: narrow specialist profiles for delegated checks.

Do not duplicate detailed checklists or templates in `AGENTS.md` when a rule or skill owns them.

## Mandatory Gates

These gates are always active, but their details live in the owning rule files:

1. Define the current outcome boundary and Task Brief before deep work.
2. Stop for human confirmation when `.agents/rules/decision-gates.md` requires a decision.
3. Preserve project architecture, source layout, security, trace, and contract boundaries.
4. Apply the testing gate before implementation, after failures, and before final verification claims.
5. Follow the development workflow, including comment/docstring discipline, before implementation.
6. Run the code/design review gate after code or document changes.
7. Record, clean, or promote session-state conclusions when context compression could dilute them.
8. Maintain `README.md` when a human project reader needs to know a changed capability, workflow, command, directory, entry point, or design location.
9. Read `.agents/project/README.md` before applying repository-specific constraints, and maintain it as the index for every file under `.agents/project/`.
10. Maintain related indexes and README files when changing `.agents/`, `AGENTS.md`, `.agents/scripts/`, design entrypoints, or repository structure.
11. Run `sh .agents/scripts/check-agent-assets.sh` or `sh .agents/scripts/verify-agent-dev.sh protocol` after AI protocol, `.agents/`, skill/rule/project constraint names, document links, or session-state JSON changes.
12. After any `.agents/skills/` change, run `sh .agents/scripts/sync-agent-assets.sh` and verify configured client adapters. Codex uses `.agents/skills` directly; Claude uses `.claude/skills`.
