"""Interactive prompts for Agent Feed."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.keys import Keys

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
STEP_TEXT_INSTRUCTION = "Enter confirm, Esc back"
STEP_SELECT_INSTRUCTION = "Use ↑/↓, Enter confirm, Esc back"
STEP_CHECKBOX_INSTRUCTION = "Use ↑/↓, Space select, Enter confirm, Esc back"
ESC_KEY_TIMEOUT_SECONDS = 0.0


def make_escape_eager(prompt: Any) -> Any:
    """Register standalone Esc as an eager skip binding so it does not wait for Alt sequences."""

    def skip(event: Any) -> None:
        handler = getattr(prompt, "_handle_skip", None)
        if callable(handler):
            handler(event)
            return
        status = getattr(prompt, "status", None)
        if isinstance(status, dict):
            status["answered"] = True
            status["skipped"] = True
            status["result"] = None
        event.app.exit(result=None)

    register_kb = getattr(prompt, "register_kb", None)
    if not callable(register_kb):
        return prompt
    try:
        register_kb(Keys.Escape, eager=True)(skip)
    except TypeError:
        register_kb(Keys.Escape)(skip)
    return prompt


def tune_escape_key(prompt: Any) -> Any:
    """Make standalone Esc feel like an immediate back/cancel action."""
    session = getattr(prompt, "_session", None)
    application = (
        getattr(prompt, "application", None)
        or getattr(prompt, "_application", None)
        or getattr(session, "app", None)
    )
    if application is not None:
        application.ttimeoutlen = ESC_KEY_TIMEOUT_SECONDS
    return make_escape_eager(prompt)


def can_prompt() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_main_action() -> str:
    return str(
        inquirer.select(
            message="What do you want to do?",
            instruction=SELECT_INSTRUCTION,
            choices=[
                {"name": "Initialize AI docs", "value": "init"},
                {"name": "Upgrade AI docs", "value": "upgrade"},
                {"name": "Sync client adapters", "value": "sync"},
                {"name": "Check docs health", "value": "check"},
                {"name": "Show status", "value": "status"},
                {"name": "Preview writes", "value": "preview"},
                {"name": "Uninstall AI docs", "value": "uninstall"},
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


def prompt_path_step(message: str, default: Path) -> Path | None:
    prompt = inquirer.text(
        message=message,
        default=str(default),
        instruction=STEP_TEXT_INSTRUCTION,
        mandatory=False,
        keybindings={"skip": [{"key": Keys.Escape}]},
    )
    value = tune_escape_key(prompt).execute()
    if value is None:
        return None
    return Path(str(value or default)).expanduser()


def prompt_text(message: str, default: str) -> str:
    value = inquirer.text(
        message=message,
        default=default,
        instruction=TEXT_INSTRUCTION,
    ).execute()
    return str(value).strip() or default


def prompt_text_step(message: str, default: str) -> str | None:
    prompt = inquirer.text(
        message=message,
        default=default,
        instruction=STEP_TEXT_INSTRUCTION,
        mandatory=False,
        keybindings={"skip": [{"key": Keys.Escape}]},
    )
    value = tune_escape_key(prompt).execute()
    if value is None:
        return None
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


def prompt_clients_step(default: tuple[Client, ...]) -> tuple[Client, ...] | None:
    prompt = inquirer.checkbox(
        message="Select AI clients to configure",
        instruction=STEP_CHECKBOX_INSTRUCTION,
        choices=[
            {"name": "Codex  AGENTS.md + .agents/skills", "value": Client.CODEX},
            {"name": "Claude CLAUDE.md + .claude/skills", "value": Client.CLAUDE},
            {"name": "Cursor .cursor/rules/agent-feed.mdc", "value": Client.CURSOR},
        ],
        default=list(default),
        mandatory=False,
        keybindings={"skip": [{"key": Keys.Escape}]},
    )
    selected = tune_escape_key(prompt).execute()
    if selected is None:
        return None
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


def prompt_verification_profile_step(
    default: VerificationProfile,
) -> VerificationProfile | None:
    prompt = inquirer.select(
        message="Select project verification profile",
        instruction=STEP_SELECT_INSTRUCTION,
        choices=[
            {"name": f"{profile.value}  {PROFILE_LABELS[profile]}", "value": profile}
            for profile in VERIFICATION_PROFILES
        ],
        default=default,
        mandatory=False,
        keybindings={"skip": [{"key": Keys.Escape}]},
    )
    selected = tune_escape_key(prompt).execute()
    if selected is None:
        return None
    return VerificationProfile(str(selected))


def prompt_checks(default: tuple[Check, ...]) -> tuple[Check, ...]:
    selected = inquirer.checkbox(
        message="Select checks to run",
        instruction=CHECKBOX_INSTRUCTION,
        choices=[{"name": check.value, "value": check} for check in CHECKS],
        default=list(default),
    ).execute()
    return tuple(selected)


def prompt_skill_hub_keyword(default: str = "") -> str | None:
    prompt = inquirer.text(
        message="Search curated skill hubs",
        default=default,
        instruction="Type a keyword, Enter to search, Esc to go back",
        mandatory=False,
        keybindings={"skip": [{"key": Keys.Escape}]},
    )
    value = tune_escape_key(prompt).execute()
    if value is None:
        return None
    return str(value or "").strip()


def prompt_secret(message: str) -> str:
    prompt = inquirer.secret(
        message=message,
        instruction="Paste token, Enter to continue, Esc to skip",
        mandatory=False,
        keybindings={"skip": [{"key": Keys.Escape}]},
    )
    value = tune_escape_key(prompt).execute()
    return str(value or "").strip()


def prompt_skill_hub_selection(
    choices: list[dict[str, Any]],
    *,
    on_preview: Any,
) -> list[str] | None:
    prompt = inquirer.checkbox(
        message="Select skills to install",
        instruction="Space select, v preview, Enter install, Esc back",
        long_instruction=(
            "Tip: v fetches and previews the highlighted skill; "
            "Cmd/Ctrl-click source URLs when your terminal supports links."
        ),
        choices=choices,
        mandatory=False,
        keybindings={
            "skip": [{"key": Keys.Escape}],
            "preview": [{"key": "v"}],
        },
    )
    prompt.kb_func_lookup = {
        "preview": [
            {
                "func": lambda _event: run_in_terminal(
                    lambda: on_preview(prompt.content_control.selection),
                    in_executor=True,
                )
            }
        ]
    }
    result = tune_escape_key(prompt).execute()
    if result is None:
        return None
    return [str(item) for item in result]


def prompt_confirm(message: str, default: bool = True) -> bool:
    return bool(
        inquirer.confirm(
            message=message,
            default=default,
            instruction=CONFIRM_INSTRUCTION,
        ).execute()
    )


def prompt_view_diff_key() -> bool:
    key = read_single_key()
    return key.lower() == "v" if key else False


def read_single_key() -> str:
    if os.name == "nt":
        return read_single_key_windows()
    return read_single_key_posix()


def read_single_key_windows() -> str:
    try:
        import msvcrt as raw_msvcrt
    except ImportError:
        return ""
    msvcrt: Any = raw_msvcrt
    key_bytes = msvcrt.getch()
    try:
        key = str(key_bytes.decode("utf-8", errors="ignore"))
    except AttributeError:
        key = str(key_bytes)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return key


def read_single_key_posix() -> str:
    try:
        import termios
        import tty
    except ImportError:
        return ""

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)
        sys.stdout.write("\n")
        sys.stdout.flush()
    return key
