"""Safe removal of Agent Feed-managed project assets."""

from __future__ import annotations

import shutil
from pathlib import Path

from agent_feed.adapters import claude, cursor
from agent_feed.asset_trust import project_trust_uninstall_plan, remove_project_trust_state
from agent_feed.fs import same_tree
from agent_feed.models import WriteAction


def uninstall_plan(root: Path, *, dry_run: bool) -> list[WriteAction]:
    action = "would delete" if dry_run else "delete"
    actions: list[WriteAction] = []

    _plan_file(
        actions,
        root / "CLAUDE.md",
        action=action,
        safe=claude.is_managed_claude_md(root / "CLAUDE.md"),
        unmanaged_detail="unmanaged Claude instructions; not removed",
        managed_detail="managed Claude adapter",
    )

    claude_root = root / ".claude"
    claude_skills = claude_root / "skills"
    claude_readme = claude_root / "README.md"
    has_managed_claude_skills = claude.is_managed_skill_mirror(claude_root)
    _plan_path(
        actions,
        claude_skills,
        action=action,
        safe=has_managed_claude_skills,
        unmanaged_detail="unmanaged Claude skills; not removed",
        managed_detail="managed Claude skills mirror",
    )
    _plan_file(
        actions,
        claude_readme,
        action=action,
        safe=has_managed_claude_skills,
        unmanaged_detail="unmanaged Claude README; not removed",
        managed_detail="managed Claude skills README",
    )

    cursor_rule = root / ".cursor/rules/agent-feed.mdc"
    _plan_file(
        actions,
        cursor_rule,
        action=action,
        safe=cursor.is_managed_cursor_rule(cursor_rule),
        unmanaged_detail="unmanaged Cursor rule; not removed",
        managed_detail="managed Cursor adapter",
    )

    codex_skills = root / ".codex/skills"
    agents_skills = root / ".agents/skills"
    _plan_path(
        actions,
        codex_skills,
        action=action,
        safe=agents_skills.is_dir()
        and codex_skills.is_dir()
        and same_tree(agents_skills, codex_skills),
        unmanaged_detail="legacy .codex/skills is not a verified mirror; not removed",
        managed_detail="legacy Agent Feed Codex skill mirror",
    )

    agents_md = root / "AGENTS.md"
    _plan_file(
        actions,
        agents_md,
        action=action,
        safe=is_agent_feed_agents_md(agents_md),
        unmanaged_detail="unmanaged AGENTS.md; not removed",
        managed_detail="Agent Feed entry contract",
    )

    agents_dir = root / ".agents"
    _plan_path(
        actions,
        agents_dir,
        action=action,
        safe=is_agent_feed_agents_dir(agents_dir),
        unmanaged_detail="unmanaged .agents directory; not removed",
        managed_detail="Agent Feed protocol directory",
    )

    actions.extend(project_trust_uninstall_plan(root, dry_run=dry_run))
    return actions


def apply_uninstall_plan(root: Path, actions: list[WriteAction]) -> list[WriteAction]:
    applied: list[WriteAction] = []
    for item in actions:
        if item.action != "delete":
            continue
        if not item.path.exists():
            applied.append(WriteAction(item.path, "skip", "already absent"))
            continue
        if item.path.is_dir():
            shutil.rmtree(item.path)
        else:
            item.path.unlink()
        applied.append(WriteAction(item.path, "deleted", item.detail))

    for directory in {
        action.path.parent
        for action in actions
        if action.action == "delete"
        and action.path.name in {"agent-feed.mdc", "README.md", "skills"}
    }:
        remove_empty_parents(directory)

    applied.extend(remove_project_trust_state(root))
    return applied


def has_deletions(actions: list[WriteAction]) -> bool:
    return any(
        action.action in {"delete", "would delete", "update", "would update"} for action in actions
    )


def is_agent_feed_agents_md(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return (
        "AI Development Instructions" in text
        and "repository-level entry contract" in text
        and ".agents/rules/outcome-boundary.md" in text
    )


def is_agent_feed_agents_dir(path: Path) -> bool:
    readme = path / "README.md"
    return (
        path.is_dir()
        and readme.is_file()
        and "# AI Development Engineering" in readme.read_text(encoding="utf-8")
        and (path / "rules/outcome-boundary.md").is_file()
        and (path / "scripts/check-agent-assets.sh").is_file()
    )


def remove_empty_parents(path: Path) -> None:
    while path.name in {"rules", ".cursor", ".claude", ".codex"}:
        try:
            path.rmdir()
        except OSError:
            return
        path = path.parent


def _plan_file(
    actions: list[WriteAction],
    path: Path,
    *,
    action: str,
    safe: bool,
    unmanaged_detail: str,
    managed_detail: str,
) -> None:
    _plan_path(
        actions,
        path,
        action=action,
        safe=safe,
        unmanaged_detail=unmanaged_detail,
        managed_detail=managed_detail,
    )


def _plan_path(
    actions: list[WriteAction],
    path: Path,
    *,
    action: str,
    safe: bool,
    unmanaged_detail: str,
    managed_detail: str,
) -> None:
    if not path.exists():
        return
    if safe:
        actions.append(WriteAction(path, action, managed_detail))
    else:
        actions.append(WriteAction(path, "skip", unmanaged_detail))
