"""Command line entry point for Agent Feed."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

import agent_feed
from agent_feed import __version__
from agent_feed.adapters import claude, codex, cursor
from agent_feed.checks import collect_status, run_checks
from agent_feed.choices import parse_choice_csv
from agent_feed.console import (
    console,
    print_check_report,
    print_status,
    print_welcome,
    print_write_plan,
)
from agent_feed.fs import has_existing_content
from agent_feed.models import (
    DEFAULT_CHECKS,
    DEFAULT_CLIENTS,
    DEFAULT_VERIFICATION_PROFILE,
    Check,
    Client,
    VerificationProfile,
    WriteAction,
)
from agent_feed.prompts import (
    can_prompt,
    prompt_checks,
    prompt_clients,
    prompt_confirm,
    prompt_main_action,
    prompt_path,
    prompt_text,
    prompt_verification_profile,
)
from agent_feed.templates import canonical_write_plan, write_text
from agent_feed.uninstall import apply_uninstall_plan, has_deletions, uninstall_plan
from agent_feed.update import (
    infer_project_name,
    infer_verification_profile,
    is_installed,
    update_plan as build_update_plan,
)


app = typer.Typer(
    name="agent-feed",
    help="Install and maintain reusable AI engineering protocol assets.",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the Agent Feed version and install location.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Agent Feed command group."""
    if version:
        print_version()
        raise typer.Exit(0)

    if ctx.invoked_subcommand is not None:
        return

    if can_prompt():
        print_welcome()
        action = prompt_main_action()
        code = _run_menu_action(action)
        raise typer.Exit(code)

    print_welcome()
    console.print(ctx.get_help())
    raise typer.Exit(0)


@app.command("welcome")
def welcome_cmd() -> None:
    """Show the Agent Feed welcome screen."""
    print_welcome()


def print_version() -> None:
    console.print(f"agent-feed {__version__}")
    console.print(f"executable: {Path(sys.argv[0]).resolve()}")
    if agent_feed.__file__:
        console.print(f"package: {Path(agent_feed.__file__).resolve().parent}")


@app.command("version", hidden=True)
def version_cmd() -> None:
    """Compatibility alias for --version."""
    print_version()


@app.command("init")
def init_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    project_name: Annotated[
        str | None,
        typer.Option("--project-name", help="Display name inserted into generated templates."),
    ] = None,
    clients: Annotated[
        str | None,
        typer.Option(
            "--clients",
            help="Comma-separated clients: codex,claude,cursor,all,none. Defaults to all.",
        ),
    ] = None,
    verification_profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            help="Project code verification profile: python,node,custom,none.",
        ),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option(
            "-i",
            "--interactive",
            help="Prompt for path, project name, clients, and verification profile.",
        ),
    ] = False,
    yes: Annotated[
        bool, typer.Option("-y", "--yes", help="Use defaults without prompting.")
    ] = False,
    no_input: Annotated[bool, typer.Option("--no-input", help="Never prompt.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview writes without changing files.")
    ] = False,
    force_generated: Annotated[
        bool,
        typer.Option("--force-generated", help="Overwrite managed generated adapters only."),
    ] = False,
) -> None:
    """Install AGENTS.md, .agents assets, and selected client adapters."""
    target = (path or Path(".")).resolve()
    selected_clients = _parse_clients(clients, default=DEFAULT_CLIENTS)
    selected_verification_profile = _parse_verification_profile(
        verification_profile, default=DEFAULT_VERIFICATION_PROFILE
    )

    if _should_prompt(
        interactive=interactive, no_input=no_input, yes=yes, explicit=path is not None
    ):
        print_welcome()
        target = prompt_path("Project path", target).resolve()
        project_name = prompt_text("Project display name", project_name or target.name)
        selected_clients = prompt_clients(selected_clients)
        selected_verification_profile = prompt_verification_profile(selected_verification_profile)
    else:
        project_name = project_name or target.name

    actions, errors = init_project(
        target=target,
        project_name=project_name,
        clients=selected_clients,
        verification_profile=selected_verification_profile,
        dry_run=dry_run,
        force_generated=force_generated,
    )
    if actions:
        print_write_plan(actions)
    if errors:
        _print_errors("Init blocked", errors)
        raise typer.Exit(3)

    if not dry_run:
        console.print("[green]agent-feed: init complete[/green]")
        console.print("Next: agent-feed check")


@app.command("i")
def init_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
    verification_profile: Annotated[str | None, typer.Option("--profile")] = None,
    yes: Annotated[bool, typer.Option("-y", "--yes")] = False,
) -> None:
    """Shortcut for init."""
    init_cmd(
        path=path,
        clients=clients,
        verification_profile=verification_profile,
        yes=yes,
        no_input=yes,
    )


@app.command("sync")
def sync_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    clients: Annotated[
        str | None,
        typer.Option(
            "--clients",
            help="Comma-separated clients: codex,claude,cursor,all,none. Defaults to all.",
        ),
    ] = None,
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="Prompt for clients.")
    ] = False,
    no_input: Annotated[bool, typer.Option("--no-input", help="Never prompt.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview writes without changing files.")
    ] = False,
    force_generated: Annotated[
        bool,
        typer.Option("--force-generated", help="Overwrite managed generated adapters only."),
    ] = False,
) -> None:
    """Sync selected client adapters from canonical Agent Feed assets."""
    target = (path or Path(".")).resolve()
    selected_clients = _parse_clients(clients, default=DEFAULT_CLIENTS)
    if (interactive or (clients is None and can_prompt() and not no_input)) and not no_input:
        selected_clients = prompt_clients(selected_clients)

    actions, errors = sync_clients(
        target,
        clients=selected_clients,
        dry_run=dry_run,
        force_generated=force_generated,
    )
    if actions:
        print_write_plan(actions)
    if errors:
        _print_errors("Sync blocked", errors)
        raise typer.Exit(3)
    console.print("[green]agent-feed: sync complete[/green]")


@app.command("s")
def sync_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
) -> None:
    """Shortcut for sync."""
    sync_cmd(path=path, clients=clients, no_input=True)


@app.command("sync-skills")
def sync_skills_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    force_generated: Annotated[bool, typer.Option("--force-generated")] = False,
) -> None:
    """Compatibility alias. Sync Claude skills and adapters from .agents."""
    sync_cmd(
        path=path,
        clients="claude",
        no_input=True,
        dry_run=dry_run,
        force_generated=force_generated,
    )


@app.command("update")
def update_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    project_name: Annotated[
        str | None,
        typer.Option(
            "--project-name",
            help="Override the project display name used for regenerated canonical assets.",
        ),
    ] = None,
    clients: Annotated[
        str | None,
        typer.Option(
            "--clients",
            help="Comma-separated clients: codex,claude,cursor,all,none. Defaults to all.",
        ),
    ] = None,
    verification_profile: Annotated[
        str | None,
        typer.Option("--profile", help="Project code verification profile."),
    ] = None,
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="Prompt for update options.")
    ] = False,
    no_input: Annotated[bool, typer.Option("--no-input", help="Never prompt.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview update diff without changing files.")
    ] = False,
) -> None:
    """Update installed Agent Feed assets without deleting local files."""
    target = (path or Path(".")).resolve()
    selected_clients = _parse_clients(clients, default=DEFAULT_CLIENTS)

    if _should_prompt(
        interactive=interactive, no_input=no_input, yes=False, explicit=path is not None
    ):
        print_welcome()
        target = prompt_path("Project path", target).resolve()
        project_name = prompt_text("Project display name", project_name or infer_project_name(target))
        selected_clients = prompt_clients(selected_clients)
        selected_verification_profile = prompt_verification_profile(
            _resolve_update_profile(target, verification_profile)
        )
    else:
        project_name = project_name or infer_project_name(target)
        selected_verification_profile = _resolve_update_profile(target, verification_profile)

    actions, errors = update_project(
        target=target,
        project_name=project_name,
        clients=selected_clients,
        verification_profile=selected_verification_profile,
        dry_run=dry_run,
    )
    if actions:
        print_write_plan(actions)
    if errors:
        _print_errors("Update blocked", errors)
        raise typer.Exit(3)

    if dry_run:
        console.print("agent-feed: update preview complete; no files changed")
    else:
        console.print("[green]agent-feed: update complete[/green]")


@app.command("upgrade")
def upgrade_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    project_name: Annotated[str | None, typer.Option("--project-name")] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
    verification_profile: Annotated[str | None, typer.Option("--profile")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    no_input: Annotated[bool, typer.Option("--no-input")] = False,
) -> None:
    """Alias for update."""
    update_cmd(
        path=path,
        project_name=project_name,
        clients=clients,
        verification_profile=verification_profile,
        dry_run=dry_run,
        no_input=no_input,
    )


@app.command("check")
def check_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    checks: Annotated[
        str | None,
        typer.Option(
            "--checks",
            "--only",
            help="Comma-separated checks: structure,skills,references,session,scripts,codex,claude,cursor,all.",
        ),
    ] = None,
    clients: Annotated[
        str | None,
        typer.Option("--clients", help="Add client checks: codex,claude,cursor,all,none."),
    ] = None,
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="Prompt for checks.")
    ] = False,
    no_input: Annotated[bool, typer.Option("--no-input", help="Never prompt.")] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Validate protocol assets and selected client adapters."""
    target = (path or Path(".")).resolve()
    selected_checks = _parse_checks(checks, default=DEFAULT_CHECKS)
    if clients:
        selected_checks = _with_client_checks(selected_checks, _parse_clients(clients, default=()))

    if (interactive or (checks is None and can_prompt() and not no_input)) and not no_input:
        selected_checks = prompt_checks(selected_checks)

    report = run_checks(target, selected_checks)
    print_check_report(report, as_json=json_output)
    if not report.ok:
        raise typer.Exit(1)


@app.command("c")
def check_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    checks: Annotated[str | None, typer.Option("--checks", "--only")] = None,
) -> None:
    """Shortcut for check."""
    check_cmd(path=path, checks=checks, no_input=True)


@app.command("status")
def status_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Show Agent Feed protocol and adapter status."""
    print_status(collect_status((path or Path(".")).resolve()), as_json=json_output)


@app.command("doctor")
def doctor_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    checks: Annotated[str | None, typer.Option("--checks", "--only")] = None,
    fix: Annotated[
        bool, typer.Option("--fix", help="Fix deterministic generated adapters.")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print machine-readable JSON.")
    ] = False,
) -> None:
    """Run full diagnostics and optionally fix managed generated adapters."""
    target = (path or Path(".")).resolve()
    selected_checks = _parse_checks(checks, default=DEFAULT_CHECKS)
    report = run_checks(target, selected_checks)

    if fix and not report.ok:
        actions, errors = sync_clients(
            target,
            clients=(Client.CLAUDE, Client.CURSOR),
            dry_run=False,
            force_generated=True,
        )
        if actions:
            print_write_plan(actions)
        if errors:
            _print_errors("Doctor fix blocked", errors)
            raise typer.Exit(3)
        report = run_checks(target, selected_checks)

    print_check_report(report, as_json=json_output)

    if not report.ok:
        raise typer.Exit(1)


@app.command("uninstall")
def uninstall_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview removals without deleting files.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("-y", "--yes", help="Delete managed files without prompting.")
    ] = False,
    no_input: Annotated[bool, typer.Option("--no-input", help="Never prompt.")] = False,
) -> None:
    """Remove Agent Feed-managed assets without deleting unmanaged user files."""
    target = (path or Path(".")).resolve()
    actions = uninstall_plan(target, dry_run=dry_run)

    if not actions:
        console.print("[green]agent-feed: no Agent Feed assets found[/green]")
        return

    print_write_plan(actions)
    if not has_deletions(actions):
        console.print("[yellow]agent-feed: no managed files are safe to delete[/yellow]")
        return
    if dry_run:
        console.print("Next: rerun with --yes to delete the managed files listed above.")
        return

    if not yes:
        if no_input or not can_prompt():
            console.print("[red]Uninstall blocked[/red]")
            console.print("- pass --yes to delete the managed files listed above")
            console.print("- pass --dry-run to preview removals without deleting files")
            raise typer.Exit(3)
        if not prompt_confirm("Delete only the managed Agent Feed files listed above?", False):
            console.print("agent-feed: uninstall canceled")
            return

    applied = apply_uninstall_plan(actions)
    if applied:
        print_write_plan(applied)
    console.print("[green]agent-feed: uninstall complete[/green]")


@app.command("preview")
def preview_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    project_name: Annotated[str | None, typer.Option("--project-name")] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
    verification_profile: Annotated[str | None, typer.Option("--profile")] = None,
) -> None:
    """Preview init writes or installed-project update diffs."""
    target = (path or Path(".")).resolve()
    selected_clients = _parse_clients(clients, default=DEFAULT_CLIENTS)
    if is_installed(target):
        actions, errors = update_project(
            target=target,
            project_name=project_name or infer_project_name(target),
            clients=selected_clients,
            verification_profile=_resolve_update_profile(target, verification_profile),
            dry_run=True,
        )
        if actions:
            print_write_plan(actions)
        if errors:
            _print_errors("Preview blocked", errors)
            raise typer.Exit(3)
        return

    selected_verification_profile = _parse_verification_profile(
        verification_profile, default=DEFAULT_VERIFICATION_PROFILE
    )
    actions = preview_project(
        target,
        project_name=project_name or target.name,
        clients=selected_clients,
        verification_profile=selected_verification_profile,
    )
    print_write_plan(actions)


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
    for path, content in canonical_write_plan(
        target,
        project_name,
        verification_profile,
    ):
        actions.append(write_text(path, content, dry_run=dry_run, force=force_generated))

    adapter_actions, adapter_errors = sync_clients(
        target,
        clients=clients,
        dry_run=dry_run,
        force_generated=force_generated,
    )
    return [*actions, *adapter_actions], adapter_errors


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


def update_project(
    *,
    target: Path,
    project_name: str,
    clients: tuple[Client, ...],
    verification_profile: VerificationProfile,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    canonical_actions, canonical_errors = build_update_plan(
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
    return [*canonical_actions, *adapter_actions], adapter_errors


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


def find_init_conflicts(target: Path, clients: tuple[Client, ...]) -> list[str]:
    errors: list[str] = []
    if (target / "AGENTS.md").exists():
        errors.append("AGENTS.md already exists")
    if has_existing_content(target / ".agents"):
        errors.append(".agents already exists and is not empty")
    if Client.CLAUDE in clients:
        claude_file = target / "CLAUDE.md"
        if claude_file.exists() and not claude.is_managed_claude_md(claude_file):
            errors.append("CLAUDE.md already exists and is unmanaged")
        if has_existing_content(target / ".claude/skills") and not claude.is_managed_skill_mirror(
            target / ".claude"
        ):
            errors.append(".claude/skills already exists and is unmanaged")
    if Client.CURSOR in clients:
        cursor_file = target / ".cursor/rules/agent-feed.mdc"
        if cursor_file.exists() and not cursor.is_managed_cursor_rule(cursor_file):
            errors.append(".cursor/rules/agent-feed.mdc already exists and is unmanaged")
    return errors


def _parse_clients(raw: str | None, *, default: tuple[Client, ...]) -> tuple[Client, ...]:
    try:
        return parse_choice_csv(
            raw,
            enum_type=Client,
            default=default,
            value_name="clients",
            allow_none=True,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _parse_checks(raw: str | None, *, default: tuple[Check, ...]) -> tuple[Check, ...]:
    try:
        return parse_choice_csv(
            raw,
            enum_type=Check,
            default=default,
            value_name="checks",
            allow_none=False,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _parse_verification_profile(
    raw: str | None, *, default: VerificationProfile
) -> VerificationProfile:
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    aliases = {
        "python-uv": VerificationProfile.PYTHON,
        "node-pnpm": VerificationProfile.NODE,
    }
    if value in aliases:
        return aliases[value]
    try:
        return VerificationProfile(value)
    except ValueError as exc:
        allowed = ", ".join(profile.value for profile in VerificationProfile)
        raise typer.BadParameter(
            f"unknown verification profile: {value}. Allowed values: {allowed}."
        ) from exc


def _resolve_update_profile(root: Path, raw: str | None) -> VerificationProfile:
    if raw is None or raw.strip() == "":
        return infer_verification_profile(root)
    return _parse_verification_profile(raw, default=infer_verification_profile(root))


def _with_client_checks(
    checks: tuple[Check, ...], clients: tuple[Client, ...]
) -> tuple[Check, ...]:
    mapped = {
        Client.CODEX: Check.CODEX,
        Client.CLAUDE: Check.CLAUDE,
        Client.CURSOR: Check.CURSOR,
    }
    return tuple(dict.fromkeys((*checks, *(mapped[client] for client in clients))))


def _should_prompt(*, interactive: bool, no_input: bool, yes: bool, explicit: bool) -> bool:
    if no_input or yes:
        return False
    return interactive or (can_prompt() and not explicit)


def _print_errors(title: str, errors: list[str]) -> None:
    console.print(f"[red]{title}[/red]")
    for error in errors:
        console.print(f"- {error}")


def _run_menu_action(action: str) -> int:
    try:
        if action == "exit":
            return 0
        if action == "init":
            init_cmd(interactive=True)
        elif action == "sync":
            sync_cmd(interactive=True)
        elif action == "update":
            update_cmd(interactive=True)
        elif action == "check":
            check_cmd(interactive=True)
        elif action == "status":
            status_cmd()
        elif action == "doctor":
            doctor_cmd()
        elif action == "preview":
            preview_cmd()
        elif action == "uninstall":
            uninstall_cmd()
        else:
            console.print(f"[red]Unknown menu action:[/red] {action}")
            return 2
    except typer.Exit as exc:
        return int(exc.exit_code or 0)
    return 0


def main() -> None:
    app()


if __name__ == "__main__":
    main()
