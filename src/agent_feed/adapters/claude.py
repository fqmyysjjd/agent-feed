"""Claude Code adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from agent_feed.fs import same_tree
from agent_feed.models import WriteAction

MANAGED_MARKER = "<!-- agent-feed:managed adapter=claude version=1 -->"


def claude_md() -> str:
    return f"""{MANAGED_MARKER}
@AGENTS.md

## Claude Code

Use `AGENTS.md` as the canonical project protocol.
Use `.claude/skills/` for Claude Code skill discovery.
Do not duplicate `.agents/rules/`; update the canonical files under `.agents/`.
"""


def sync(
    root: Path, *, dry_run: bool, force_generated: bool
) -> tuple[list[WriteAction], list[str]]:
    actions: list[WriteAction] = []
    errors: list[str] = []
    claude_file = root / "CLAUDE.md"
    skills_source = root / ".agents/skills"
    skills_target = root / ".claude/skills"
    target_root = root / ".claude"

    if claude_file.exists() and not is_managed_claude_md(claude_file):
        errors.append("CLAUDE.md exists and is unmanaged; move it aside or review before syncing")
    elif dry_run:
        actions.append(
            WriteAction(claude_file, "would update" if claude_file.exists() else "would create")
        )
    else:
        action = "update" if claude_file.exists() else "create"
        claude_file.write_text(claude_md(), encoding="utf-8")
        actions.append(WriteAction(claude_file, action))

    if not skills_source.exists() and not dry_run:
        errors.append("missing .agents/skills; cannot sync Claude skills")
        return actions, errors
    if skills_source.exists() and not skills_source.is_dir():
        errors.append(".agents/skills exists but is not a directory")
        return actions, errors
    if target_root.exists() and not target_root.is_dir():
        errors.append(".claude exists but is not a directory")
        return actions, errors
    if skills_target.exists() and not skills_target.is_dir():
        errors.append(".claude/skills exists but is not a directory")
        return actions, errors

    if (
        skills_target.exists()
        and not is_managed_skill_mirror(target_root)
    ):
        errors.append(
            ".claude/skills exists and is unmanaged; move it aside or review before syncing"
        )
        return actions, errors

    if dry_run:
        actions.append(WriteAction(skills_target, "would sync", ".agents/skills -> .claude/skills"))
        return actions, errors

    target_root.mkdir(parents=True, exist_ok=True)
    if skills_target.exists():
        shutil.rmtree(skills_target)
    shutil.copytree(skills_source, skills_target)
    (target_root / "README.md").write_text(skill_mirror_readme(), encoding="utf-8")
    actions.append(WriteAction(skills_target, "sync", ".agents/skills -> .claude/skills"))
    return actions, errors


def check(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    claude_file = root / "CLAUDE.md"
    skills_source = root / ".agents/skills"
    skills_target = root / ".claude/skills"

    if not claude_file.exists():
        errors.append("Claude adapter missing CLAUDE.md")
    elif not claude_file.is_file():
        errors.append("CLAUDE.md exists but is not a file")
    elif not is_managed_claude_md(claude_file):
        errors.append("CLAUDE.md exists but is not a managed Agent Feed adapter")
    elif "@AGENTS.md" not in claude_file.read_text(encoding="utf-8"):
        errors.append("CLAUDE.md must import @AGENTS.md")

    if not skills_target.exists():
        errors.append("Claude adapter missing .claude/skills")
    elif not skills_target.is_dir():
        errors.append(".claude/skills exists but is not a directory")
    elif skills_source.exists() and not same_tree(skills_source, skills_target):
        errors.append(".claude/skills is out of sync with .agents/skills")

    if (root / ".claude/rules").exists():
        warnings.append(
            ".claude/rules exists; Agent Feed does not manage Claude path-scoped rules yet"
        )

    return errors, warnings


def is_managed_claude_md(path: Path) -> bool:
    return path.is_file() and path.read_text(encoding="utf-8").startswith(MANAGED_MARKER)


def is_managed_skill_mirror(target_root: Path) -> bool:
    readme = target_root / "README.md"
    if not readme.is_file():
        return False
    text = readme.read_text(encoding="utf-8")
    return (
        text.startswith("# Synced AI Development Skills")
        and "generated from `.agents/skills/`" in text
    )


def skill_mirror_readme() -> str:
    return """# Synced AI Development Skills

This directory is generated from `.agents/skills/`.

Rules stay in `.agents/rules/` and are not synced here.
"""
