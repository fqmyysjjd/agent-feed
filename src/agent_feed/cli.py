"""Command line entry point for Agent Feed."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, List

import typer
from rich import box
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

import agent_feed
from agent_feed import __version__
from agent_feed.asset_trust import (
    AGENT_FEED_HOME_ENV,
    CONFIG_FILE_NAME,
    check_asset_trust,
    cleanup_missing_project_entries,
    configured_github_token,
    legacy_config_path,
    project_local_config_errors,
    missing_project_entries,
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
from agent_feed.config import check_config, get_config_value, set_config_value
from agent_feed.console import (
    console,
    display_path,
    has_diff_details,
    print_diff_details,
    print_diff_hint,
    print_check_report,
    print_config_check_report,
    print_error_panel,
    print_markdown_panel,
    print_action_result,
    print_recommended_command,
    print_status,
    print_stale_project_cleanup,
    print_update_notice,
    print_welcome,
    print_write_plan,
    print_write_plan_with_title,
)
from agent_feed.install_source import latest_update_notice
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
    prompt_skills_to_remove,
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
from agent_feed.services.clients import installed_clients, sync_clients
from agent_feed.services.lifecycle import (
    downgrade_preflight_errors,
    init_backup_dir,
    init_project,
    preview_actions,
    upgrade_project,
)
from agent_feed.skill_index import SkillMetadata, discover_skills, index_skill_metadata
from agent_feed.uninstall import apply_uninstall_plan, has_deletions, uninstall_plan
from agent_feed.upgrade import (
    infer_project_name,
    infer_verification_profile,
    is_installed,
    settings_asset_plan as build_settings_asset_plan,
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
skills_app = typer.Typer(
    name="skills",
    help="List or remove installed local skills.",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(skills_app, name="skills")


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

def print_version() -> None:
    console.print(f"agent-feed {__version__}")
    console.print(f"executable: {Path(sys.argv[0]).resolve()}")
    if agent_feed.__file__:
        console.print(f"package: {Path(agent_feed.__file__).resolve().parent}")


def maybe_print_update_notice() -> None:
    notice = latest_update_notice()
    if notice is None or not notice.source.update_command:
        return
    print_update_notice(
        current_version=notice.current_version,
        latest_version=notice.latest_version,
        source_label=notice.source.label,
        command=notice.source.update_command,
    )


def _print_trust_config_location() -> None:
    """Surface the AI-asset trust file path so users can find it after init/upgrade."""
    config_file, _errors = trust_config_path()
    if config_file is None:
        return
    console.print(
        f"[dim]Trust state: {display_path(config_file)} (under {AGENT_FEED_HOME_ENV})[/dim]"
    )


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
        if no_input or not can_prompt():
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
        if not prompt_confirm(f"{prompt_text}?", False):
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
    env_home: Annotated[
        Path | None,
        typer.Option(
            "--env-home",
            help=(
                "External Agent Feed home to create when AGENT_FEED_HOME is missing. "
                "Defaults to ~/.agent-feed or %APPDATA%\\agent-feed."
            ),
        ),
    ] = None,
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

    prompt_for_init = (not no_input and not yes and path is None and can_prompt())
    if prompt_for_init:
        print_welcome()
        wizard_result = prompt_init_wizard(
            target=target,
            project_name=project_name,
            clients=selected_clients,
            verification_profile=selected_verification_profile,
        )
        if wizard_result is None:
            print_action_result(
                title="Initialization",
                message="Canceled",
                kind="warning",
            )
            return
        target, project_name, selected_clients, selected_verification_profile = wizard_result
    else:
        project_name = project_name or target.name
        resolved_profile = resolve_init_verification_profile(
            verification_profile,
            no_input=no_input or yes,
        )
        if resolved_profile is None:
            print_action_result(
                title="Initialization",
                message="Canceled",
                kind="warning",
            )
            return
        selected_verification_profile = resolved_profile

    if not ensure_trust_home_for_init(
        target=target,
        home=env_home,
        dry_run=dry_run,
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
        _print_trust_config_location()
        backup_dir = init_backup_dir(actions, target=target)
        if backup_dir is not None:
            console.print(
                f"[cyan]Legacy AI instruction assets were backed up to[/cyan] "
                f"[blue italic]{display_path(backup_dir)}[/blue italic]"
            )
        if selected_verification_profile == VerificationProfile.CUSTOM:
            print_recommended_command(
                "Custom verification needs project commands",
                "sh .agents/scripts/verify-agent-dev.sh code",
                path=".agents/project/verification-commands.sh",
            )
        console.print("Next: agent-feed check")


@app.command("i", hidden=True)
def init_alias(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
    clients: Annotated[str | None, typer.Option("--clients")] = None,
    verification_profile: Annotated[str | None, typer.Option("--profile")] = None,
    env_home: Annotated[Path | None, typer.Option("--env-home")] = None,
    yes: Annotated[bool, typer.Option("-y")] = False,
) -> None:
    """Shortcut for init."""
    init_cmd(
        path=path,
        clients=clients,
        verification_profile=verification_profile,
        env_home=env_home,
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
    all_clients: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Sync every supported client adapter without opening the client prompt.",
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
    """Sync selected client adapters from canonical Agent Feed assets."""
    if all_clients and clients is not None:
        raise typer.BadParameter("use either -a/--all or --clients, not both")
    target = (path or Path(".")).resolve()
    selected_clients = tuple(Client) if all_clients else _parse_clients(clients, default=DEFAULT_CLIENTS)
    if not all_clients and clients is None and can_prompt() and not no_input:
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


@skills_app.command("list")
def skills_list_cmd(
    path: Annotated[
        Path | None, typer.Argument(help="Target project path. Defaults to cwd.")
    ] = None,
) -> None:
    """List installed local skills."""
    target = (path or Path(".")).resolve()
    skill_root = target / ".agents/skills"
    if not skill_root.exists():
        _print_errors("Skill listing blocked", ["missing .agents/skills; run agent-feed init first"])
        raise typer.Exit(3)

    skills = discover_skills(target)
    if not skills:
        print_action_result(
            title="Skills",
            message="No installed skills found",
            kind="warning",
            detail=f"Checked {skill_root}",
        )
        return

    table = Table(
        title=f"Installed Skills: {target}",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
    )
    table.add_column("Skill", style="bold")
    table.add_column("Source")
    table.add_column("Trust")
    table.add_column("Path", overflow="fold")
    for skill in skills:
        table.add_row(skill.name, skill.source, skill.trust, skill.path.as_posix())
    console.print(table)


@skills_app.command("remove")
def skills_remove_cmd(
    names: Annotated[
        List[str],
        typer.Argument(
            help=(
                "Installed skill directory names to remove. Omit for interactive selection. "
                "Skill names only; the current working directory is the target project."
            )
        ),
    ] = [],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview skill removal without deleting files.")
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("-y", help="Remove the skills and refresh derived assets without asking."),
    ] = False,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Never prompt; require -y for removal.")
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Allow removal of bundled core skills after review."),
    ] = False,
) -> None:
    """Remove one or more installed local skills from the current working directory."""
    selected_names = list(names)
    path_like = [name for name in selected_names if _is_path_like_argument(name)]
    if path_like:
        _print_errors(
            "Skill removal blocked",
            [
                f"path-like argument is not allowed: {name}" for name in path_like
            ]
            + ["skills remove only accepts skill directory names; cd into the project first."],
        )
        raise typer.Exit(3)
    target = Path(".").resolve()
    skill_root = target / ".agents/skills"
    if not skill_root.exists():
        _print_errors("Skill removal blocked", ["missing .agents/skills; run agent-feed init first"])
        raise typer.Exit(3)

    all_skills = discover_skills(target)
    if not all_skills:
        print_action_result(
            title="Skills",
            message="No installed skills found",
            kind="warning",
            detail=f"Checked {skill_root}",
        )
        return

    if not selected_names:
        if not no_input and can_prompt():
            selected_names = _prompt_skills_to_remove(all_skills)
            if not selected_names:
                print_action_result(
                    title="Skills",
                    message="Canceled",
                    kind="warning",
                    detail="No skills were selected for removal.",
                )
                return
        else:
            _print_errors("Skill removal blocked", ["pass skill names or use an interactive terminal"])
            raise typer.Exit(3)

    errors: list[str] = []
    validated_names: list[str] = []
    for name in selected_names:
        if not _safe_skill_name(name):
            errors.append(f"unsafe skill name: {name}")
            continue
        skill_dir = skill_root / name
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.exists() or not skill_dir.is_dir():
            errors.append(f"installed skill not found: {name}")
            continue
        if not skill_file.exists():
            errors.append(f"{skill_dir} does not contain SKILL.md")
            continue
        skill_metadata = next(
            (skill for skill in all_skills if skill.path.parent.name == name),
            None,
        )
        if (
            skill_metadata
            and not force
            and (skill_metadata.source == "agent-feed" or skill_metadata.trust == "core")
        ):
            errors.append(
                f"{name} is a bundled core skill. Review the impact first, then rerun with --force if intentional."
            )
            continue
        validated_names.append(name)

    if errors:
        _print_errors("Skill removal blocked", errors)
        raise typer.Exit(3)

    if not validated_names:
        _print_errors("Skill removal blocked", ["no valid skills to remove"])
        raise typer.Exit(3)

    if dry_run:
        delete_actions = build_skill_delete_actions(
            skill_root=skill_root,
            names=validated_names,
            action="would delete",
        )
        print_write_plan(delete_actions)
        names_arg = " ".join(validated_names)
        print_recommended_command("Preview complete", f"agent-feed skills remove {names_arg} -y")
        return
    if not yes:
        if no_input or not can_prompt():
            _print_errors("Skill removal blocked", ["pass -y to remove skills without prompts"])
            raise typer.Exit(3)
        label = ", ".join(validated_names)
        if not prompt_confirm(f"Remove {len(validated_names)} skill(s) ({label}) from {target}?", default=False):
            print_action_result(
                title="Skills",
                message="Canceled",
                kind="warning",
                detail="No skills were removed.",
            )
            return

    removed_names: list[str] = []
    delete_errors: list[str] = []
    for name in validated_names:
        try:
            shutil.rmtree(skill_root / name)
        except OSError as exc:
            delete_errors.append(f"{name}: {exc}")
        else:
            removed_names.append(name)
    index_actions, index_errors = index_skill_metadata(target, dry_run=False)
    adapter_actions, adapter_errors = sync_clients(
        target,
        clients=installed_clients(target),
        dry_run=False,
        force_generated=False,
    )
    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=False,
        accept_changed=True,
        project_name=infer_project_name(target),
    )
    actions = [
        *build_skill_delete_actions(skill_root=skill_root, names=removed_names, action="delete"),
        *index_actions,
        *adapter_actions,
        *trust_actions,
    ]
    refresh_errors = [
        *delete_errors,
        *index_errors,
        *adapter_errors,
        *trust_errors,
    ]
    if actions:
        print_write_plan(actions)
    if refresh_errors:
        _print_errors("Skill removal blocked", refresh_errors)
        raise typer.Exit(3)
    count = len(validated_names)
    print_action_result(
        title="Skills",
        message=f"{count} skill(s) removed",
        kind="success",
        detail="The skill index, client adapters, and trust state were refreshed.",
    )


def build_skill_delete_actions(
    *,
    skill_root: Path,
    names: list[str],
    action: str,
) -> list[WriteAction]:
    return [
        WriteAction(
            path=skill_root / name,
            action=action,
            detail="installed skill",
        )
        for name in names
    ]


def _is_path_like_argument(name: str) -> bool:
    """Return True for tokens that look like a filesystem path rather than a skill name."""
    if not name:
        return False
    if "/" in name or "\\" in name:
        return True
    if name in {".", ".."}:
        return True
    if name.startswith(".") or name.startswith("~"):
        return True
    return False


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
    config_report = check_config(target)
    print_config_check_report(config_report, as_json=False)
    if not config_report.ok:
        raise typer.Exit(3)
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
                print_action_result(
                    title="Skill Hub",
                    message="Canceled",
                    kind="warning",
                    detail="No skill search was started.",
                )
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
            print_action_result(
                title="Skill Hub",
                message="No curated skills matched that keyword",
                kind="warning",
                detail="Try another keyword or check the curated hubs below.",
            )
            console.print("Hubs searched:")
            for hub in CURATED_HUBS:
                console.print(f"- [bold]{hub.name}[/bold]: {hub.url}")
            if keyword_from_prompt:
                current_keyword = ""
                console.print("[dim]Try another keyword, or press Esc to cancel.[/dim]")
                continue
            return

        selection = _select_remote_skills(
            skills,
            token=token,
            interactive=interactive,
            no_input=no_input,
            save_token=save_token,
            target=target,
        )
        if selection is None:
            if keyword_from_prompt:
                current_keyword = ""
                console.print("[dim]Returned to keyword search.[/dim]")
                continue
            print_action_result(
                title="Skill Hub",
                message="Canceled",
                kind="warning",
                detail="No skills were installed.",
            )
            return
        selected_keys, by_key, token = selection
        break

    if not selected_keys:
        _print_errors("Skill hub install blocked", ["select at least one skill"])
        raise typer.Exit(3)

    selected_skills = [by_key[key] for key in selected_keys]
    packages = _download_selected_skill_packages(selected_skills, token=token)
    token_retry_error = _first_skill_hub_token_retry_error(packages)
    if token_retry_error is not None:
        retry_token = _prompt_skill_hub_token(
            error=token_retry_error,
            no_input=no_input,
            save_token=save_token,
            target=target,
            retry_action="download",
        )
        if retry_token is None:
            _print_errors("Skill hub install blocked", [_skill_hub_failure_help(token_retry_error)])
            raise typer.Exit(3)
        token = retry_token
        packages = _download_selected_skill_packages(selected_skills, token=token)

    actions: list[WriteAction] = []
    errors: list[str] = []
    installed_labels: list[str] = []
    for skill, package, fetch_error in packages:
        if fetch_error:
            errors.append(_skill_hub_error_label(skill, fetch_error))
            continue
        if package is None:
            errors.append(_skill_hub_error_label(skill, "skill package was not loaded"))
            continue
        try:
            package_actions, package_errors = install_remote_skill_package(
                target,
                package,
                dry_run=dry_run,
            )
        except Exception as exc:
            errors.append(_skill_hub_error_label(skill, str(exc)))
            continue
        if package_errors:
            errors.extend(_skill_hub_error_label(skill, error) for error in package_errors)
            continue
        actions.extend(package_actions)
        installed_labels.append(f"{skill.name} ({skill.hub.name})")

    if actions:
        print_write_plan(actions)
    if installed_labels:
        print_action_result(
            title="Skill Hub",
            message="Skills ready" if dry_run else "Skills installed",
            kind="success",
            detail=", ".join(installed_labels),
        )
    if dry_run:
        if errors:
            _print_errors("Skill hub install blocked", errors)
            raise typer.Exit(3)
        print_recommended_command(
            "Preview complete",
            f"agent-feed skill-hub {target} --keyword {current_keyword!r}",
        )
        return

    if installed_labels:
        if not _confirm_skill_registration(target=target, interactive=interactive):
            print_action_result(
                title="Skill Hub",
                message="Skills installed but not registered",
                kind="warning",
                detail="Run agent-feed index-skills -y when ready.",
            )
            if errors:
                _print_errors("Skill hub install blocked", errors)
                raise typer.Exit(3)
            return

        registration_actions, registration_errors = _register_installed_skills(target)
        if registration_actions:
            print_write_plan(registration_actions)
        if registration_errors:
            _print_errors("Skill indexing blocked", registration_errors)
            raise typer.Exit(3)
    if errors:
        _print_errors("Skill hub install blocked", errors)
        raise typer.Exit(3)
    print_action_result(
        title="Skill Hub",
        message="Selected skills installed",
        kind="success",
        detail="The skill index, client adapters, and trust state were refreshed.",
    )


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
    allow_downgrade: Annotated[
        bool,
        typer.Option(
            "--allow-downgrade",
            help="Allow an older Agent Feed CLI to write older managed assets. Interactive terminals can also confirm inline.",
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview upgrade diff without changing files.")
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

    if not no_input and not yes and path is None and can_prompt():
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

    if not dry_run and not allow_downgrade:
        downgrade_errors = downgrade_preflight_errors(
            target=target,
            interactive=not no_input and not yes and can_prompt(),
        )
        if downgrade_errors:
            _print_errors("Upgrade blocked", downgrade_errors)
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
            actions,
            target=target,
            command="agent-feed preview",
        )
    if errors:
        _print_errors("Upgrade blocked", errors)
        raise typer.Exit(3)

    if dry_run:
        console.print("[cyan]agent-feed: upgrade preview complete; no files changed[/cyan]")
    else:
        console.print("[green]agent-feed: upgrade complete[/green]")
        _print_trust_config_location()
    maybe_print_update_notice()


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
        and can_prompt()
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


def _prompt_skills_to_remove(skills: list[SkillMetadata]) -> list[str]:
    choices = [
        {
            "name": f"{skill.name}  [{skill.trust}] {skill.source}  {skill.path.parent.as_posix()}",
            "value": skill.path.parent.name,
        }
        for skill in skills
    ]
    return prompt_skills_to_remove(choices)


def _safe_skill_name(name: str) -> bool:
    if not name or name in {".", ".."} or name.startswith("."):
        return False
    return all(character.isalnum() or character in {"-", "_", "."} for character in name)


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
        console.print("[dim]Trying GitHub CLI token fallback.[/dim]")
    elif token:
        return token

    gh_token = _github_cli_token()
    if gh_token:
        console.print("[dim]Using GitHub token from gh auth token.[/dim]")
        return gh_token
    if errors:
        console.print("[dim]GitHub CLI token fallback was unavailable; using anonymous GitHub API access.[/dim]")
    return None


def _github_cli_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    token = result.stdout.strip()
    if result.returncode != 0 or not token:
        return None
    return token


def _search_remote_skills_with_feedback(
    keyword: str,
    *,
    token: str | None,
    message: str | None = None,
) -> list[RemoteSkill]:
    if can_prompt():
        with console.status(
            f"[cyan]{message or f'Searching curated skill hubs for {keyword!r}...'}[/cyan]",
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


def _download_selected_skill_packages(
    skills: list[RemoteSkill],
    *,
    token: str | None,
) -> list[tuple[RemoteSkill, RemoteSkillPackage | None, str | None]]:
    results: list[tuple[RemoteSkill, RemoteSkillPackage | None, str | None]] = []
    if can_prompt():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[dim]{task.fields[skill]}[/dim]"),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                "Downloading skills",
                total=len(skills),
                skill="",
            )
            for index, skill in enumerate(skills, start=1):
                progress.update(task_id, skill=f"{index}/{len(skills)} {skill.name}")
                try:
                    results.append((skill, fetch_remote_skill(skill, token=token), None))
                except Exception as exc:
                    results.append((skill, None, str(exc)))
                progress.advance(task_id)
        return results

    for index, skill in enumerate(skills, start=1):
        try:
            package = _fetch_remote_skill_with_feedback(
                skill,
                token=token,
                message=f"Downloading skill {index}/{len(skills)}: {skill.name}...",
            )
            results.append((skill, package, None))
        except RuntimeError as exc:
            results.append((skill, None, str(exc)))
    return results


def _select_remote_skills(
    skills: list[RemoteSkill],
    *,
    token: str | None,
    interactive: bool,
    no_input: bool,
    save_token: bool,
    target: Path,
) -> tuple[list[str], dict[str, RemoteSkill], str | None] | None:
    by_key = {f"{skill.hub.key}:{skill.name}": skill for skill in skills}
    if not interactive:
        return list(by_key), by_key, token

    choices = [
        {
            "name": f"{skill.name}  [dim]{skill.hub.name}[/dim]  {skill.description}",
            "value": key,
        }
        for key, skill in by_key.items()
    ]

    def preview_current(selection: dict[str, object]) -> None:
        nonlocal token
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
            retry_token = _prompt_skill_hub_token(
                error=str(exc),
                no_input=no_input,
                save_token=save_token,
                target=target,
                retry_action="preview",
            )
            if retry_token is None:
                _print_errors("Skill preview blocked", [_skill_hub_failure_help(str(exc))])
                return
            token = retry_token
            try:
                package = _fetch_remote_skill_with_feedback(
                    skill,
                    token=token,
                    message=f"Loading preview for {skill.name} with token...",
                )
            except RuntimeError as retry_exc:
                _print_errors("Skill preview blocked", [_skill_hub_failure_help(str(retry_exc))])
                return
            print_skill_preview(package)
            return
        print_skill_preview(package)

    selected_keys = prompt_skill_hub_selection(choices, on_preview=preview_current)
    if selected_keys is None:
        return None
    return selected_keys, by_key, token


def _first_skill_hub_token_retry_error(
    packages: list[tuple[RemoteSkill, RemoteSkillPackage | None, str | None]],
) -> str | None:
    for _skill, _package, fetch_error in packages:
        if fetch_error and _skill_hub_error_can_use_token(fetch_error):
            return fetch_error
    return None


def _register_installed_skills(target: Path) -> tuple[list[WriteAction], list[str]]:
    index_actions, index_errors = index_skill_metadata(target, dry_run=False)
    adapter_actions, adapter_errors = sync_clients(
        target,
        clients=installed_clients(target),
        dry_run=False,
        force_generated=False,
    )
    trust_actions, trust_errors = sync_asset_trust(
        target,
        dry_run=False,
        accept_changed=True,
        project_name=infer_project_name(target),
    )
    return [*index_actions, *adapter_actions, *trust_actions], [
        *index_errors,
        *adapter_errors,
        *trust_errors,
    ]


def _confirm_skill_registration(*, target: Path, interactive: bool) -> bool:
    if not interactive:
        return True
    return prompt_confirm(
        f"Register installed skills in Agent Feed now for {target}?",
        default=True,
    )


def _skill_hub_error_label(skill: RemoteSkill, error: str) -> str:
    return f"{skill.name} ({skill.hub.name}): {error}"


def _retry_skill_hub_with_token(
    *,
    keyword: str,
    error: str,
    no_input: bool,
    save_token: bool,
    target: Path,
) -> tuple[list[RemoteSkill], str] | None:
    token = _prompt_skill_hub_token(
        error=error,
        no_input=no_input,
        save_token=save_token,
        target=target,
        retry_action="search",
    )
    if token is None:
        return None

    try:
        return (
            _search_remote_skills_with_feedback(
                keyword,
                token=token,
                message=f"Searching curated skill hubs for {keyword!r} with token...",
            ),
            token,
        )
    except RuntimeError as exc:
        _print_errors("Skill hub search blocked", [_skill_hub_failure_help(str(exc))])
        raise typer.Exit(3) from exc


def _prompt_skill_hub_token(
    *,
    error: str,
    no_input: bool,
    save_token: bool,
    target: Path,
    retry_action: str,
) -> str | None:
    if no_input or not can_prompt() or not _skill_hub_error_can_use_token(error):
        return None

    console.print("[yellow]GitHub did not allow the anonymous skill-hub request.[/yellow]")
    console.print(_skill_hub_failure_help(error))
    token_prompt = (
        f"GitHub token (saved to settings.github_token, then retries {retry_action})"
        if save_token
        else f"GitHub token (used once, then retries {retry_action})"
    )
    token = prompt_secret(token_prompt)
    if not token:
        return None

    if save_token:
        save_actions, save_errors = save_github_token(token, target)
        if save_actions:
            print_write_plan(save_actions)
        if save_errors:
            _print_errors("GitHub token not saved", save_errors)
            console.print("[dim]Continuing with the token for this command only.[/dim]")

    return token


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
        "If you already use GitHub CLI, run `gh auth login`; Agent Feed will automatically reuse `gh auth token`.\n"
        "Set a GitHub token in your current shell and rerun the command:\n"
        'macOS/Linux: `export GITHUB_TOKEN="ghp_your_token_here"`\n'
        'Windows PowerShell: `$env:GITHUB_TOKEN = "ghp_your_token_here"`\n'
        f"{config_hint}"
    )


def ensure_trust_home_for_init(
    *,
    target: Path,
    home: Path | None = None,
    dry_run: bool = False,
    no_input: bool,
) -> bool:
    config_file, errors = trust_config_path()
    if not errors:
        return True
    missing_env = any(f"{AGENT_FEED_HOME_ENV} is required" in error for error in errors)
    if not missing_env:
        return True

    recommended = home or suggested_agent_feed_home(target)
    detail = (
        f"Will use {recommended}. "
        f"To choose another path, rerun init with --env-home PATH or run agent-feed env setup --home PATH."
    )
    print_action_result(
        title="Environment Setup",
        message="Preparing external Agent Feed home",
        kind="info",
        detail=detail,
    )

    if (no_input or (not can_prompt() and not dry_run)) and home is None:
        _print_errors(
            "Environment setup blocked",
            [
                f"{AGENT_FEED_HOME_ENV} is required before init can record AI asset trust.",
                f"Run: agent-feed env setup {target}",
                "Or rerun init with --env-home PATH.",
            ],
        )
        return False

    result = setup_agent_feed_home(
        home=recommended,
        target=target,
        shell=SHELL_AUTO,
        dry_run=dry_run,
    )
    if _should_offer_env_replace(result.errors, force=False, dry_run=dry_run):
        current_home = current_agent_feed_home()
        if no_input:
            _print_errors(
                "Environment setup blocked",
                [
                    f"{AGENT_FEED_HOME_ENV} is already set to {current_home}.",
                    f"Run: agent-feed env setup {target} --home {recommended} --force",
                ],
            )
            return False
        if prompt_confirm(
            f"Replace existing {AGENT_FEED_HOME_ENV} ({current_home}) with {recommended}?",
            False,
        ):
            result = setup_agent_feed_home(
                home=recommended,
                target=target,
                shell=SHELL_AUTO,
                dry_run=dry_run,
                force=True,
            )
    if result.actions:
        print_write_plan(list(result.actions))
    if dry_run:
        os.environ[AGENT_FEED_HOME_ENV] = str(result.home)
        return True
    if result.errors:
        remediation_home = f" --home {recommended}" if home is not None else ""
        _print_errors(
            "Environment setup blocked",
            [
                *list(result.errors),
                f"Run: agent-feed env setup {target}{remediation_home}",
                "If shell detection failed, add --shell zsh, bash, fish, or powershell.",
            ],
        )
        return False
    print_action_result(
        title="Environment Setup",
        message="Environment configured",
        kind="success",
        detail="The user-level Agent Feed home and shell binding are ready for this session.",
    )
    console.print(f"{AGENT_FEED_HOME_ENV}: {result.home}")
    return True


def ensure_trust_home_for_upgrade(*, target: Path, interactive: bool, no_input: bool) -> bool:
    config_file, errors = trust_config_path()
    if not errors:
        return True
    missing_env = any(f"{AGENT_FEED_HOME_ENV} is required" in error for error in errors)
    if not missing_env or no_input or not interactive or not can_prompt():
        return True

    recommended = suggested_agent_feed_home(target)
    print_action_result(
        title="Environment Setup Required",
        message="Agent Feed needs an external user config home",
        kind="warning",
        detail=f"Recommended: {recommended}",
    )
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
    print_action_result(
        title="Environment Setup",
        message="Environment configured",
        kind="success",
        detail="The user-level Agent Feed home and shell binding are ready.",
    )
    console.print(f"{AGENT_FEED_HOME_ENV}: {result.home}")
    return True


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
    if not can_prompt():
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
    if not prompt_confirm("Remove these stale project records from the user-level config?", True):
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
        if no_input or not can_prompt():
            return [], [
                "stale project entries found; rerun `agent-feed config prune -y` "
                "to remove them without prompting"
            ]
        if not prompt_confirm("Remove these stale project records from the user-level config?", True):
            return [], []
    return cleanup_missing_project_entries(dry_run=False)


def _run_menu_action(action: str) -> int:
    try:
        if action == "exit":
            return 0
        if action == "init":
            init_cmd()
        elif action == "sync":
            sync_cmd()
        elif action == "upgrade":
            upgrade_cmd()
        elif action == "check":
            check_cmd()
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
) -> None:
    print_write_plan(actions)
    if not has_diff_details(actions):
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
    )
    if interactive and prompt_view_diff_key():
        preview_cmd(path=target)


def print_skill_preview(package: RemoteSkillPackage) -> None:
    body = "\n".join(
        [
            f"**Source:** {package.skill.hub.name}  {package.skill.hub.url}",
            f"**Skill:** {package.skill.name}  {package.skill.url}",
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
    app(prog_name="agent-feed")


if __name__ == "__main__":
    main()
