"""Cursor adapter."""

from __future__ import annotations

from pathlib import Path

from agent_feed.models import WriteAction

MANAGED_MARKER = "<!-- agent-feed:managed adapter=cursor version=1 -->"


def cursor_rule() -> str:
    return f"""---
description: Agent Feed AI development protocol
alwaysApply: true
---
{MANAGED_MARKER}

Start with `AGENTS.md`, then follow the referenced `.agents/` rules, project
constraints, domain docs, and skills.

Treat this Cursor rule as an adapter pointer. Do not duplicate `.agents/rules/`
inside `.cursor/rules/`.
"""


def sync(
    root: Path, *, dry_run: bool, force_generated: bool
) -> tuple[list[WriteAction], list[str]]:
    target = root / ".cursor/rules/agent-feed.mdc"
    if target.parent.exists() and not target.parent.is_dir():
        return [], [".cursor/rules exists but is not a directory"]
    if target.exists() and not is_managed_cursor_rule(target):
        return [], ["Cursor rule .cursor/rules/agent-feed.mdc exists and is unmanaged"]

    action = "update" if target.exists() else "create"
    if dry_run:
        return [WriteAction(target, f"would {action}")], []

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(cursor_rule(), encoding="utf-8")
    return [WriteAction(target, action)], []


def check(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    target = root / ".cursor/rules/agent-feed.mdc"
    if not target.exists():
        errors.append("Cursor adapter missing .cursor/rules/agent-feed.mdc")
    elif not is_managed_cursor_rule(target):
        errors.append(".cursor/rules/agent-feed.mdc is not a managed Agent Feed adapter")
    else:
        text = target.read_text(encoding="utf-8")
        if "alwaysApply: true" not in text:
            errors.append("Cursor adapter must set alwaysApply: true")
        if "AGENTS.md" not in text or ".agents/" not in text:
            errors.append("Cursor adapter must point to AGENTS.md and .agents/")

    if (root / ".cursorrules").exists():
        warnings.append(".cursorrules exists; it is legacy and not managed by Agent Feed")

    return errors, warnings


def is_managed_cursor_rule(path: Path) -> bool:
    return path.is_file() and MANAGED_MARKER in path.read_text(encoding="utf-8")
