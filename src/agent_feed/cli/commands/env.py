"""``agent-feed env`` command group.

Routes through ``agent_feed.cli`` for ``can_prompt`` and ``prompt_confirm`` so
that ``monkeypatch.setattr(cli, ...)`` keeps working from tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agent_feed import cli as _cli
from agent_feed.asset_trust import AGENT_FEED_HOME_ENV
from agent_feed.cli._helpers import _print_errors
from agent_feed.console import console, print_action_result, print_write_plan
from agent_feed.env_setup import (
    SHELL_AUTO,
    apply_env_uninstall_plan,
    current_agent_feed_home,
    env_uninstall_plan,
    get_env_status,
    recommended_agent_feed_home,
    resolve_shell,
    setup_agent_feed_home,
    shell_export_text,
)
from agent_feed.uninstall import has_deletions

env_app = typer.Typer(
    name="env",
    help="Set up the external Agent Feed home used for trusted AI asset hashes.",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@env_app.command("status")
def env_status_cmd(
    path: Annotated[
        Path | None,
        typer.Argument(help="Project path used to verify AGENT_FEED_HOME is external."),
    ] = None,
) -> None:
    """Show Agent Feed environment configuration status."""
    status = get_env_status((path or Path(".")).resolve())
    if status.ok:
        print_action_result(
            title="Environment Status",
            message="Agent Feed environment is ready",
            kind="success",
        )
    else:
        print_action_result(
            title="Environment Status",
            message="Agent Feed environment needs setup",
            kind="warning",
        )
    console.print(f"{AGENT_FEED_HOME_ENV}: {status.home or '<not set>'}")
    console.print(f"recommended: {status.recommendation}")
    if status.config_file:
        console.print(f"config: {status.config_file}")
    if status.errors:
        _print_errors("Environment diagnostics", list(status.errors))
        raise typer.Exit(1)


@env_app.command("print")
def env_print_cmd(
    home: Annotated[
        Path | None,
        typer.Option("--home", help="Agent Feed home to print. Defaults to recommendation."),
    ] = None,
    shell: Annotated[
        str,
        typer.Option("--shell", help="Shell format: auto,zsh,bash,fish,powershell."),
    ] = SHELL_AUTO,
) -> None:
    """Print the shell command that configures AGENT_FEED_HOME."""
    target_home = home.expanduser() if home is not None else recommended_agent_feed_home()
    resolved_shell, shell_error = resolve_shell(shell)
    if shell_error or resolved_shell is None:
        _print_errors("Environment print blocked", [shell_error or "unsupported shell"])
        raise typer.Exit(3)
    print(shell_export_text(target_home, resolved_shell))


@env_app.command("setup")
def env_setup_cmd(
    path: Annotated[
        Path | None,
        typer.Argument(help="Project path used to ensure AGENT_FEED_HOME is external."),
    ] = None,
    home: Annotated[
        Path | None,
        typer.Option(
            "--home",
            help="External Agent Feed home. Defaults to the user-level recommendation.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing AGENT_FEED_HOME value."),
    ] = False,
    shell: Annotated[
        str,
        typer.Option("--shell", help="Shell to configure: auto,zsh,bash,fish,powershell."),
    ] = SHELL_AUTO,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview environment writes.")] = False,
) -> None:
    """Create ~/.agent-feed and persist AGENT_FEED_HOME for the current user."""
    result = setup_agent_feed_home(
        home=home,
        target=(path or Path(".")).resolve(),
        shell=shell,
        dry_run=dry_run,
        force=force,
    )
    if _cli._should_offer_env_replace(result.errors, force=force, dry_run=dry_run):
        current_home = current_agent_feed_home()
        if _cli.prompt_confirm(
            f"Replace existing {AGENT_FEED_HOME_ENV} ({current_home}) with {result.home}?",
            False,
        ):
            result = setup_agent_feed_home(
                home=home,
                target=(path or Path(".")).resolve(),
                shell=shell,
                dry_run=dry_run,
                force=True,
            )
    if result.actions:
        print_write_plan(list(result.actions))
    if result.errors:
        _print_errors("Environment setup blocked", list(result.errors))
        raise typer.Exit(3)
    if dry_run:
        print_action_result(
            title="Environment Setup",
            message="Preview complete",
            kind="info",
            detail="No files or shell settings were changed.",
        )
        return
    print_action_result(
        title="Environment Setup",
        message="Environment configured",
        kind="success",
        detail="The user-level Agent Feed home and shell binding are ready.",
    )
    console.print(f"{AGENT_FEED_HOME_ENV}: {result.home}")


@env_app.command("uninstall")
def env_uninstall_cmd(
    home: Annotated[
        Path | None,
        typer.Option(
            "--home",
            help=(
                "Agent Feed home to remove from shell config. With --remove-home, "
                "also delete this directory."
            ),
        ),
    ] = None,
    shell: Annotated[
        str,
        typer.Option("--shell", help="Shell to clean: auto,zsh,bash,fish,powershell."),
    ] = SHELL_AUTO,
    remove_home: Annotated[
        bool,
        typer.Option(
            "--remove-home",
            help="Also delete the user-level ~/.agent-feed config/trust directory.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview environment cleanup without changing files."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "-y",
            help="Apply the cleanup plan with defaults; do not ask for confirmation.",
        ),
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
) -> None:
    """Remove the Agent Feed environment variable and optionally its user config home."""
    actions, errors = env_uninstall_plan(
        home=home,
        shell=shell,
        dry_run=dry_run,
        remove_home=remove_home,
    )
    if actions:
        print_write_plan(actions)
    if errors:
        _print_errors("Environment uninstall blocked", errors)
        raise typer.Exit(3)
    if not actions:
        print_action_result(
            title="Environment Cleanup",
            message="Nothing to remove",
            kind="info",
            detail="No Agent Feed environment changes were found.",
        )
        return
    if not has_deletions(actions):
        print_action_result(
            title="Environment Cleanup",
            message="Nothing to remove",
            kind="info",
            detail="No Agent Feed environment changes were found.",
        )
        return
    if dry_run:
        print_action_result(
            title="Environment Cleanup",
            message="Preview complete",
            kind="info",
            detail="Rerun with -y to apply the environment cleanup plan.",
        )
        return
    if not yes:
        if no_input or not _cli.can_prompt():
            print_action_result(
                title="Environment Cleanup Blocked",
                message="Confirmation is required before removing the environment setup",
                kind="error",
                detail="Pass -y to apply the plan, or pass --dry-run to preview it first.",
            )
            raise typer.Exit(3)
        prompt_text = "Remove Agent Feed environment variable"
        if remove_home:
            prompt_text += " and delete the user-level Agent Feed home"
        if not _cli.prompt_confirm(f"{prompt_text}?", False):
            print_action_result(
                title="Environment Cleanup",
                message="Canceled",
                kind="warning",
                detail="The Agent Feed environment setup was left unchanged.",
            )
            return
    applied = apply_env_uninstall_plan(actions, shell=shell)
    if applied:
        print_write_plan(applied)
    print_action_result(
        title="Environment Cleanup",
        message="Environment uninstall complete",
        kind="success",
        detail="The managed shell binding and optional user-level home were cleaned up.",
    )
