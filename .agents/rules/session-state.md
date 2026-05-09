# Session State

Session state is a compact handoff card for context compression and final handoff.

It is not product memory, a transcript, a backlog, or durable documentation. Its only job is to let the next AI turn recover what matters now.

`Context Capsule` is lower priority than session state. The capsule is a short Markdown summary in the final response. It can report the session-state action, but it does not replace the JSON handoff card when a conclusion must survive context compression.

## What To Store

Use `.agents/session-state/<session_id>.json` whenever not recording the conclusion could make a future AI turn lose direction, repeat a resolved decision, miss a constraint, misunderstand the next action, or continue with an outdated result boundary after context compression.

This threshold is intentionally broader than only "major decisions." Record any result-affecting conclusion that is not tiny, already stable elsewhere, or trivially recoverable from code, tests, or git diff.

Store only:

1. `current_task`: what is being advanced, where it currently stands, when to stop, and the next action. May include an optional `review_round` integer counter — the **number of completed review rounds** — when an Implementation review or Fix task is running, so `.agents/rules/review-gates.md` Fix-Loop Budget is enforceable across compression. The field is absent until the first round completes (absent = 0), incremented by `.agents/skills/project-review/SKILL.md` after each completed round, and dropped when the task is closed.
2. `carry_forwards`: short conclusions that must survive compression because they affect later behavior.

Do not store:

1. Detailed transcripts.
2. Facts already represented in stable docs.
3. Completed tasks that do not affect the next action.
4. Low-value notes or "might be useful later" ideas.
5. Implementation logs that can be recovered from code, tests, or git diff.

## Final Handoff Gate

Before every final handoff for design, implementation, fix, review, protocol, document, or multi-turn work:

1. Decide whether the current result needs a session-state update, cleanup, promotion, or no action.
2. Check existing carry-forwards for expired topics whose `expires_when` condition is already met.
3. Update `current_task` when the work is still active or the next action would be unclear after compression.
4. Add or update a carry-forward when a decision, constraint, blocker, direction change, unresolved gap, or next-step dependency would affect future results if lost.
5. Clean or promote expired carry-forwards before adding new ones when possible.
6. Use `not needed` only when the final answer, changed files, or stable docs already preserve everything needed for the next turn.
7. Include a Context Capsule in the final response for code or document design tasks, and make its `Session state` row state the action and reason.

## Carry-Forward Rules

Each carry-forward must answer:

1. `content`: the conclusion, blocker, constraint, or handoff.
2. `why_keep`: why losing it would harm the next AI action.
3. `expires_when`: when it should be deleted or promoted.

Keep at most 7 carry-forwards. If more are needed, delete stale items or promote stable conclusions into `.agents/rules/`, `.agents/project/`, `.agents/domain/`, `.agents/skills/`, README, or design docs.

## Maintenance Rules

When the Final Handoff Gate decides session-state action is needed:

1. Update `current_task` if the task is still active.
2. Update an existing carry-forward when the same concern evolves; do not add a near-duplicate.
3. Add a carry-forward only for a new decision, constraint, blocker, or handoff that still affects the next action.
4. Delete carry-forwards whose `expires_when` condition has been met.
5. Promote durable cross-session guidance into stable docs, then delete the carry-forward.
6. If no current task or carry-forward remains, remove the session file or remove it from `.agents/session-state/current.json`.
7. Mention in the Context Capsule whether session state was updated, cleaned, promoted, or not needed, with the reason.

## Context Capsule

Code or document design tasks must end with a Markdown table Context Capsule. The capsule is a **delta on top of the Task Brief**, not a full restatement of it. Stable fields owned by the Task Brief (goal, stop condition, constraints, write set) are not repeated here.

```md
## Context Capsule

| Item | Content |
| --- | --- |
| Completed this turn | What changed since the last handoff |
| Changed files | Files actually written or deleted |
| Verification | Evidence run and outcome |
| Session state | updated / cleaned / promoted / not needed, with reason |
| Known gaps | New gaps that appeared this turn (omit if none) |
| Next action | One executable step |
| Next required reading | Only context the next action needs (omit if none) |
```

`Session state` must explain the action and reason, not only the status word. `Next action` must be executable. If the Task Brief boundary itself changed (rare), record that change in the carry-forwards instead of duplicating it in the capsule.

## Current Registry

`.agents/session-state/current.json` is optional. Use it only as a simple pointer when multiple AI conversations exist in the same repository or the AI client does not expose a stable thread id.

Keep it minimal:

1. `active_session_file`: the best match for the current conversation when known.
2. `sessions[]`: file, label, and updated_at for currently useful handoff cards.

AI clients may not expose thread id, title, rename history, or archive status to repository files. Do not pretend that metadata is known. If the environment exposes a thread id or title, store it in the session object. If not, match by `session.label`, `current_task.goal`, `carry_forwards`, and the user's latest request. If multiple sessions match, ask the user.
