"""Codex adapter checks.

Codex consumes Agent Feed canonical assets directly: AGENTS.md and .agents/skills.
"""

from __future__ import annotations

from pathlib import Path

from agent_feed.models import WriteAction


def sync(root: Path, *, dry_run: bool) -> list[WriteAction]:
    detail = "Codex uses AGENTS.md and .agents/skills directly; no .codex/skills mirror is written."
    return [WriteAction(path=root, action="ok", detail=detail)]


def check(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not (root / "AGENTS.md").exists():
        errors.append("Codex adapter missing AGENTS.md")
    if not (root / ".agents/skills").exists():
        errors.append("Codex adapter missing .agents/skills")
    if (root / ".codex/skills").exists():
        warnings.append(
            ".codex/skills exists but is a legacy Agent Feed mirror; Codex uses .agents/skills"
        )
    return errors, warnings
