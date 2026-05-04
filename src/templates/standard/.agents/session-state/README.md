# Session State

This directory stores local JSON handoff cards for long-running AI-assisted development sessions.

Session state preserves only conclusions needed to continue the current conversation after context compression. It is not a transcript, a backlog, or durable project documentation.

Every final handoff must decide whether this directory needs an update, cleanup, promotion to stable docs, or no action. Use "no action" only when the final response, changed files, or stable docs already preserve everything needed for the next turn.

`Context Capsule` is only the final-response summary. It is lower priority than session state and does not replace a JSON handoff card when losing the conclusion could affect future results.

Use one session file per active conversation:

```txt
.agents/session-state/<session_id>.json
```

Each session file contains:

1. `session`: lightweight identity fields such as id, label, optional thread id, and known titles.
2. `current_task`: the current goal, current step, stop condition, and next action.
3. `carry_forwards`: at most 7 decisions, constraints, blockers, or handoff notes that would affect the next AI action if lost.

When a carry-forward has a machine-checkable expiry, include an ISO date or timestamp in `expires_when`, for example `2026-05-10` or `2026-05-10T18:00:00+08:00`. `agent-feed check --checks session` warns when such an expiry is already past. Natural-language expiry conditions are still allowed, but the AI must check them during the final handoff gate.

`current.json` is optional. Use it only as a simple pointer when multiple active AI conversations exist in the same repository.

Session JSON files are local state and ignored by git. Promote stable cross-session conclusions into `.agents/rules/`, `.agents/project/`, `.agents/domain/`, `.agents/skills/`, README, or design documents instead of keeping them here permanently.
