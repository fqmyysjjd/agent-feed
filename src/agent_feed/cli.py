"""Command line entry point for Agent Feed."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

import agent_feed
from agent_feed import __version__
from agent_feed.adapters import claude, codex, cursor
from agent_feed.asset_trust import (
    AGENT_FEED_HOME_ENV,
    CONFIG_FILE_NAME,
    check_asset_trust,
    cleanup_missing_project_entries,
    configured_github_token,
    legacy_config_path,
    project_local_config_errors,
    recommended_agent_feed_home,
    save_github_token,
    settings_config_path,
    sync_asset_trust,
    trust_config_path,
    trust_preview_actions,
    validate_config_shape,
)
from agent_feed.checks import collect_status, run_checks
from agent_feed.choices import parse_choice_csv
from agent_feed.config import get_config_value, set_config_value
from agent_feed.console import (
    console,
    has_diff_details,
    print_diff_details,
    print_diff_hint,
    print_check_report,
    print_error_panel,
    print_markdown_panel,
    print_recommended_command,
    print_status,
    print_welcome,
    print_write_plan,
    print_write_plan_with_title,
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
from agent_feed.env_setup import (
    SHELL_AUTO,
    apply_env_uninstall_plan,
    current_agent_feed_home,
    env_uninstall_plan,
    get_env_status,
    resolve_shell,
    setup_agent_feed_home,
    shell_export_text,
    suggested_agent_feed_home,
)
from agent_feed.prompts import (
    can_prompt,
    prompt_checks,
    prompt_clients,
    prompt_clients_step,
    prompt_confirm,
    prompt_main_action,
    prompt_path_step,
    prompt_secret,
    prompt_skill_hub_keyword,
    prompt_skill_hub_selection,
    prompt_text_step,
    prompt_verification_profile_step,
    prompt_view_diff_key,
)
from agent_feed.skill_hub import (
    CURATED_HUBS,
    RemoteSkill,
    RemoteSkillPackage,
    fetch_remote_skill,
    install_remote_skill_package,
    preview_skill_tree,
    search_remote_skills,
)
from agent_feed.skill_index import index_skill_metadata
from agent_feed.templates import canonical_write_plan, write_text
from agent_feed.uninstall import apply_uninstall_plan, has_deletions, uninstall_plan
from agent_feed.upgrade import (
    infer_project_name,
    infer_verification_profile,
    is_installed,
    settings_asset_plan as build_settings_asset_plan,
    upgrade_plan as build_upgrade_plan,
)


app = typer.Typer(
    name="agent-feed",
    help=(
        "Install, verify, and maintain AGENTS.md, .agents rules, skills, and AI client adapters."
    ),
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
env_app = typer.Typer(
    name="env",
    help="Set up the external Agent Feed home used for trusted AI asset hashes.",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(env_app, name="env")
config_app = typer.Typer(
    name="config",
    help="Read and set project-visible .agents/agent-feed.json settings.",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(config_app, name="config")


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
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


@app.command("welcome", hidden=True)
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
        console.print("[green]Agent Feed environment is ready[/green]")
    else:
        console.print("[yellow]Agent Feed environment needs setup[/yellow]")
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
    if _should_offer_env_replace(result.errors, force=force, dry_run=dry_run):
        current_home = current_agent_feed_home()
        if prompt_confirm(
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
        console.print("[cyan]agent-feed: environment setup preview complete[/cyan]")
        return
    console.print("[green]agent-feed: environment configured[/green]")
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
        console.print("[green]agent-feed: no Agent Feed environment changes found[/green]")
        return
    if not has_deletions(actions):
        console.print("[green]agent-feed: no Agent Feed environment changes found[/green]")
        return
    if dry_run:
        console.print("Next: rerun with -y to apply the environment cleanup plan.")
        return
    if not yes:
        if no_input or not can_prompt():
            console.print("[red]Environment uninstall blocked[/red]")
            console.print("- pass -y to apply the environment cleanup plan")
            console.print("- pass --dry-run to preview changes")
            raise typer.Exit(3)
        prompt_text = "Remove Agent Feed environment variable"
        if remove_home:
            prompt_text += " and delete the user-level Agent Feed home"
        if not prompt_confirm(f"{prompt_text}?", False):
            console.print("agent-feed: environment uninstall canceled")
            return
    applied = apply_env_uninstall_plan(actions, shell=shell)
    if applied:
        print_write_plan(applied)
    console.print("[green]agent-feed: environment uninstall complete[/green]")


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
            help=(
                "Initial project code verification profile: python,node,custom,none. "
                "Later changes use agent-feed config set verification_profile <profile>."
            ),
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
        bool,
        typer.Option(
            "-y",
            help=(
                "Use default non-profile choices and apply writes without prompts. "
                "Still requires explicit --profile."
            ),
        ),
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
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

    prompt_for_init = _should_prompt(
        interactive=interactive,
        no_input=no_input or yes,
        explicit=path is not None,
    )
    if prompt_for_init:
        print_welcome()
        wizard_result = prompt_init_wizard(
            target=target,
            project_name=project_name,
            clients=selected_clients,
            verification_profile=selected_verification_profile,
        )
        if wizard_result is None:
            console.print("agent-feed: init canceled")
            return
        target, project_name, selected_clients, selected_verification_profile = wizard_result
    else:
        project_name = project_name or target.name
        resolved_profile = resolve_init_verification_profile(
            verification_profile,
            no_input=no_input or yes,
        )
        if resolved_profile is None:
            console.print("agent-feed: init canceled")
            return
        selected_verification_profile = resolved_profile

    if not ensure_trust_home_for_init(
        target=target,
        interactive=prompt_for_init,
        no_input=no_input,
    ):
        raise typer.Exit(3)

    trust_errors = _trust_preflight_errors(target)
    if trust_errors:
        _print_errors("Init blocked", trust_errors)
        raise typer.Exit(3)

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
        if selected_verification_profile == VerificationProfile.CUSTOM:
            print_recommended_command(
                "Custom verification needs project commands",
                "Edit .agents/project/verification-commands.sh, then run sh .agents/scripts/verify-agent-dev.sh code",
            )
        console.print("Next: agent-feed check")


@app.command("i", hidden=True)
def init_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
    verification_profile: Annotated[str | None, typer.Option("--profile")] = None,
    yes: Annotated[bool, typer.Option("-y")] = False,
) -> None:
    """Shortcut for init."""
    init_cmd(
        path=path,
        clients=clients,
        verification_profile=verification_profile,
        yes=yes,
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
        bool, typer.Option("-i", "--interactive", help="Open a client-selection prompt.")
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
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


@app.command("s", hidden=True)
def sync_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
) -> None:
    """Shortcut for sync."""
    sync_cmd(path=path, clients=clients, no_input=True)


@app.command("sync-skills", hidden=True)
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


@app.command("index-skills")
def index_skills_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview skill indexing without changing files.")
    ] = False,
    accept_changed: Annotated[
        bool,
        typer.Option(
            "-y",
            help=("Accept changed AI asset hashes after you have reviewed preview/status output."),
        ),
    ] = False,
) -> None:
    """Index skills and add default source/trust metadata when missing."""
    target = (path or Path(".")).resolve()
    trust_errors = _trust_preflight_errors(target)
    if not trust_errors and not accept_changed:
        report = check_asset_trust(target)
        trust_errors.extend(
            f"{issue.path}: trusted hash changed. Inspect with agent-feed preview; "
            "if intentional, accept with agent-feed index-skills -y."
            for issue in report.issues
            if issue.reason == "trusted hash mismatch" and issue.allowed_sha256
        )
    if trust_errors:
        _print_errors("Skill indexing blocked", trust_errors)
        raise typer.Exit(3)

    actions, errors = index_skill_metadata(target, dry_run=dry_run)
    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=dry_run,
        accept_changed=accept_changed,
        project_name=infer_project_name(target),
    )
    actions.extend(trust_actions)
    errors.extend(trust_errors)
    if actions:
        print_write_plan(actions)
    if errors:
        _print_errors("Skill indexing blocked", errors)
        raise typer.Exit(3)
    if dry_run:
        console.print("[cyan]agent-feed: skill index preview complete; no files changed[/cyan]")
    else:
        console.print("[green]agent-feed: skills indexed[/green]")


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
        trust_errors = _trust_preflight_errors(target)
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
    console.print("[green]agent-feed: config updated[/green]")


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
    adapter_actions, adapter_errors = sync_clients(
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


@app.command("skill-hub")
def skill_hub_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    keyword: Annotated[
        str | None,
        typer.Option(
            "--keyword",
            "-k",
            help="Keyword matched against skill names, descriptions, and curated hub names.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview skill installation without writing files."),
    ] = False,
    save_token: Annotated[
        bool,
        typer.Option(
            "--save-token/--no-save-token",
            help=f"When a token is entered interactively, save it in ~/.agent-feed/{CONFIG_FILE_NAME}.",
        ),
    ] = True,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; install every matched skill."),
    ] = False,
) -> None:
    """Search curated public skill hubs and install selected skills."""
    target = (path or Path(".")).resolve()
    interactive = can_prompt() and not no_input
    keyword_from_prompt = keyword is None and interactive
    current_keyword = keyword.strip() if keyword else ""
    if not current_keyword and not keyword_from_prompt:
        _print_errors("Skill hub search blocked", ["pass --keyword in non-interactive mode"])
        raise typer.Exit(3)
    token = _preferred_github_token(target)
    selected_keys: list[str] | None = None
    by_key: dict[str, RemoteSkill] = {}

    while True:
        if keyword_from_prompt and not current_keyword:
            keyword_value = prompt_skill_hub_keyword(current_keyword)
            if keyword_value is None:
                console.print("agent-feed: skill hub search canceled")
                return
            current_keyword = keyword_value
            if not current_keyword:
                _print_errors("Skill hub search blocked", ["type a keyword before searching"])
                current_keyword = ""
                continue

        try:
            skills = _search_remote_skills_with_feedback(current_keyword, token=token)
        except RuntimeError as exc:
            retry = _retry_skill_hub_with_token(
                keyword=current_keyword,
                error=str(exc),
                no_input=no_input,
                save_token=save_token,
                target=target,
            )
            if retry is None:
                _print_errors("Skill hub search blocked", [_skill_hub_failure_help(str(exc))])
                raise typer.Exit(3) from exc
            skills, token = retry
        if not skills:
            console.print("[yellow]agent-feed: no curated skills matched that keyword[/yellow]")
            console.print("Hubs searched:")
            for hub in CURATED_HUBS:
                console.print(f"- [bold]{hub.name}[/bold]: {hub.url}")
            if keyword_from_prompt:
                current_keyword = ""
                console.print("[dim]Try another keyword, or press Esc to cancel.[/dim]")
                continue
            return

        by_key = {f"{skill.hub.key}:{skill.name}": skill for skill in skills}
        if interactive:
            choices = [
                {
                    "name": f"{skill.name}  [dim]{skill.hub.name}[/dim]  {skill.description}",
                    "value": key,
                }
                for key, skill in by_key.items()
            ]

            def preview_current(selection: dict[str, object]) -> None:
                value = str(selection.get("value", ""))
                skill = by_key.get(value)
                if skill is None:
                    return
                try:
                    package = _fetch_remote_skill_with_feedback(
                        skill,
                        token=token,
                        message=f"Loading preview for {skill.name}...",
                    )
                except RuntimeError as exc:
                    _print_errors("Skill preview blocked", [_skill_hub_failure_help(str(exc))])
                    return
                print_skill_preview(package)

            result = prompt_skill_hub_selection(choices, on_preview=preview_current)
            if result is None:
                if keyword_from_prompt:
                    current_keyword = ""
                    console.print("[dim]Returned to keyword search.[/dim]")
                    continue
                console.print("agent-feed: skill hub install canceled")
                return
            selected_keys = result
        else:
            selected_keys = list(by_key)
        break

    if not selected_keys:
        _print_errors("Skill hub install blocked", ["select at least one skill"])
        raise typer.Exit(3)

    actions: list[WriteAction] = []
    errors: list[str] = []
    for key in selected_keys:
        skill = by_key[key]
        try:
            package = _fetch_remote_skill_with_feedback(
                skill,
                token=token,
                message=f"Downloading {skill.name}...",
            )
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        package_actions, package_errors = install_remote_skill_package(
            target,
            package,
            dry_run=dry_run,
        )
        actions.extend(package_actions)
        errors.extend(package_errors)

    if actions:
        print_write_plan(actions)
    if errors:
        _print_errors("Skill hub install blocked", errors)
        raise typer.Exit(3)
    if dry_run:
        print_recommended_command(
            "Preview complete",
            f"agent-feed skill-hub {target} --keyword {current_keyword!r}",
        )
        return

    index_actions, index_errors = index_skill_metadata(target, dry_run=False)
    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=False,
        accept_changed=True,
        project_name=infer_project_name(target),
    )
    if index_actions or trust_actions:
        print_write_plan([*index_actions, *trust_actions])
    if index_errors or trust_errors:
        _print_errors("Skill indexing blocked", [*index_errors, *trust_errors])
        raise typer.Exit(3)
    console.print("[green]agent-feed: selected skills installed[/green]")


@app.command("upgrade")
def upgrade_cmd(
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
            help=(
                "Comma-separated clients: codex,claude,cursor,all,none. "
                "Defaults to currently configured adapters."
            ),
        ),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("-i", "--interactive", help="Open prompts for path and clients."),
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "-y",
            help="Use detected/default upgrade choices and apply writes without prompts.",
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview upgrade diff without changing files.")
    ] = False,
    show_diff: Annotated[
        bool,
        typer.Option("--diff", help="Print full red/green unified diffs after the Changes table."),
    ] = False,
) -> None:
    """Upgrade installed Agent Feed assets without deleting local files."""
    target = (path or Path(".")).resolve()
    clients_explicit = clients is not None
    selected_clients = (
        _parse_clients(clients, default=DEFAULT_CLIENTS)
        if clients_explicit
        else installed_clients(target)
    )

    if _should_prompt(
        interactive=interactive,
        no_input=no_input or yes,
        explicit=path is not None,
    ):
        print_welcome()
        wizard_result = prompt_upgrade_wizard(
            target=target,
            project_name=project_name,
            clients=selected_clients,
            clients_explicit=clients_explicit,
        )
        if wizard_result is None:
            console.print("agent-feed: upgrade canceled")
            return
        target, project_name, selected_clients = wizard_result
    else:
        project_name = project_name or infer_project_name(target)
    selected_verification_profile = infer_verification_profile(target)

    if not ensure_trust_home_for_upgrade(
        target=target,
        interactive=not no_input and not yes and can_prompt(),
        no_input=no_input or yes,
    ):
        raise typer.Exit(3)

    trust_errors = _trust_preflight_errors(target)
    if trust_errors:
        _print_errors("Upgrade blocked", trust_errors)
        raise typer.Exit(3)

    actions, errors = upgrade_project(
        target=target,
        project_name=project_name,
        clients=selected_clients,
        verification_profile=selected_verification_profile,
        dry_run=dry_run,
    )
    if dry_run:
        actions.extend(trust_preview_actions(target))
    if actions:
        print_upgrade_plan(
            actions, target=target, command="agent-feed upgrade", show_diff=show_diff
        )
    if errors:
        _print_errors("Upgrade blocked", errors)
        raise typer.Exit(3)

    if dry_run:
        console.print("[cyan]agent-feed: upgrade preview complete; no files changed[/cyan]")
    else:
        console.print("[green]agent-feed: upgrade complete[/green]")


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
    all_checks: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Run every protocol and client check without opening the checkbox prompt.",
        ),
    ] = False,
    interactive: Annotated[
        bool,
        typer.Option("-i", "--interactive", help="Open a checkbox prompt for check categories."),
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
        and (interactive or (checks is None and can_prompt() and not no_input))
        and not no_input
    ):
        selected_checks = prompt_checks(selected_checks)
        if not selected_checks:
            _print_errors("Check blocked", ["select at least one check or pass -a"])
            raise typer.Exit(3)

    report = run_checks(target, selected_checks)
    print_check_report(report, as_json=json_output)
    if not report.ok:
        raise typer.Exit(1)


@app.command("c", hidden=True)
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


@app.command("uninstall")
def uninstall_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview removals without deleting files.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("-y", help="Apply the uninstall plan without asking for confirmation.")
    ] = False,
    no_input: Annotated[
        bool,
        typer.Option("--no-input", help="Never prompt; fail instead of asking for input."),
    ] = False,
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
        console.print("Next: rerun with -y to apply the uninstall plan listed above.")
        return

    if not yes:
        if no_input or not can_prompt():
            console.print("[red]Uninstall blocked[/red]")
            console.print("- pass -y to apply the uninstall plan listed above")
            console.print("- pass --dry-run to preview removals without deleting files")
            raise typer.Exit(3)
        if not prompt_confirm("Apply the Agent Feed uninstall plan listed above?", False):
            console.print("agent-feed: uninstall canceled")
            return

    applied = apply_uninstall_plan(target, actions)
    if applied:
        print_write_plan(applied)
    console.print("[green]agent-feed: uninstall complete[/green]")


@app.command("preview")
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
    actions, errors = preview_actions(
        target=target,
        project_name=project_name,
        clients=selected_clients,
        verification_profile=verification_profile,
    )
    if actions:
        print_write_plan(actions, show_diffs=True)
    if errors:
        _print_errors("Preview blocked", errors)
        raise typer.Exit(3)


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
    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=dry_run,
        accept_changed=True,
        project_name=project_name,
    )
    return [*actions, *adapter_actions, *trust_actions], [*adapter_errors, *trust_errors]


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
    verification_profile: str | None,
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
        return actions, errors

    selected_verification_profile = _parse_verification_profile(
        verification_profile, default=DEFAULT_VERIFICATION_PROFILE
    )
    return (
        preview_project(
            target,
            project_name=project_name or target.name,
            clients=clients if clients is not None else DEFAULT_CLIENTS,
            verification_profile=selected_verification_profile,
        ),
        [],
    )


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


def find_init_conflicts(target: Path, clients: tuple[Client, ...]) -> list[str]:
    errors: list[str] = []
    if (target / "AGENTS.md").exists():
        errors.append("AGENTS.md already exists")
    if has_existing_content(target / ".agents"):
        errors.append(".agents already exists and is not empty")
    if Client.CLAUDE in clients:
        claude_file = target / "CLAUDE.md"
        if claude_file.exists():
            if not claude_file.is_file():
                errors.append("CLAUDE.md exists but is not a file")
            else:
                missing = claude.missing_required_snippets(claude_file, root=target)
                if missing:
                    errors.append(
                        "CLAUDE.md already exists but is missing required Agent Feed "
                        f"references: {', '.join(missing)}"
                    )
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


def resolve_init_verification_profile(
    raw: str | None,
    *,
    no_input: bool,
) -> VerificationProfile | None:
    if raw is not None and raw.strip():
        return _parse_verification_profile(raw, default=DEFAULT_VERIFICATION_PROFILE)
    if no_input or not can_prompt():
        allowed = ", ".join(profile.value for profile in VerificationProfile)
        _print_errors(
            "Init blocked",
            [
                "choose a project verification profile explicitly before init writes files",
                f"run: agent-feed init --profile <{allowed}>",
            ],
        )
        raise typer.Exit(3)
    return prompt_verification_profile_step(DEFAULT_VERIFICATION_PROFILE)


def _with_client_checks(
    checks: tuple[Check, ...], clients: tuple[Client, ...]
) -> tuple[Check, ...]:
    mapped = {
        Client.CODEX: Check.CODEX,
        Client.CLAUDE: Check.CLAUDE,
        Client.CURSOR: Check.CURSOR,
    }
    return tuple(dict.fromkeys((*checks, *(mapped[client] for client in clients))))


def _should_prompt(*, interactive: bool, no_input: bool, explicit: bool) -> bool:
    if no_input:
        return False
    return interactive or (can_prompt() and not explicit)


def _should_offer_env_replace(
    errors: tuple[str, ...],
    *,
    force: bool,
    dry_run: bool,
) -> bool:
    if force or dry_run or not errors or not can_prompt():
        return False
    replace_errors = [error for error in errors if "pass --force to replace it" in error]
    return bool(replace_errors) and len(replace_errors) == len(errors)


def _print_errors(title: str, errors: list[str]) -> None:
    print_error_panel(title, errors)


def prompt_init_wizard(
    *,
    target: Path,
    project_name: str | None,
    clients: tuple[Client, ...],
    verification_profile: VerificationProfile,
) -> tuple[Path, str, tuple[Client, ...], VerificationProfile] | None:
    step = 0
    current_target = target
    current_project_name = project_name or target.name
    current_clients = clients
    current_profile = verification_profile

    while step < 4:
        if step == 0:
            path_value = prompt_path_step("Project path", current_target)
            if path_value is None:
                return None
            current_target = path_value.resolve()
            if project_name is None:
                current_project_name = current_target.name
            step += 1
        elif step == 1:
            text_value = prompt_text_step("Project display name", current_project_name)
            if text_value is None:
                step -= 1
                _print_step_back("Project path")
                continue
            current_project_name = text_value
            step += 1
        elif step == 2:
            clients_value = prompt_clients_step(current_clients)
            if clients_value is None:
                step -= 1
                _print_step_back("project display name")
                continue
            current_clients = clients_value
            step += 1
        else:
            profile_value = prompt_verification_profile_step(current_profile)
            if profile_value is None:
                step -= 1
                _print_step_back("AI clients")
                continue
            current_profile = profile_value
            step += 1

    return current_target, current_project_name, current_clients, current_profile


def prompt_upgrade_wizard(
    *,
    target: Path,
    project_name: str | None,
    clients: tuple[Client, ...],
    clients_explicit: bool,
) -> tuple[Path, str, tuple[Client, ...]] | None:
    step = 0
    current_target = target
    current_project_name = project_name or infer_project_name(target)
    current_clients = clients

    while step < 3:
        if step == 0:
            path_value = prompt_path_step("Project path", current_target)
            if path_value is None:
                return None
            current_target = path_value.resolve()
            if project_name is None:
                current_project_name = infer_project_name(current_target)
            if not clients_explicit:
                current_clients = installed_clients(current_target)
            step += 1
        elif step == 1:
            text_value = prompt_text_step("Project display name", current_project_name)
            if text_value is None:
                step -= 1
                _print_step_back("Project path")
                continue
            current_project_name = text_value
            step += 1
        elif step == 2:
            clients_value = prompt_clients_step(current_clients)
            if clients_value is None:
                step -= 1
                _print_step_back("project display name")
                continue
            current_clients = clients_value
            step += 1

    return current_target, current_project_name, current_clients


def _print_step_back(label: str) -> None:
    console.print(f"[dim]Returned to {label}.[/dim]")


def _preferred_github_token(target: Path) -> str | None:
    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        return env_token

    token, errors = configured_github_token(target)
    if errors:
        console.print(
            "[yellow]Agent Feed could not read the user-level GitHub token config.[/yellow]"
        )
        for error in errors:
            console.print(f"- {error}")
        console.print("[dim]Continuing with GITHUB_TOKEN or anonymous GitHub API access.[/dim]")
        return None
    return token


def _search_remote_skills_with_feedback(
    keyword: str,
    *,
    token: str | None,
) -> list[RemoteSkill]:
    if can_prompt():
        with console.status(
            f"[cyan]Searching curated skill hubs for {keyword!r}...[/cyan]",
            spinner="dots",
        ):
            return search_remote_skills(keyword, token=token)
    return search_remote_skills(keyword, token=token)


def _fetch_remote_skill_with_feedback(
    skill: RemoteSkill,
    *,
    token: str | None,
    message: str,
) -> RemoteSkillPackage:
    try:
        if can_prompt():
            with console.status(f"[cyan]{message}[/cyan]", spinner="dots"):
                return fetch_remote_skill(skill, token=token)
        return fetch_remote_skill(skill, token=token)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _retry_skill_hub_with_token(
    *,
    keyword: str,
    error: str,
    no_input: bool,
    save_token: bool,
    target: Path,
) -> tuple[list[RemoteSkill], str] | None:
    if no_input or not can_prompt() or not _skill_hub_error_can_use_token(error):
        return None

    console.print("[yellow]GitHub did not allow the anonymous skill-hub request.[/yellow]")
    console.print(_skill_hub_failure_help(error))
    token = prompt_secret("GitHub token")
    if not token:
        return None

    if save_token:
        save_actions, save_errors = save_github_token(token, target)
        if save_actions:
            print_write_plan(save_actions)
        if save_errors:
            _print_errors("GitHub token not saved", save_errors)
            console.print("[dim]Continuing with the token for this command only.[/dim]")

    try:
        return search_remote_skills(keyword, token=token), token
    except RuntimeError as exc:
        _print_errors("Skill hub search blocked", [_skill_hub_failure_help(str(exc))])
        raise typer.Exit(3) from exc


def _skill_hub_error_can_use_token(error: str) -> bool:
    lowered = error.lower()
    return any(text in lowered for text in ["rate limit", "http 401", "http 403", "token"])


def _skill_hub_failure_help(error: str) -> str:
    config_file, config_errors = settings_config_path()
    config_target = str(config_file)
    config_example = (
        "{\n"
        '  "schema_version": 1,\n'
        f'  "agent_feed_version": "{__version__}",\n'
        '  "settings": {\n'
        '    "github_token": "ghp_your_token_here"\n'
        "  },\n"
        '  "projects": {}\n'
        "}"
    )
    config_hint = (
        f"Could not read the token config location cleanly: {'; '.join(config_errors)}"
        if config_errors
        else (
            "Or open the user-level Agent Feed config and set the token under "
            f"`settings.github_token` in `{config_target}`. If the file already exists, "
            'paste the `"github_token"` line inside the existing `"settings"` object. '
            "If the file does not exist yet, you can create it with:"
            f"\n```json\n{config_example}\n```"
        )
    )
    return (
        f"{error}\n"
        "Skill hub uses the GitHub API.\n"
        "Set a GitHub token in your current shell and rerun the command:\n"
        'macOS/Linux: `export GITHUB_TOKEN="ghp_your_token_here"`\n'
        'Windows PowerShell: `$env:GITHUB_TOKEN = "ghp_your_token_here"`\n'
        f"{config_hint}"
    )


def ensure_trust_home_for_init(*, target: Path, interactive: bool, no_input: bool) -> bool:
    config_file, errors = trust_config_path()
    if not errors:
        return True
    missing_env = any(f"{AGENT_FEED_HOME_ENV} is required" in error for error in errors)
    if not missing_env or no_input or not interactive or not can_prompt():
        return True

    recommended = suggested_agent_feed_home(target)
    console.print("[yellow]Agent Feed needs an external user config home.[/yellow]")
    console.print(f"Recommended: {recommended}")
    if not prompt_confirm("Set up AGENT_FEED_HOME now and continue?", True):
        return True

    result = setup_agent_feed_home(
        home=recommended,
        target=target,
        shell=SHELL_AUTO,
        dry_run=False,
    )
    if result.actions:
        print_write_plan(list(result.actions))
    if result.errors:
        _print_errors("Environment setup blocked", list(result.errors))
        return False
    console.print("[green]agent-feed: environment configured[/green]")
    console.print(f"{AGENT_FEED_HOME_ENV}: {result.home}")
    return True


def ensure_trust_home_for_upgrade(*, target: Path, interactive: bool, no_input: bool) -> bool:
    return ensure_trust_home_for_init(target=target, interactive=interactive, no_input=no_input)


def _trust_preflight_errors(root: Path) -> list[str]:
    config_file, errors = trust_config_path()
    if errors:
        return errors
    if config_file is None:
        return []
    local_errors = project_local_config_errors(root, config_file)
    if local_errors:
        return local_errors
    if config_file.exists() or legacy_config_path(config_file).exists():
        return validate_config_shape(config_file)
    return []


def maybe_cleanup_missing_project_entries(*, dry_run: bool) -> tuple[list[WriteAction], list[str]]:
    actions, errors = cleanup_missing_project_entries(dry_run=True)
    if errors or not actions:
        return actions, errors
    if dry_run:
        return actions, []
    stale_detail = actions[0].detail or "remove stale project entries"
    if not can_prompt():
        return [
            WriteAction(
                path=actions[0].path,
                action="review",
                detail=f"{stale_detail}; rerun in an interactive terminal to clean up",
            )
        ], []
    if not prompt_confirm(f"{stale_detail}?", True):
        return [], []
    return cleanup_missing_project_entries(dry_run=False)


def _run_menu_action(action: str) -> int:
    try:
        if action == "exit":
            return 0
        if action == "init":
            init_cmd(interactive=True)
        elif action == "sync":
            sync_cmd(interactive=True)
        elif action == "upgrade":
            upgrade_cmd(interactive=True)
        elif action == "check":
            check_cmd(interactive=True)
        elif action == "status":
            status_cmd()
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


def print_upgrade_plan(
    actions: list[WriteAction],
    *,
    target: Path,
    command: str,
    show_diff: bool,
) -> None:
    print_write_plan(actions, show_diffs=show_diff)
    if show_diff or not has_diff_details(actions):
        return
    interactive = can_prompt()
    print_diff_hint(command=f"{command} {target}", interactive=interactive)
    if interactive and prompt_view_diff_key():
        print_diff_details(actions)


def print_inspection_plan(actions: list[WriteAction], *, target: Path) -> None:
    print_write_plan_with_title(actions, title=f"Agent Feed Inspection: {target}")
    if not has_diff_details(actions):
        return
    interactive = can_prompt()
    print_diff_hint(
        command=f"agent-feed preview {target}",
        interactive=interactive,
        append_diff_flag=False,
    )
    if interactive and prompt_view_diff_key():
        preview_cmd(path=target)


def print_skill_preview(package: RemoteSkillPackage) -> None:
    body = "\n".join(
        [
            f"**Source:** [{package.skill.hub.name}]({package.skill.hub.url})",
            f"**Skill:** [{package.skill.name}]({package.skill.url})",
            "",
            "**Files to add:**",
            "",
            "```txt",
            preview_skill_tree(package),
            "```",
            "",
            "Imported skills are installed as `trust: custom`. Agent Feed does not execute remote scripts during install.",
        ]
    )
    print_markdown_panel("Skill Preview", body, border_style="yellow")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
