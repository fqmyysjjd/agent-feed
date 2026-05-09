"""Project lifecycle services: init, preview, upgrade orchestration.

These functions compose lower-level building blocks (canonical write plans,
legacy migration backups, adapter sync, trust sync) into the user-facing
``init``, ``preview``, ``status``, and ``upgrade`` flows. They may print
Rich progress UI but do not import Typer.
"""

from __future__ import annotations

from pathlib import Path

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from agent_feed import __version__
from agent_feed.asset_trust import sync_asset_trust, trust_preview_actions
from agent_feed.checks import downgrade_warnings
from agent_feed.console import console
from agent_feed.install_source import is_older_version
from agent_feed.legacy_migration import backup_legacy_ai_assets
from agent_feed.models import (
    DEFAULT_CLIENTS,
    DEFAULT_VERIFICATION_PROFILE,
    Client,
    VerificationProfile,
    WriteAction,
)
from agent_feed.prompts import prompt_confirm
from agent_feed.services.clients import (
    find_init_conflicts,
    installed_clients,
    planned_backup_resolves_init_adapter_error,
    sync_clients,
)
from agent_feed.templates import canonical_write_plan, write_text
from agent_feed.upgrade import (
    infer_project_name,
    infer_verification_profile,
    installed_version,
    is_installed,
    upgrade_plan as build_upgrade_plan,
)


def init_project(
    *,
    target: Path,
    project_name: str,
    clients: tuple[Client, ...],
    verification_profile: VerificationProfile,
    dry_run: bool,
    force_generated: bool,
) -> tuple[list[WriteAction], list[str]]:
    errors = find_init_conflicts(target, clients)
    if errors:
        return [], errors

    actions: list[WriteAction] = []
    backup_actions, backup_errors = backup_legacy_ai_assets(
        target,
        project_name=project_name,
        verification_profile=verification_profile,
        dry_run=dry_run,
    )
    if backup_errors:
        return backup_actions, backup_errors
    actions.extend(backup_actions)

    plan = canonical_write_plan(
        target,
        project_name,
        verification_profile,
    )
    if dry_run:
        for path, content in plan:
            actions.append(write_text(path, content, dry_run=True, force=force_generated))
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[dim]{task.fields[path]}[/dim]"),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                "Copying Agent Feed assets",
                total=len(plan),
                path="",
            )
            for path, content in plan:
                rel_path = path.relative_to(target)
                progress.update(task_id, path=rel_path.as_posix())
                actions.append(write_text(path, content, dry_run=False, force=force_generated))
                progress.advance(task_id)

    adapter_actions, adapter_errors = sync_clients(
        target,
        clients=clients,
        dry_run=dry_run,
        force_generated=force_generated,
    )
    if dry_run and backup_actions:
        adapter_errors = [
            error
            for error in adapter_errors
            if not planned_backup_resolves_init_adapter_error(error, backup_actions, target=target)
        ]
    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=dry_run,
        accept_changed=True,
        project_name=project_name,
    )
    return [*actions, *adapter_actions, *trust_actions], [*adapter_errors, *trust_errors]


def init_backup_dir(actions: list[WriteAction], *, target: Path) -> Path | None:
    for action in actions:
        if action.action != "backup":
            continue
        detail = action.detail.strip()
        if not detail.startswith("-> "):
            continue
        destination = (target / detail.removeprefix("-> ")).resolve()
        try:
            relative = destination.relative_to(target / ".feed-backup")
        except ValueError:
            continue
        if relative.parts:
            return target / ".feed-backup" / relative.parts[0]
    return None


def preview_project(
    target: Path,
    *,
    project_name: str,
    clients: tuple[Client, ...],
    verification_profile: VerificationProfile,
) -> list[WriteAction]:
    actions = [
        WriteAction(path=path, action="would update" if path.exists() else "would create")
        for path, _content in canonical_write_plan(
            target,
            project_name,
            verification_profile,
        )
    ]
    adapter_actions, _errors = sync_clients(
        target,
        clients=clients,
        dry_run=True,
        force_generated=False,
    )
    return [*actions, *adapter_actions]


def preview_actions(
    *,
    target: Path,
    project_name: str | None,
    clients: tuple[Client, ...] | None,
    verification_profile: VerificationProfile | None,
) -> tuple[list[WriteAction], list[str]]:
    if is_installed(target):
        selected_clients = clients if clients is not None else installed_clients(target)
        actions, errors = upgrade_project(
            target=target,
            project_name=project_name or infer_project_name(target),
            clients=selected_clients,
            verification_profile=infer_verification_profile(target),
            dry_run=True,
        )
        actions.extend(trust_preview_actions(target))
        downgrade_warning = _downgrade_warning(target)
        if downgrade_warning:
            actions.insert(0, downgrade_warning)
        return actions, errors

    return (
        preview_project(
            target,
            project_name=project_name or target.name,
            clients=clients if clients is not None else DEFAULT_CLIENTS,
            verification_profile=verification_profile or DEFAULT_VERIFICATION_PROFILE,
        ),
        [],
    )


def _downgrade_warning(target: Path) -> WriteAction | None:
    """Return a visible warning action when the CLI is older than the project."""
    warnings = downgrade_warnings(target)
    if not warnings:
        return None
    return WriteAction(
        path=target / ".agents/agent-feed.json",
        action="review",
        detail=warnings[0],
    )


def downgrade_preflight_errors(*, target: Path, interactive: bool) -> list[str]:
    project_version = installed_version(target)
    if not project_version or not is_older_version(__version__, project_version):
        return []

    message = (
        f"This project was last managed by Agent Feed {project_version}, "
        f"but this CLI is {__version__}. Running upgrade with an older CLI can "
        "rewrite managed assets to older templates."
    )
    if interactive and prompt_confirm(
        f"{message} Continue with a downgrade?",
        default=False,
    ):
        return []

    return [
        message,
        "Update this CLI first, or rerun with --allow-downgrade if this downgrade is intentional.",
    ]


def upgrade_project(
    *,
    target: Path,
    project_name: str,
    clients: tuple[Client, ...],
    verification_profile: VerificationProfile,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    canonical_actions, canonical_errors = build_upgrade_plan(
        target,
        project_name=project_name,
        verification_profile=verification_profile,
        dry_run=dry_run,
    )
    if canonical_errors:
        return canonical_actions, canonical_errors

    adapter_actions, adapter_errors = sync_clients(
        target,
        clients=clients,
        dry_run=dry_run,
        force_generated=True,
        prune_generated=False,
    )
    if dry_run:
        return [*canonical_actions, *adapter_actions], adapter_errors

    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=dry_run,
        accept_changed=True,
        project_name=project_name,
    )
    return [*canonical_actions, *adapter_actions, *trust_actions], [
        *adapter_errors,
        *trust_errors,
    ]
