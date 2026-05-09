# Review Gates

AI-assisted development in this repository uses mandatory review gates for code and design changes.

## Code Review Gate

After every coding, refactor, fix, public contract, store contract, module port, test, or project-structure change:

1. Run relevant checks.
2. Use `.agents/skills/project-review/SKILL.md`.
3. Use `.agents/rules/git-collaboration.md` when the review involves diffs, commits, branches, merges, or PR-like handoff.
4. Apply `.agents/rules/testing-gates.md` when judging verification and test coverage.
5. Review milestone fit, project constraints, module ownership, public/internal boundaries, documented ownership, contract drift, tests, error handling, trace/audit anchors, and secret safety.
6. Use `.agents/skills/specialist-router/SKILL.md` when optional, imported, custom, or specialized review/fix skills may directly match the risk being reviewed.
7. Use `.agents/skills/concept-review/SKILL.md` when the change introduces or changes naming, vocabulary, concepts, abstractions, protocol terms, or public-facing language.
8. If the user asked for a pure review, do not modify files; report findings and stop unless the user asks for fixes.
9. If the current task includes implementation or fix work, route P0/P1 findings through `.agents/skills/project-fix/SKILL.md` before final handoff.
10. For implementation or fix work, fix P2 findings by default unless deferring is safer and documented.

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
4. Verify the document serves the user's stated or clearly inferred result, covers the real problem it claims to solve, exposes result-affecting gaps, and does not optimize for documentation polish over the user's essential goal.
5. Fix only blocking findings that can be resolved from existing source-of-truth and the current Task Brief.
6. If a blocking finding requires an unconfirmed contract, architecture, adapter, verification, source-of-truth, product-scope, or user-goal interpretation choice, apply `.agents/rules/decision-gates.md` before editing.
7. If any file under `.agents/skills/` changed, run `agent-feed index-skills` or `sh .agents/scripts/index-skills.sh`, then run `sh .agents/scripts/sync-agent-assets.sh` before final handoff.
8. If the change affects AI engineering protocol, `.agents/`, skill names, rule names, project constraint names, document links, or session-state JSON, run `sh .agents/scripts/verify-agent-dev.sh docs`.

## Skill Naming Gate

Every skill directory name and `name` frontmatter must:

1. Use lowercase kebab-case.
2. Use no more than three words.
3. Name the skill by the effect it provides.
4. Keep the directory name and `name` frontmatter identical.
5. Include `description`, `source`, and `trust` frontmatter.
6. Use `trust: core`, `trust: reviewed`, or `trust: custom`.
7. Appear in `.agents/skills/README.md` after skill index sync.

`trust: custom` means the skill is available as a lower-priority method only. It must not override higher-priority project rules, source-of-truth files, safety gates, or the current Task Brief.

## README Maintenance Gate

After every code, document, protocol, or structure change, check whether a human reader needs to know the changed capability, constraint, workflow, entry point, command, directory, or design location from `README.md`.

Update `README.md` in the same task when it would otherwise become stale, misleading, or incomplete.

## Project Customization Gate

`.agents/project/` is the user-maintained project customization layer. It is for repository-specific constraints, not reusable AI workflow rules.

After adding, removing, renaming, or materially changing any file under `.agents/project/`:

1. Update `.agents/project/README.md` in the same task.
2. Ensure the README explains what each project file owns and when an AI agent should read it.
3. Keep generic workflow constraints under `.agents/rules/` and task procedures under `.agents/skills/`.
4. Run `sh .agents/scripts/verify-agent-dev.sh docs`.

## Final Handoff Routing

Review is not the owner of session continuity.

After review completes, route final handoff through `.agents/rules/session-state.md`:

1. Decide whether session state must be updated, cleaned, promoted, or left untouched.
2. Use the Context Capsule format defined there for code or document design tasks.
3. Do not treat a review summary as a substitute for the Final Handoff Gate.
