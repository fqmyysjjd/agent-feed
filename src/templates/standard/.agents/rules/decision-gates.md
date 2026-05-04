# Decision Gates

This rule defines when an AI assistant must stop automatic work and ask for human confirmation.

It exists to prevent unconfirmed product, protocol, architecture, migration, or workflow decisions from becoming code or documentation facts.

## Core Rule

If a discovered gap, ambiguity, or improvement would affect future development results and the user has not already authorized the decision, stop before editing and ask for confirmation.

Do not treat "I found a gap" as permission to design and implement the missing policy.

When the user suggests a concrete solution, first evaluate it against the current project context and relevant code. If adopting that solution would change public behavior, persistence, environment setup, source-of-truth ownership, adapter behavior, verification, security, release scope, or AI protocol rules, present the assessment and wait for confirmation before editing unless the user has already confirmed the exact plan.

## Must Stop And Ask

Pause and ask for a decision before changing files when the choice would affect:

1. Public behavior, CLI contracts, API contracts, persistence contracts, or migration strategy.
2. AI instruction entrypoints such as `AGENTS.md`, `.agents/`, `.cursor/rules`, `.claude/`, or `.codex/`.
3. Source-of-truth boundaries between reusable rules, project constraints, domain knowledge, skills, generated mirrors, and local session state.
4. Adapter behavior for a specific AI client.
5. Verification gates, CI behavior, release packaging, or publishable package contents.
6. New dependencies, external services, permissions, network behavior, or destructive operations.
7. Product positioning or scope boundaries.

## May Continue Without Asking

Continue within the current Task Brief when the action is already implied by the confirmed task and does not change future contracts:

1. Local bug fixes inside the approved write set.
2. Formatting, lint, type, or build fixes.
3. Updating stale references caused by the current approved change.
4. Syncing generated mirrors when the source asset changed and the sync rule already requires it.
5. Adding focused tests or checks that prove the approved behavior.

## Decision Request Format

When confirmation is required, use this compact format and do not modify files until the user chooses:

```md
## Decision Required

Problem:
...

Why it affects future development:
...

Options:
1. ...
2. ...
3. ...

Recommended:
...

Default if not confirmed:
Stop. Do not modify files.
```

Options should be concrete contract choices, not vague preferences. Prefer two or three options.

## Default Behavior

If the user does not confirm a decision, stop. Do not implement the recommendation by default.

If the user asks to proceed with the recommended option, update the relevant rule, project constraint, domain document, README, or template so the decision becomes durable.
