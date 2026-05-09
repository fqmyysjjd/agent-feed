"""``agent-feed skills`` command group.

Patched names (``can_prompt``, ``prompt_confirm``, ``sync_clients``) are
routed through ``agent_feed.cli`` so ``monkeypatch.setattr(cli, ...)`` keeps
working from tests.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated, List

import typer
from rich import box
from rich.table import Table

from agent_feed import cli as _cli
from agent_feed.asset_trust import sync_asset_trust
from agent_feed.cli._helpers import (
    _is_path_like_argument,
    _print_errors,
    _safe_skill_name,
    build_skill_delete_actions,
)
from agent_feed.console import (
    console,
    print_action_result,
    print_recommended_command,
    print_write_plan,
)
from agent_feed.prompts import prompt_skills_to_remove
from agent_feed.services.clients import installed_clients
from agent_feed.skill_index import SkillMetadata, discover_skills, index_skill_metadata
from agent_feed.upgrade import infer_project_name

skills_app = typer.Typer(
    name="skills",
    help="List or remove installed local skills.",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _prompt_skills_to_remove(skills: list[SkillMetadata]) -> list[str]:
    choices = [
        {
            "name": f"{skill.name}  [{skill.trust}] {skill.source}  {skill.path.parent.as_posix()}",
            "value": skill.path.parent.name,
        }
        for skill in skills
    ]
    return prompt_skills_to_remove(choices)


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
        if not no_input and _cli.can_prompt():
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
        if no_input or not _cli.can_prompt():
            _print_errors("Skill removal blocked", ["pass -y to remove skills without prompts"])
            raise typer.Exit(3)
        label = ", ".join(validated_names)
        if not _cli.prompt_confirm(
            f"Remove {len(validated_names)} skill(s) ({label}) from {target}?", default=False
        ):
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
    adapter_actions, adapter_errors = _cli.sync_clients(
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
