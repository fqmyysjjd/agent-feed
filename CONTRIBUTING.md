# Contributing

Thank you for considering a contribution to Agent Feed.

Agent Feed is a small CLI and template project. Contributions should keep the public command surface, generated files, and AI development protocol clear and stable.

## Development Setup

```sh
uv sync --dev
uv run agent-feed --help
```

## Verification

Before opening a pull request, run:

```sh
uv run python -m pytest
uv run python -m ruff check .
uv run python -m mypy .
uv build
```

If the change affects generated AI development docs, `.agents/` templates, skills, rules, links, session-state JSON, or client adapters, also run:

```sh
sh .agents/scripts/verify-agent-dev.sh docs
```

## Contribution Guidelines

1. Keep CLI commands explicit and minimal.
2. Keep `AGENTS.md` and `.agents/` as the canonical source for generated AI development guidance.
3. Do not add project-specific rules to reusable templates unless they apply broadly.
4. Prefer small, reviewable changes with focused tests.
5. Update README or docs when a human user needs to know about a changed command, workflow, or generated file.
6. Avoid adding dependencies unless they clearly reduce complexity or improve reliability.

## Reporting Issues

Use the issue templates for bugs, feature requests, and docs/protocol feedback.
