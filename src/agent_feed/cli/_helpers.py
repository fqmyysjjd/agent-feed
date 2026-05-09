"""Pure helpers used across CLI command implementations.

These functions are independent of the test patch surface (they do not call
``can_prompt``/``prompt_*``/``sync_clients``/``search_remote_skills``/etc.),
so they can live outside ``cli/__init__.py`` without breaking any
``monkeypatch.setattr(cli, ...)`` seam.
"""

from __future__ import annotations

from pathlib import Path

import typer

from agent_feed.choices import parse_choice_csv
from agent_feed.console import print_error_panel
from agent_feed.models import Check, Client, VerificationProfile, WriteAction


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


def _with_client_checks(
    checks: tuple[Check, ...], clients: tuple[Client, ...]
) -> tuple[Check, ...]:
    mapped = {
        Client.CODEX: Check.CODEX,
        Client.CLAUDE: Check.CLAUDE,
        Client.CURSOR: Check.CURSOR,
    }
    return tuple(dict.fromkeys((*checks, *(mapped[client] for client in clients))))


def _print_errors(title: str, errors: list[str]) -> None:
    print_error_panel(title, errors)


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
