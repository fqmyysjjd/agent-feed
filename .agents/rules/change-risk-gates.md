# Change Risk Gates

Use this rule before AI-assisted development performs project-level actions that write files, change environment state, use network access, touch databases, or perform destructive/security-sensitive operations.

This rule does not replace the AI client sandbox, approval prompts, or platform permissions.

## Non-Negotiable Safety Lines

These lines apply across projects unless a higher-priority human instruction explicitly narrows and confirms the action. Project-specific rules may add stricter constraints, but they must not weaken these defaults.

1. Do not hardcode, print, commit, or move credentials, tokens, passwords, private keys, or secret-bearing config.
2. Do not bypass, remove, weaken, or mock away authentication, authorization, validation, audit, or security checks to make a task pass.
3. Do not run destructive filesystem, git, database, credential, deployment, or environment operations unless the user explicitly requested or confirmed the exact target and scope.
4. Do not add network access, dependency installation, persistence writes, telemetry, or external-service calls to a local/offline workflow unless the Task Brief and project contracts allow it.
5. Do not leak sensitive internals in user-facing errors, logs, docs, or final answers when a safer message can preserve the result.
6. Do not weaken tests, verification gates, trust checks, or review gates to make completion easier.

## Change Classes

1. `T1 local project change`: edit files, format, run tests, run lint/type checks, run project sync scripts.
2. `T2 external or environment change`: network access, dependency install or upgrade, dev servers, database migrations, external services, credentials, generated assets from remote sources.
3. `T3 destructive or security-sensitive`: deleting files, resetting git state, force push, irreversible data mutation, secret handling, production-like data access.

## Change Rules

1. Apply the non-negotiable safety lines before classifying the change.
2. Before `T1`, know the current task boundary and write set.
3. Before `T2`, state why the external/environment action is needed when it is not obvious from the user request, then follow sandbox or user approval requirements.
4. Before `T3`, require an explicit user request or confirmation with the target path, data, or command scope.
5. Never hide a failed verification command.
6. Record relevant verification commands and results in final handoff.
