# Session State

Session state is a compact handoff card for context compression.

It is not product memory, a transcript, a backlog, or durable documentation. Its only job is to let the next AI turn recover what matters now.

## What To Store

Use `.agents/session-state/<session_id>.json` only when context compression could dilute information that still affects the next action.

Store only:

1. `current_task`: what is being advanced, where it currently stands, when to stop, and the next action.
2. `carry_forwards`: short conclusions that must survive compression because they affect later behavior.

Do not store:

1. Detailed transcripts.
2. Facts already represented in stable docs.
3. Completed tasks that do not affect the next action.
4. Low-value notes or "might be useful later" ideas.
5. Implementation logs that can be recovered from code, tests, or git diff.

## Carry-Forward Rules

Each carry-forward must answer:

1. `content`: the conclusion, blocker, constraint, or handoff.
2. `why_keep`: why losing it would harm the next AI action.
3. `expires_when`: when it should be deleted or promoted.

Keep at most 7 carry-forwards. If more are needed, delete stale items or promote stable conclusions into `.agents/rules/`, `.agents/project/`, `.agents/domain/`, `.agents/skills/`, README, or design docs.

## Maintenance Rules

Before final handoff:

1. Update `current_task` if the task is still active.
2. Update an existing carry-forward when the same concern evolves; do not add a near-duplicate.
3. Add a carry-forward only for a new decision, constraint, blocker, or handoff that still affects the next action.
4. Delete carry-forwards whose `expires_when` condition has been met.
5. Promote durable cross-session guidance into stable docs, then delete the carry-forward.
6. If no current task or carry-forward remains, remove the session file or remove it from `.agents/session-state/current.json`.
7. Mention in the Context Capsule whether session state was updated, cleaned, promoted, or not needed, with the reason.

## Current Registry

`.agents/session-state/current.json` is optional. Use it only as a simple pointer when multiple AI conversations exist in the same repository or the AI client does not expose a stable thread id.

Keep it minimal:

1. `active_session_file`: the best match for the current conversation when known.
2. `sessions[]`: file, label, and updated_at for currently useful handoff cards.

AI clients may not expose thread id, title, rename history, or archive status to repository files. Do not pretend that metadata is known. If the environment exposes a thread id or title, store it in the session object. If not, match by `session.label`, `current_task.goal`, `carry_forwards`, and the user's latest request. If multiple sessions match, ask the user.
