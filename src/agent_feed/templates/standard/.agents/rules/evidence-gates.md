# Evidence Gates

Use this rule when AI-assisted work depends on external facts, web research, framework documentation, protocol specifications, security guidance, dependency behavior, or current ecosystem practice.

## Source Priority

Use sources in this order:

1. Current repository files and implementation state.
2. Official documentation, specifications, standards, or source repositories.
3. Primary project issue trackers, release notes, or changelogs.
4. Secondary articles only for patterns, terminology, or comparison.

Do not treat a secondary article as canonical behavior when an official source exists.

## Research Requirements

When external research affects a recommendation or document change:

1. Record the source link in the final handoff or changed document when useful.
2. Separate sourced facts from project-specific inference.
3. Prefer current official docs for tools, APIs, security, and protocol behavior.
4. Treat dates, version support, pricing, and API behavior as unstable unless verified.
5. Do not copy an external framework wholesale into this repository.

## Adoption Filter

Adopt an external practice only if it improves reliability, verification quality, context recovery, security, developer speed without weakening review gates, or reduced hallucination/concept drift.
