# Git Collaboration

Use this rule when AI-assisted work involves diffs, commits, branches, pull requests, merges, or review preparation.

## Diff First

Before claiming work is ready for review:

1. Run `git status --short` to understand the changed file set.
2. Review `git diff` for files changed by the current task.
3. Use staged diff commands such as `git diff --cached` only after staging succeeds.
4. Do not include unrelated user changes in summaries, commits, or cleanup.

## Commit Boundary

Commit only when the user asks for a commit or the task explicitly includes preparing one.

Before committing:

1. Verify the current task boundary is satisfied.
2. Run the verification gate selected by `.agents/rules/testing-gates.md`.
3. Ensure generated indexes, client adapters, or docs required by `.agents/rules/review-gates.md` are current.
4. Confirm the staged files match the current task and exclude unrelated work.

If `.git` writes fail, stop and report the exact command and error. Do not work around git permission failures with destructive commands.

## Commit Message Format

Use concise imperative commit messages:

```text
<type>: <summary>
```

Allowed types:

1. `feat`: user-visible feature or capability.
2. `fix`: bug fix or regression repair.
3. `docs`: documentation-only change.
4. `test`: tests or fixtures.
5. `refactor`: behavior-preserving internal change.
6. `chore`: maintenance, packaging, or repo hygiene.

Keep the summary under 72 characters when practical. Add a body only when it explains a non-obvious boundary, verification result, migration note, or follow-up.

## Merge And Review Rules

Before review or merge handoff:

1. Lead with findings if doing a review.
2. Include verification commands and results.
3. Call out unverified areas and known residual risks.
4. Do not claim a clean worktree unless `git status --short` proves it.
5. Do not rewrite, reset, or discard user changes unless the user explicitly requests that operation.
