"""Client adapter sync and init conflict detection.

These services translate the user's selected client adapters into adapter
sync calls and detect filesystem state that would block ``init``.
"""

from __future__ import annotations

from pathlib import Path

from agent_feed.adapters import claude, codex, cursor
from agent_feed.fs import has_existing_content
from agent_feed.legacy_migration import backup_actions_include
from agent_feed.models import Client, WriteAction
from agent_feed.upgrade import is_installed


def sync_clients(
    root: Path,
    *,
    clients: tuple[Client, ...],
    dry_run: bool,
    force_generated: bool,
    prune_generated: bool = True,
) -> tuple[list[WriteAction], list[str]]:
    if not clients:
        return [WriteAction(path=root, action="skip", detail="no clients selected")], []

    if not (root / ".agents").exists() and not dry_run:
        return [], ["missing .agents; run agent-feed init first"]

    actions: list[WriteAction] = []
    errors: list[str] = []
    for client in clients:
        if client == Client.CODEX:
            actions.extend(codex.sync(root, dry_run=dry_run))
        elif client == Client.CLAUDE:
            client_actions, client_errors = claude.sync(
                root,
                dry_run=dry_run,
                force_generated=force_generated,
                prune_generated=prune_generated,
            )
            actions.extend(client_actions)
            errors.extend(client_errors)
        elif client == Client.CURSOR:
            client_actions, client_errors = cursor.sync(
                root, dry_run=dry_run, force_generated=force_generated
            )
            actions.extend(client_actions)
            errors.extend(client_errors)
    return actions, errors


def installed_clients(root: Path) -> tuple[Client, ...]:
    clients: list[Client] = [Client.CODEX]
    if (root / "CLAUDE.md").exists() or (root / ".claude/skills").exists():
        clients.append(Client.CLAUDE)
    if (root / ".cursor/rules/agent-feed.mdc").exists():
        clients.append(Client.CURSOR)
    return tuple(clients)


def planned_backup_resolves_init_adapter_error(
    error: str,
    backup_actions: list[WriteAction],
    *,
    target: Path,
) -> bool:
    if "CLAUDE.md" in error and backup_actions_include(
        backup_actions, Path("CLAUDE.md"), target=target
    ):
        return True
    if ".claude/skills" in error and backup_actions_include(
        backup_actions, Path(".claude/skills"), target=target
    ):
        return True
    if ".cursor/rules/agent-feed.mdc" in error and backup_actions_include(
        backup_actions, Path(".cursor/rules"), target=target
    ):
        return True
    return False


def find_init_conflicts(target: Path, clients: tuple[Client, ...]) -> list[str]:
    errors: list[str] = []
    if is_installed(target) and (target / ".agents/agent-feed.json").is_file():
        errors.append("Agent Feed is already installed; use agent-feed status or upgrade")
    if (target / "AGENTS.md").exists() and not (target / "AGENTS.md").is_file():
        errors.append("AGENTS.md exists but is not a file")
    if (target / ".agents").exists() and not (target / ".agents").is_dir():
        errors.append(".agents exists but is not a directory")
    if Client.CLAUDE in clients:
        claude_file = target / "CLAUDE.md"
        if claude_file.exists():
            if not claude_file.is_file():
                errors.append("CLAUDE.md exists but is not a file")
        if has_existing_content(target / ".claude/skills") and not claude.is_managed_skill_mirror(
            target / ".claude"
        ):
            skills_path = target / ".claude/skills"
            if not skills_path.is_dir():
                errors.append(".claude/skills exists but is not a directory")
    if Client.CURSOR in clients:
        cursor_file = target / ".cursor/rules/agent-feed.mdc"
        if cursor_file.exists() and not cursor_file.is_file():
            errors.append(".cursor/rules/agent-feed.mdc exists but is not a file")
    return errors
