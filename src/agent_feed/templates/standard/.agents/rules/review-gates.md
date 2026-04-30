# Review Gates

AI-assisted development in this repository uses mandatory review gates for code and design changes.

## Code Review Gate

After every coding, refactor, fix, public contract, store contract, module port, test, or project-structure change:

1. Run relevant checks.
2. Use `.agents/skills/project-review/SKILL.md`.
3. Apply `.agents/rules/testing-gates.md` when judging verification and test coverage.
4. Review milestone fit, project constraints, module ownership, public/internal boundaries, documented ownership, contract drift, tests, error handling, trace/audit anchors, and secret safety.
5. Fix P0/P1 findings before continuing.
6. Fix P2 findings by default unless deferring is safer and documented.

## Design Review Gate

After every design document, architecture plan, module plan, implementation route, gap analysis, proposal, README, AGENTS, rule, domain, or skill update:

1. Rebuild the current task result boundary from `.agents/rules/outcome-boundary.md`.
2. Use `.agents/skills/design-review/SKILL.md`.
3. Verify the document produces a usable next action and can support the next development step without invented decisions.
4. Fix blocking findings before continuing.
5. If any file under `.agents/skills/` changed, run `sh .agents/scripts/sync-agent-assets.sh` before final handoff.
6. If the change affects AI engineering protocol, `.agents/`, skill names, rule names, project constraint names, document links, or session-state JSON, run `sh .agents/scripts/verify-agent-dev.sh protocol`.

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
| Session state | updated / cleaned / not needed |
| Known gaps | ... |
| Next action | ... |
| Next required reading | ... |
| Constraints not to break | ... |
```

`Next action` must be executable. `Next required reading` records only the context needed before that action.
