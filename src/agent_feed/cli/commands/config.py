"""``agent-feed config`` command group.

Patched names (``can_prompt``, ``prompt_confirm``, ``sync_clients``) and the
shared helper ``_trust_preflight_errors`` are routed through
``agent_feed.cli`` so that ``monkeypatch.setattr(cli, ...)`` keeps working.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agent_feed import cli as _cli
from agent_feed.asset_trust import (
    cleanup_missing_project_entries,
    missing_project_entries,
    sync_asset_trust,
    trust_preview_actions,
)
from agent_feed.cli._helpers import _print_errors
from agent_feed.config import check_config, get_config_value, set_config_value
from agent_feed.console import (
    console,
    print_action_result,
    print_config_check_report,
    print_stale_project_cleanup,
    print_write_plan,
)
from agent_feed.models import WriteAction
from agent_feed.services.clients import installed_clients
from agent_feed.skill_index import index_skill_metadata
from agent_feed.upgrade import (
    infer_project_name,
    infer_verification_profile,
    is_installed,
)
from agent_feed.upgrade import settings_asset_plan as build_settings_asset_plan

config_app = typer.Typer(
    name="config",
    help="Read and set project-visible .agents/agent-feed.json settings.",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def maybe_cleanup_missing_project_entries(*, dry_run: bool) -> tuple[list[WriteAction], list[str]]:
    stale_entries, errors = missing_project_entries()
    if errors:
        return [], errors
    if stale_entries is None:
        return [], []
    actions, errors = cleanup_missing_project_entries(dry_run=True)
    if errors:
        return [], errors
    if dry_run:
        return actions, []
    if not _cli.can_prompt():
        return [
            WriteAction(
                path=stale_entries.config_file,
                action="review",
                detail=(
                    f"{len(stale_entries.project_roots)} stale project "
                    "entries found; rerun in an interactive terminal to clean them up"
                ),
            )
        ], []
    print_stale_project_cleanup(stale_entries.config_file, stale_entries.project_roots)
    if not _cli.prompt_confirm(
        "Remove these stale project records from the user-level config?", True
    ):
        return [], []
    return cleanup_missing_project_entries(dry_run=False)


def prune_missing_project_entries(
    *,
    dry_run: bool,
    yes: bool,
    no_input: bool,
) -> tuple[list[WriteAction], list[str]]:
    stale_entries, errors = missing_project_entries()
    if errors:
        return [], errors
    if stale_entries is None:
        return [], []

    print_stale_project_cleanup(stale_entries.config_file, stale_entries.project_roots)
    actions, errors = cleanup_missing_project_entries(dry_run=True)
    if errors:
        return [], errors
    if dry_run:
        return actions, []
    if not yes:
        if no_input or not _cli.can_prompt():
            return [], [
                "stale project entries found; rerun `agent-feed config prune -y` "
                "to remove them without prompting"
            ]
        if not _cli.prompt_confirm(
            "Remove these stale project records from the user-level config?", True
        ):
            return [], []
    return cleanup_missing_project_entries(dry_run=False)


def apply_config_effects(target: Path, *, dry_run: bool) -> tuple[list[WriteAction], list[str]]:
    if not is_installed(target):
        return [], ["missing Agent Feed installation; run agent-feed init first"]

    project_name = infer_project_name(target)
    verification_profile = infer_verification_profile(target)
    selected_clients = installed_clients(target)

    cleanup_actions, cleanup_errors = maybe_cleanup_missing_project_entries(dry_run=dry_run)
    actions, errors = build_settings_asset_plan(
        target=target,
        project_name=project_name,
        verification_profile=verification_profile,
        dry_run=dry_run,
    )
    actions.extend(cleanup_actions)
    errors.extend(cleanup_errors)
    skill_actions, skill_errors = index_skill_metadata(target, dry_run=dry_run)
    actions.extend(skill_actions)
    errors.extend(skill_errors)
    adapter_actions, adapter_errors = _cli.sync_clients(
        target,
        clients=selected_clients,
        dry_run=dry_run,
        force_generated=True,
        prune_generated=False,
    )
    actions.extend(adapter_actions)
    errors.extend(adapter_errors)
    if not dry_run:
        trust_actions, trust_errors = sync_asset_trust(
            target,
            dry_run=False,
            accept_changed=True,
            project_name=project_name,
        )
        actions.extend(trust_actions)
        errors.extend(trust_errors)
    if dry_run:
        actions.extend(trust_preview_actions(target))
    return actions, errors


@config_app.command("get")
def config_get_cmd(
    key: Annotated[
        str | None,
        typer.Argument(
            help="Config key to read, for example verification_profile or settings.skills.default_import_trust."
        ),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Target project path. Defaults to cwd."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Read .agents/agent-feed.json or one config key."""
    target = (path or Path(".")).resolve()
    value, errors = get_config_value(target, key)
    if errors:
        _print_errors("Config read blocked", errors)
        raise typer.Exit(3)
    if json_output:
        import json

        print(json.dumps(value, indent=2, ensure_ascii=False))
    elif isinstance(value, (dict, list)):
        import json

        console.print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        console.print(str(value))


@config_app.command("check")
def config_check_cmd(
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Target project path. Defaults to cwd."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Validate project config and user-level Agent Feed trust config."""
    target = (path or Path(".")).resolve()
    report = check_config(target)
    print_config_check_report(report, as_json=json_output)
    if not report.ok:
        raise typer.Exit(1)


@config_app.command("prune")
def config_prune_cmd(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview stale project cleanup without writing files."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "-y",
            help="Remove stale project records with defaults; do not ask for confirmation.",
        ),
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
) -> None:
    """Remove stale project records from the user-level Agent Feed config."""
    actions, errors = prune_missing_project_entries(
        dry_run=dry_run,
        yes=yes,
        no_input=no_input,
    )
    if errors:
        _print_errors("Config prune blocked", errors)
        raise typer.Exit(3)
    if actions:
        print_write_plan(actions)
    if dry_run:
        console.print("[cyan]agent-feed: config prune preview complete; no files changed[/cyan]")
        return
    if not actions:
        print_action_result(
            title="Config Prune",
            message="No stale project entries found",
            kind="success",
            detail="The user-level Agent Feed config is already clean.",
        )
        return
    print_action_result(
        title="Config Prune",
        message="Stale project entries removed",
        kind="success",
        detail="Only user-level trust metadata was changed; project files were not touched.",
    )


@config_app.command("set")
def config_set_cmd(
    key: Annotated[
        str,
        typer.Argument(
            help="Config key to set, for example verification_profile or settings.session_state.max_carry_forwards."
        ),
    ],
    value: Annotated[
        str,
        typer.Argument(help="New value. JSON values are accepted, plain strings are preserved."),
    ],
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Target project path. Defaults to cwd."),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview config update without writing files.")
    ] = False,
) -> None:
    """Set one project-visible Agent Feed config value and refresh derived assets."""
    target = (path or Path(".")).resolve()
    if not dry_run:
        trust_errors = _cli._trust_preflight_errors(target)
        if trust_errors:
            _print_errors("Config update blocked", trust_errors)
            raise typer.Exit(3)

    actions, errors = set_config_value(target, key=key, raw_value=value, dry_run=dry_run)
    if errors:
        _print_errors("Config update blocked", errors)
        raise typer.Exit(3)

    if not dry_run:
        effect_actions, effect_errors = apply_config_effects(target, dry_run=False)
        actions.extend(effect_actions)
        errors.extend(effect_errors)
        if errors:
            _print_errors("Config update blocked", errors)
            raise typer.Exit(3)

    if actions:
        print_write_plan(actions, show_diffs=True)
    if dry_run:
        console.print("[cyan]agent-feed: config preview complete; no files changed[/cyan]")
        return
    config_report = check_config(target)
    print_config_check_report(config_report, as_json=False)
    if not config_report.ok:
        raise typer.Exit(3)
    console.print("[green]agent-feed: config updated[/green]")
