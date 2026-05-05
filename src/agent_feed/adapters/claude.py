"""Claude Code adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from agent_feed.fs import same_tree
from agent_feed.models import WriteAction
from agent_feed.project_settings import (
    DEFAULT_CLAUDE_REQUIRED_SNIPPETS,
    read_project_settings,
)

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
    root: Path,
    *,
    dry_run: bool,
    force_generated: bool,
    prune_generated: bool = True,
) -> tuple[list[WriteAction], list[str]]:
    actions: list[WriteAction] = []
    errors: list[str] = []
    claude_file = root / "CLAUDE.md"
    skills_source = root / ".agents/skills"
    skills_target = root / ".claude/skills"
    target_root = root / ".claude"

    if claude_file.exists():
        if not claude_file.is_file():
            errors.append("CLAUDE.md exists but is not a file")
        else:
            missing = missing_required_snippets(claude_file, root=root)
            if missing:
                errors.append(
                    "CLAUDE.md is missing required Agent Feed references: " + ", ".join(missing)
                )
            else:
                actions.append(
                    WriteAction(
                        claude_file,
                        "skip",
                        "contains required Agent Feed references",
                    )
                )
    elif dry_run:
        actions.append(WriteAction(claude_file, "would create"))
    else:
        claude_file.write_text(claude_md(), encoding="utf-8")
        actions.append(WriteAction(claude_file, "create"))

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

    if skills_target.exists() and not is_managed_skill_mirror(target_root):
        errors.append(
            ".claude/skills exists and is unmanaged; move it aside or review before syncing"
        )
        return actions, errors

    if dry_run:
        detail = ".agents/skills -> .claude/skills"
        if not prune_generated:
            detail = f"{detail} (non-destructive; stale files are not removed)"
        action = "skip" if same_tree(skills_source, skills_target) else "would sync"
        actions.append(WriteAction(skills_target, action, detail))
        return actions, errors

    target_root.mkdir(parents=True, exist_ok=True)
    if same_tree(skills_source, skills_target):
        actions.append(WriteAction(skills_target, "skip", ".agents/skills already synced"))
        return actions, errors
    if skills_target.exists() and prune_generated:
        shutil.rmtree(skills_target)
    if prune_generated:
        shutil.copytree(skills_source, skills_target)
    else:
        merge_tree(skills_source, skills_target)
    (target_root / "README.md").write_text(skill_mirror_readme(), encoding="utf-8")
    detail = ".agents/skills -> .claude/skills"
    if not prune_generated:
        detail = f"{detail} (non-destructive; stale files are not removed)"
    actions.append(WriteAction(skills_target, "sync", detail))
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
    else:
        for snippet in missing_required_snippets(claude_file, root=root):
            errors.append(f"CLAUDE.md must contain {snippet}")

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


def missing_required_snippets(path: Path, *, root: Path | None = None) -> list[str]:
    text = path.read_text(encoding="utf-8")
    snippets = (
        read_project_settings(root).claude.required_snippets
        if root is not None
        else DEFAULT_CLAUDE_REQUIRED_SNIPPETS
    )
    return [snippet for snippet in snippets if snippet not in text]


def is_managed_skill_mirror(target_root: Path) -> bool:
    readme = target_root / "README.md"
    if not readme.is_file():
        return False
    text = readme.read_text(encoding="utf-8")
    return (
        text.startswith("# Synced AI Development Skills")
        and "generated from `.agents/skills/`" in text
    )


def merge_tree(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for source_path in sorted(source.rglob("*")):
        target_path = target / source_path.relative_to(source)
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def skill_mirror_readme() -> str:
    return """# Synced AI Development Skills

This directory is generated from `.agents/skills/`.

Rules stay in `.agents/rules/` and are not synced here.
"""
