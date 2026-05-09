"""Verification commands: ``check``, ``status``, ``preview``.

Patched names (``can_prompt``, ``prompt_checks``, ``prompt_view_diff_key``)
flow through ``agent_feed.cli`` so ``monkeypatch.setattr(cli, ...)`` keeps
working from tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agent_feed import cli as _cli
from agent_feed.checks import collect_status, run_checks
from agent_feed.cli._helpers import (
    _parse_checks,
    _parse_clients,
    _parse_verification_profile,
    _print_errors,
    _with_client_checks,
)
from agent_feed.console import (
    has_diff_details,
    print_check_report,
    print_diff_hint,
    print_status,
    print_write_plan,
    print_write_plan_with_title,
)
from agent_feed.models import (
    DEFAULT_CHECKS,
    DEFAULT_CLIENTS,
    DEFAULT_VERIFICATION_PROFILE,
    Check,
    WriteAction,
)
from agent_feed.services.lifecycle import preview_actions


def print_inspection_plan(actions: list[WriteAction], *, target: Path) -> None:
    print_write_plan_with_title(actions, title=f"Agent Feed Inspection: {target}")
    if not has_diff_details(actions):
        return
    interactive = _cli.can_prompt()
    print_diff_hint(
        command=f"agent-feed preview {target}",
        interactive=interactive,
    )
    if interactive and _cli.prompt_view_diff_key():
        preview_cmd(path=target)


def check_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    checks: Annotated[
        str | None,
        typer.Option(
            "--checks",
            "--only",
            help="Comma-separated checks: structure,config,skills,references,session,scripts,codex,claude,cursor,all.",
        ),
    ] = None,
    clients: Annotated[
        str | None,
        typer.Option("--clients", help="Add client checks: codex,claude,cursor,all,none."),
    ] = None,
    all_checks: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Run every protocol and client check without opening the checkbox prompt.",
        ),
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Validate AI development docs/assets and selected client adapters."""
    target = (path or Path(".")).resolve()
    selected_checks = tuple(Check) if all_checks else _parse_checks(checks, default=DEFAULT_CHECKS)
    if clients:
        selected_checks = _with_client_checks(selected_checks, _parse_clients(clients, default=()))

    if (
        not all_checks
        and checks is None
        and _cli.can_prompt()
        and not no_input
    ):
        selected_checks = _cli.prompt_checks(selected_checks)
        if not selected_checks:
            _print_errors("Check blocked", ["select at least one check or pass -a"])
            raise typer.Exit(3)

    report = run_checks(target, selected_checks)
    print_check_report(report, as_json=json_output)
    if not report.ok:
        raise typer.Exit(1)


def check_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    checks: Annotated[str | None, typer.Option("--checks", "--only")] = None,
) -> None:
    """Shortcut for check."""
    check_cmd(path=path, checks=checks, no_input=True)


def status_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Inspect current Agent Feed drift and adapter health."""
    target = (path or Path(".")).resolve()
    if json_output:
        print_status(collect_status(target), as_json=True)
        return
    actions, errors = preview_actions(
        target=target,
        project_name=None,
        clients=None,
        verification_profile=None,
    )
    if actions:
        print_inspection_plan(actions, target=target)
    if errors:
        _print_errors("Status blocked", errors)
        raise typer.Exit(3)


def preview_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    project_name: Annotated[
        str | None,
        typer.Option("--project-name", help="Override the display name used in previewed files."),
    ] = None,
    clients: Annotated[
        str | None,
        typer.Option("--clients", help="Comma-separated clients: codex,claude,cursor,all,none."),
    ] = None,
    verification_profile: Annotated[
        str | None,
        typer.Option(
            "--profile", help="Verification profile to preview before a project is initialized."
        ),
    ] = None,
) -> None:
    """Show full init writes or installed-project upgrade diffs."""
    target = (path or Path(".")).resolve()
    selected_clients = (
        _parse_clients(clients, default=DEFAULT_CLIENTS) if clients is not None else None
    )
    selected_verification_profile = (
        _parse_verification_profile(verification_profile, default=DEFAULT_VERIFICATION_PROFILE)
        if verification_profile is not None
        else None
    )
    actions, errors = preview_actions(
        target=target,
        project_name=project_name,
        clients=selected_clients,
        verification_profile=selected_verification_profile,
    )
    if actions:
        print_write_plan(actions, show_diffs=True)
    if errors:
        _print_errors("Preview blocked", errors)
        raise typer.Exit(3)


def register(app: typer.Typer) -> None:
    """Register verification commands on the main Typer app."""
    app.command("check")(check_cmd)
    app.command("c", hidden=True)(check_alias)
    app.command("status")(status_cmd)
    app.command("preview")(preview_cmd)
