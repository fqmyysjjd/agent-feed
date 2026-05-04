# Concepts

Define the stable project vocabulary for Agent Feed.

## Target

Agent Feed installs a reusable AI engineering protocol into software repositories.

It helps AI coding agents start with the right context, stop at the right boundary, preserve session conclusions, and verify work with project-local gates.

## Non-Goals

1. It is not an AI coding agent.
2. It is not a full spec-driven development framework.
3. It is not a project management tool.
4. It is not a runtime memory system.
5. It is not a replacement for Codex, Claude Code, Cursor, or Windsurf.

## Core Terms

1. `protocol asset`: a file generated into `AGENTS.md`, `.agents/`, `.codex/`, `.claude/`, or `.agents/scripts/`.
2. `standard template`: the canonical generic protocol under `src/templates/standard/`.
3. `project constraint`: repository-specific guidance under `.agents/project/`.
4. `session state`: ignored local JSON working set for active AI development conclusions.
5. `client adapter`: generated AI-client-specific files such as `CLAUDE.md`, `.claude/skills`, or `.cursor/rules/agent-feed.mdc`.
