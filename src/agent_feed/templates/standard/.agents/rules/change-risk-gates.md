# Change Risk Gates

Use this rule before AI-assisted development performs project-level actions that write files, change environment state, use network access, touch databases, or perform destructive/security-sensitive operations.

This rule does not replace the AI client sandbox, approval prompts, or platform permissions.

## Change Classes

1. `T1 local project change`: edit files, format, run tests, run lint/type checks, run project sync scripts.
2. `T2 external or environment change`: network access, dependency install or upgrade, dev servers, database migrations, external services, credentials, generated assets from remote sources.
3. `T3 destructive or security-sensitive`: deleting files, resetting git state, force push, irreversible data mutation, secret handling, production-like data access.

## Change Rules

1. Before `T1`, know the current task boundary and write set.
2. Before `T2`, state why the external/environment action is needed when it is not obvious from the user request, then follow sandbox or user approval requirements.
3. Before `T3`, require an explicit user request or confirmation with the target path, data, or command scope.
4. Never hide a failed verification command.
5. Record relevant verification commands and results in final handoff.
