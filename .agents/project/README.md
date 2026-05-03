# Project Constraints

`.agents/project/` is the user-maintained project customization layer for this repository.

Reusable rules under `.agents/rules/` may reference project constraints when they need architecture, source layout, trace, security, dependency, or delivery boundaries. This directory is where the project owner records repository-specific constraints instead of mixing them into generic rules.

Agent Feed initializes this directory so AI agents always have a stable place to find project-specific guidance. The generated files are starting points, not final truth; users should edit them to match the real project.

## Boundary

Use this directory for:

1. Current repository architecture boundaries.
2. Current repository source-tree ownership and placement rules.
3. Current repository trace, logging, audit, and secret-safety constraints.
4. Current repository milestone or delivery constraints.
5. Current repository custom verification commands.

Do not use this directory for generic AI development workflow rules, session-local conclusions, or task-specific skills.

## Maintenance Contract

1. `README.md` is the required index for every file in `.agents/project/`.
2. When a project constraint file is added, removed, renamed, or materially changed, update this README in the same task.
3. Each listed file must explain what decision boundary it owns and when an AI agent should read it.
4. Keep reusable AI workflow rules in `.agents/rules/`; keep task procedures in `.agents/skills/`.
5. If a project constraint becomes generic and reusable across projects, promote it to `.agents/rules/` through the decision gate.

## Current Project Constraints

1. `architecture-boundaries.md`: owns repository architecture boundaries and stop rules; read before module ownership, dependency, adapter, or template responsibility decisions.
2. `project-structure.md`: owns source layout and placement rules; read before adding, moving, or importing files.
3. `milestones.md`: owns implementation milestone or phase route; read before planning scope, sequencing, or release-facing work.
4. `verification-commands.sh`: owns project-specific custom code verification commands; read or edit only when `.agents/agent-feed.json` sets `verification_profile` to `custom`.
