# Market Research

Date: 2026-04-30

## Research Question

Can Agent Feed become a useful standalone product, or is it only another AGENTS.md generator?

## Adjacent Products And Standards

### AGENTS.md

AGENTS.md is positioned as a simple open format for guiding coding agents. It gives repositories a predictable instruction entrypoint that is separate from README content.

Implication:

Agent Feed should build on AGENTS.md instead of replacing it. `AGENTS.md` should stay thin, while reusable gates and project-specific constraints live under `.agents/`.

Source: https://agents.md/

### OpenAI Codex

Codex uses `AGENTS.md` for repository instructions and supports skills under `.agents/skills`.

Implication:

Codex should be treated as a native consumer of the canonical Agent Feed protocol. Agent Feed should not generate `.codex/skills` by default unless Codex later standardizes a project-local `.codex` convention.

Sources:

1. https://developers.openai.com/codex/guides/agents-md
2. https://developers.openai.com/codex/skills

### Claude Code

Claude Code uses `CLAUDE.md` for persistent project instructions. Claude docs describe using `@AGENTS.md` from `CLAUDE.md` when a repository already uses AGENTS.md. Claude Code also supports skills as directories containing `SKILL.md`.

Implication:

Agent Feed should generate a thin `CLAUDE.md` adapter and mirror `.agents/skills` into `.claude/skills` when Claude is selected. Claude should not become the canonical source of truth.

Sources:

1. https://code.claude.com/docs/en/memory
2. https://code.claude.com/docs/en/skills

### Cursor Rules

Cursor project rules live in `.cursor/rules/*.mdc` and can include metadata such as `description`, `globs`, and `alwaysApply`. Cursor also supports AGENTS.md as a simpler project instruction option. `.cursorrules` is legacy.

Implication:

Agent Feed should generate a thin `.cursor/rules/agent-feed.mdc` adapter that points Cursor back to `AGENTS.md` and `.agents/`, not a duplicated copy of all rules.

Source: https://docs.cursor.com/context/rules

### GitHub Spec Kit

Spec Kit focuses on spec-driven development workflows and AI agent integrations.

Implication:

Agent Feed should not compete as a full spec-driven development framework. It should remain compatible with spec workflows by adding outcome boundaries, decision gates, session continuity, validation, and review discipline around them.

Source: https://github.com/github/spec-kit

### Agent OS

Agent OS focuses on standards management for AI-powered development: standards discovery, injection, planning, and spec shaping.

Implication:

Agent Feed should not claim ownership of all engineering standards. Its product value is the reliable AI development operating loop and client adapter hygiene.

Source: https://buildermethods.com/agent-os

## Mature CLI Design References

### Scaffolding CLIs

Products such as Vite's create CLI establish a common pattern: interactive prompts for humans, flags for deterministic setup.

Implication:

Agent Feed should support both `agent-feed init --interactive` and fully flagged commands such as `agent-feed init . --clients all -y`.

Source: https://www.npmjs.com/package/create-vite

### GitHub CLI

GitHub CLI demonstrates broad command groups, status commands, clear help, and machine-readable output where useful.

Implication:

Agent Feed needs `status`, `check --json`, and eventually broader
machine-readable output for automation. A separate `doctor` command is not
needed while diagnostics are owned by `check`/`status` and adapter repair is
owned by `sync`.

Source: https://cli.github.com/manual/

### Typer And Click

Typer and Click are mature Python CLI frameworks with command groups, options, prompts, and shell-completion support.

Implication:

Agent Feed has outgrown a single large `argparse` file. Typer is a reasonable next step because typed commands, help text, and completion are now product-level concerns.

Sources:

1. https://typer.tiangolo.com/
2. https://click.palletsprojects.com/

### InquirerPy And Rich

InquirerPy supports checkbox prompts suitable for arrow-key multi-select. Rich provides high-quality terminal panels, tables, tracebacks, and status output.

Implication:

Agent Feed should use InquirerPy for client/check selection and Rich for the human-facing CLI surface.

Sources:

1. https://inquirerpy.readthedocs.io/en/latest/pages/prompts/checkbox.html
2. https://rich.readthedocs.io/en/stable/introduction.html

## Product Gap

Existing tools generally solve one of these:

1. Where instructions live.
2. How a specific AI client scopes rules.
3. How to generate specs or plans.
4. How to inject standards into an agent.

The remaining gap:

AI coding sessions still fail because task boundaries drift, context compression loses decisions, verification evidence is vague, and project-specific constraints get mixed into generic rules.

Agent Feed should own that gap.

## Differentiation

Agent Feed should be:

1. Tool-neutral by default.
2. AGENTS.md-compatible.
3. Native to Codex's AGENTS.md and `.agents/skills` conventions.
4. Adapted to Claude through `CLAUDE.md` and `.claude/skills`.
5. Adapted to Cursor through `.cursor/rules/*.mdc`.
6. Strict about separating reusable rules from project-specific constraints.
7. Focused on reliability and handoff, not only prompt templates.
8. Lightweight enough to add to greenfield projects first, with brownfield migration later.

## Risks

1. If templates are too heavy, users will ignore them.
2. If validation is too weak, Agent Feed becomes another doc scaffold.
3. If adapters duplicate canonical rules, drift becomes unavoidable.
4. If interactivity blocks automation, the CLI will be unusable in scripts.
5. If session-state becomes a transcript, it will accumulate noise and defeat its purpose.
