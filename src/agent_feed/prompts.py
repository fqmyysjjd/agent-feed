"""Interactive prompts for Agent Feed."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from InquirerPy import inquirer as _inquirer

from agent_feed.models import (
    CHECKS,
    VERIFICATION_PROFILES,
    Check,
    Client,
    VerificationProfile,
)
from agent_feed.verification_profiles import PROFILE_LABELS


inquirer: Any = _inquirer

SELECT_INSTRUCTION = "Use ↑/↓ to move, Enter to execute"
CHECKBOX_INSTRUCTION = "Use ↑/↓ to move, Space to select, Enter to execute"
TEXT_INSTRUCTION = "Press Enter to confirm"
CONFIRM_INSTRUCTION = "Use y/n, Enter to confirm"


def can_prompt() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_main_action() -> str:
    return str(
        inquirer.select(
            message="What do you want to do?",
            instruction=SELECT_INSTRUCTION,
            choices=[
                {"name": "Initialize protocol", "value": "init"},
                {"name": "Update installed protocol", "value": "update"},
                {"name": "Sync client adapters", "value": "sync"},
                {"name": "Check protocol health", "value": "check"},
                {"name": "Show status", "value": "status"},
                {"name": "Run doctor", "value": "doctor"},
                {"name": "Preview writes", "value": "preview"},
                {"name": "Uninstall protocol", "value": "uninstall"},
                {"name": "Exit", "value": "exit"},
            ],
            default="status",
        ).execute()
    )


def prompt_path(message: str, default: Path) -> Path:
    value = inquirer.text(
        message=message,
        default=str(default),
        instruction=TEXT_INSTRUCTION,
    ).execute()
    return Path(str(value)).expanduser()


def prompt_text(message: str, default: str) -> str:
    value = inquirer.text(
        message=message,
        default=default,
        instruction=TEXT_INSTRUCTION,
    ).execute()
    return str(value).strip() or default


def prompt_clients(default: tuple[Client, ...]) -> tuple[Client, ...]:
    selected = inquirer.checkbox(
        message="Select AI clients to configure",
        instruction=CHECKBOX_INSTRUCTION,
        choices=[
            {"name": "Codex  AGENTS.md + .agents/skills", "value": Client.CODEX},
            {"name": "Claude CLAUDE.md + .claude/skills", "value": Client.CLAUDE},
            {"name": "Cursor .cursor/rules/agent-feed.mdc", "value": Client.CURSOR},
        ],
        default=list(default),
    ).execute()
    return tuple(selected)


def prompt_verification_profile(default: VerificationProfile) -> VerificationProfile:
    selected = inquirer.select(
        message="Select project verification profile",
        instruction=SELECT_INSTRUCTION,
        choices=[
            {"name": f"{profile.value}  {PROFILE_LABELS[profile]}", "value": profile}
            for profile in VERIFICATION_PROFILES
        ],
        default=default,
    ).execute()
    return VerificationProfile(str(selected))


def prompt_checks(default: tuple[Check, ...]) -> tuple[Check, ...]:
    selected = inquirer.checkbox(
        message="Select checks to run",
        instruction=CHECKBOX_INSTRUCTION,
        choices=[{"name": check.value, "value": check} for check in CHECKS],
        default=list(default),
    ).execute()
    return tuple(selected)


def prompt_confirm(message: str, default: bool = True) -> bool:
    return bool(
        inquirer.confirm(
            message=message,
            default=default,
            instruction=CONFIRM_INSTRUCTION,
        ).execute()
    )
