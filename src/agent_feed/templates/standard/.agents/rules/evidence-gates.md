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

## External Skill Adoption

When adding a skill from outside this repository:

1. Preserve the current task boundary; do not turn skill import into a broad marketplace search unless the user asks.
2. Read the candidate `SKILL.md` before copying or using it.
3. Check whether an existing skill already owns the same workflow.
4. Add or keep `source` and `trust` frontmatter.
5. Use `trust: custom` unless the project has reviewed and accepted the skill as a stable local standard.
6. Remove or rewrite guidance that conflicts with `AGENTS.md`, `.agents/rules/`, `.agents/project/`, `.agents/domain/`, the current user request, or the Task Brief.
7. Inspect commands, network access, destructive operations, credential handling, persistence changes, and writes outside the Task Brief before following the skill.
8. After import or edit, sync the skill index and run the normal skill/client verification gates.
