# Session State

This rule defines how AI agents preserve session-local conclusions created during multi-turn development work.

It is not a runtime feature, product memory, durable project documentation, or replacement for design documents.

## Purpose

Context compression can dilute conclusions from a long conversation. Stable project assets such as rules, domain docs, skills, and design documents are reusable, but session-specific conclusions often exist only in chat.

Use `.agents/session-state/<session_id>.json` to maintain a compact, mutable state file for the current conversation.

Use `.agents/session-state/current.json` as the optional local active-session registry when the environment does not expose a stable conversation id or when multiple AI conversations are open in the same repository.

## Mandatory Recording Triggers

Before continuing to unrelated work or final handoff, update session state or promote the conclusion to a stable asset when any of these occur:

1. The user gives a correction that changes future AI development behavior.
2. The user confirms or rejects a rule, skill name, protocol boundary, or documentation responsibility.
3. The conversation establishes a decision that will guide later development, review, or documentation work.
4. The current task has an unresolved next action, blocker, or pending validation that would be costly to reconstruct after context compression.
5. The AI notices that a prior important conclusion existed only in chat.

Do not use session state for detailed transcripts, low-value notes, or facts already fully represented in stable project docs.

## Update Rules

1. Update an existing topic when the same concern evolves, advances, narrows, or changes direction slightly.
2. Add a new topic only when the session has a genuinely different concern.
3. Remove a topic when its task is complete and no longer needed for the next action.
4. Keep each topic compact enough to be read quickly after context compression.
5. Do not preserve stale conclusions.

## Required Checkpoints

At the start of a new turn, after context compression, or before continuing a long-running task:

1. Identify the current session state file.
2. If the environment exposes a stable thread id, use the matching session file.
3. If no stable id is available, read `.agents/session-state/current.json` if it exists and find the matching `sessions[]` entry.
4. Match by `conversation_identity.external_thread_id` first when present.
5. If no thread id exists, match by `conversation_identity.resume_hint`, `current_user_goal`, active topic ids, and the user's latest request.
6. If multiple entries plausibly match, ask the user which session state to use instead of guessing.
7. Read the chosen file.
8. Reconcile it with the user's latest message and current task boundary.

Before final handoff:

1. Update session state if unresolved conclusions remain relevant.
2. Remove topics that are complete and no longer needed.
3. Update this conversation's `.agents/session-state/current.json` registry entry when needed.
4. Mention in the Context Capsule whether session state was updated, promoted, not needed, or cleaned.
