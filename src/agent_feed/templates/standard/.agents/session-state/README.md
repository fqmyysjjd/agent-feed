# Session State

This directory stores local JSON handoff cards for long-running AI-assisted development sessions.

Session state preserves only conclusions needed to continue the current conversation after context compression. It is not a transcript, a backlog, or durable project documentation.

Use one session file per active conversation:

```txt
.agents/session-state/<session_id>.json
```

Each session file contains:

1. `session`: lightweight identity fields such as id, label, optional thread id, and known titles.
2. `current_task`: the current goal, current step, stop condition, and next action.
3. `carry_forwards`: at most 7 decisions, constraints, blockers, or handoff notes that would affect the next AI action if lost.

`current.json` is optional. Use it only as a simple pointer when multiple active AI conversations exist in the same repository.

Session JSON files are local state and ignored by git. Promote stable cross-session conclusions into `.agents/rules/`, `.agents/project/`, `.agents/domain/`, `.agents/skills/`, README, or design documents instead of keeping them here permanently.
