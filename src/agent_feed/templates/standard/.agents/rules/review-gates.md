# Review Gates

AI-assisted development in this repository uses mandatory review gates for code and design changes.

## Code Review Gate

After every coding, refactor, fix, public contract, store contract, module port, test, or project-structure change:

1. Run relevant checks.
2. Use `.agents/skills/project-review/SKILL.md`.
3. Apply `.agents/rules/testing-gates.md` when judging verification and test coverage.
4. Review milestone fit, project constraints, module ownership, public/internal boundaries, documented ownership, contract drift, tests, error handling, trace/audit anchors, and secret safety.
5. If the user asked for a pure review, do not modify files; report findings and stop unless the user asks for fixes.
6. If the current task includes implementation or fix work, route P0/P1 findings through `.agents/skills/project-fix/SKILL.md` before final handoff.
7. For implementation or fix work, fix P2 findings by default unless deferring is safer and documented.

## Review/Fix Handoff

Use this boundary when review finds issues:

1. `Pure review`: read-only. Return findings ordered by severity, residual risk, and tests not run. Do not edit.
2. `Implementation review`: the review is an internal quality gate. Fix P0/P1 and default-fix P2 within the current task boundary, then rerun relevant verification.
3. `Fix task`: use `.agents/skills/project-fix/SKILL.md`, then run `.agents/skills/project-review/SKILL.md` on the fix before final handoff.
4. If a finding requires a decision outside the current Task Brief, apply `.agents/rules/decision-gates.md` instead of silently fixing it.

## Design Review Gate

After every design document, architecture plan, module plan, implementation route, gap analysis, proposal, README, AGENTS, rule, domain, or skill update:

1. Rebuild the current task result boundary from `.agents/rules/outcome-boundary.md`.
2. Use `.agents/skills/design-review/SKILL.md`.
3. Verify the document produces a usable next action and can support the next development step without invented decisions.
4. Fix only blocking findings that can be resolved from existing source-of-truth and the current Task Brief.
5. If a blocking finding requires an unconfirmed contract, architecture, adapter, verification, source-of-truth, or product-scope choice, apply `.agents/rules/decision-gates.md` before editing.
6. If any file under `.agents/skills/` changed, run `sh .agents/scripts/sync-agent-assets.sh` before final handoff.
7. If the change affects AI engineering protocol, `.agents/`, skill names, rule names, project constraint names, document links, or session-state JSON, run `sh .agents/scripts/verify-agent-dev.sh protocol`.

## Skill Naming Gate

Every skill directory name and `name` frontmatter must:

1. Use lowercase kebab-case.
2. Use no more than three words.
3. Name the skill by the effect it provides.
4. Keep the directory name and `name` frontmatter identical.

## README Maintenance Gate

After every code, document, protocol, or structure change, check whether a human reader needs to know the changed capability, constraint, workflow, entry point, command, directory, or design location from `README.md`.

Update `README.md` in the same task when it would otherwise become stale, misleading, or incomplete.

## Project Customization Gate

`.agents/project/` is the user-maintained project customization layer. It is for repository-specific constraints, not reusable AI workflow rules.

After adding, removing, renaming, or materially changing any file under `.agents/project/`:

1. Update `.agents/project/README.md` in the same task.
2. Ensure the README explains what each project file owns and when an AI agent should read it.
3. Keep generic workflow constraints under `.agents/rules/` and task procedures under `.agents/skills/`.
4. Run `sh .agents/scripts/verify-agent-dev.sh protocol`.

## Context Capsule

Code or document design tasks must end with a Markdown table Context Capsule.

```md
## Context Capsule

| Item | Content |
| --- | --- |
| Milestone/phase | ... |
| Completed | ... |
| Changed files | ... |
| Verification | ... |
| Current task boundary | ... |
| Session state | updated / cleaned / promoted / not needed, with reason |
| Known gaps | ... |
| Next action | ... |
| Next required reading | ... |
| Constraints not to break | ... |
```

`Session state` must explain the action and reason, not only the status word. `Next action` must be executable. `Next required reading` records only the context needed before that action.
