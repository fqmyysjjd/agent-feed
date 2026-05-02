"""Environment setup helpers for Agent Feed."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agent_feed.asset_trust import (
    AGENT_FEED_HOME_ENV,
    CONFIG_FILE_NAME,
    LEGACY_CONFIG_FILE_NAME,
    default_trust_config,
    legacy_config_path,
    read_existing_or_legacy_config,
    recommended_agent_feed_home,
    resolve_config_path,
    validate_config_shape,
)
from agent_feed.models import WriteAction

SHELL_AUTO = "auto"
SUPPORTED_SHELLS = {"zsh", "bash", "fish", "powershell"}
MANAGED_START = "# >>> agent-feed env >>>"
MANAGED_END = "# <<< agent-feed env <<<"


@dataclass(frozen=True)
class EnvStatus:
    configured: bool
    home: Path | None
    config_file: Path | None
    errors: tuple[str, ...]
    recommendation: Path

    @property
    def ok(self) -> bool:
        return self.configured and not self.errors


@dataclass(frozen=True)
class EnvSetupResult:
    home: Path
    config_file: Path
    shell: str
    actions: tuple[WriteAction, ...]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def suggested_agent_feed_home(target: Path | None = None) -> Path:
    candidate = recommended_agent_feed_home()
    if target is not None:
        try:
            candidate.resolve().relative_to(target.resolve())
        except ValueError:
            return candidate
        return Path.home() / ".agent-feed"
    return candidate


def current_agent_feed_home() -> Path | None:
    raw_home = os.environ.get(AGENT_FEED_HOME_ENV, "").strip()
    if not raw_home:
        return None
    return Path(raw_home).expanduser()


def get_env_status(target: Path | None = None) -> EnvStatus:
    recommendation = suggested_agent_feed_home(target)
    home = current_agent_feed_home()
    if home is None:
        return EnvStatus(
            configured=False,
            home=None,
            config_file=None,
            errors=(f"{AGENT_FEED_HOME_ENV} is not set",),
            recommendation=recommendation,
        )

    errors: list[str] = []
    if target is not None:
        try:
            resolve_config_path(home).resolve().relative_to(target.resolve())
        except ValueError:
            pass
        else:
            errors.append(
                f"{AGENT_FEED_HOME_ENV} points inside the current project ({target.resolve()})"
            )
    if not home.exists():
        errors.append(f"{home} does not exist")
    elif not home.is_dir():
        errors.append(f"{home} is not a directory")
    config_file = resolve_config_path(home)
    if config_file.exists():
        errors.extend(validate_config_shape(config_file))
    else:
        errors.append(f"{config_file} does not exist")
    return EnvStatus(
        configured=True,
        home=home,
        config_file=config_file,
        errors=tuple(errors),
        recommendation=recommendation,
    )


def resolve_shell(shell: str = SHELL_AUTO) -> tuple[str | None, str | None]:
    if shell != SHELL_AUTO:
        if shell not in SUPPORTED_SHELLS:
            return None, f"unsupported shell: {shell}"
        return shell, None
    if sys.platform == "win32":
        return "powershell", None
    shell_name = Path(os.environ.get("SHELL", "")).name
    if shell_name in {"zsh", "bash", "fish"}:
        return shell_name, None
    return None, "could not detect shell; pass --shell zsh, bash, fish, or powershell"


def shell_config_path(shell: str) -> Path | None:
    home = Path.home()
    if shell == "zsh":
        zdotdir = os.environ.get("ZDOTDIR")
        return (Path(zdotdir).expanduser() if zdotdir else home) / ".zshrc"
    if shell == "bash":
        return home / ".bashrc"
    if shell == "fish":
        return home / ".config/fish/config.fish"
    return None


def shell_export_text(home: Path, shell: str) -> str:
    if shell == "fish":
        return f'set -gx {AGENT_FEED_HOME_ENV} "{home}"'
    if shell == "powershell":
        return f"[Environment]::SetEnvironmentVariable('{AGENT_FEED_HOME_ENV}', '{home}', 'User')"
    return f'export {AGENT_FEED_HOME_ENV}="{home}"'


def managed_env_block(home: Path, shell: str) -> str:
    return f"{MANAGED_START}\n{shell_export_text(home, shell)}\n{MANAGED_END}\n"


def env_uninstall_plan(
    *,
    home: Path | None,
    shell: str,
    dry_run: bool,
    remove_home: bool,
) -> tuple[list[WriteAction], list[str]]:
    resolved_shell, shell_error = resolve_shell(shell)
    resolved_home = home.expanduser() if home is not None else current_agent_feed_home()
    if resolved_home is None:
        resolved_home = suggested_agent_feed_home()

    if shell_error or resolved_shell is None:
        return [], [shell_error or "unsupported shell"]

    action_prefix = "would " if dry_run else ""
    actions: list[WriteAction] = []
    if resolved_shell == "powershell" and sys.platform == "win32":
        actions.append(
            WriteAction(
                path=Path("HKCU/Environment") / AGENT_FEED_HOME_ENV,
                action=f"{action_prefix}update".strip(),
                detail="remove user environment variable",
            )
        )
    elif resolved_shell == "powershell":
        actions.append(
            WriteAction(
                path=Path("PowerShell user environment"),
                action="skip",
                detail="run env print or remove AGENT_FEED_HOME manually on this platform",
            )
        )
    else:
        config_path = shell_config_path(resolved_shell)
        if config_path is None:
            return actions, [f"unsupported shell: {resolved_shell}"]
        shell_action = remove_shell_config_block(config_path, dry_run=dry_run)
        if shell_action is not None:
            actions.append(shell_action)

    if remove_home:
        if resolved_home.exists():
            if is_agent_feed_home(resolved_home):
                actions.append(
                    WriteAction(
                        path=resolved_home,
                        action="would delete" if dry_run else "delete",
                        detail="Agent Feed user-level home",
                    )
                )
            else:
                actions.append(
                    WriteAction(
                        path=resolved_home,
                        action="skip",
                        detail="not removed because this path does not look like an Agent Feed home",
                    )
                )
        else:
            actions.append(
                WriteAction(
                    path=resolved_home,
                    action="skip",
                    detail="Agent Feed user-level home already absent",
                )
            )
    return actions, []


def is_agent_feed_home(path: Path) -> bool:
    if not path.is_dir():
        return False
    config_file = path / CONFIG_FILE_NAME
    legacy_file = path / LEGACY_CONFIG_FILE_NAME
    if not config_file.is_file() and not legacy_file.is_file():
        return False
    _state, errors, _used_legacy = read_existing_or_legacy_config(config_file)
    return not errors


def apply_env_uninstall_plan(actions: list[WriteAction], *, shell: str) -> list[WriteAction]:
    resolved_shell, _shell_error = resolve_shell(shell)
    applied: list[WriteAction] = []
    for action in actions:
        if (
            action.action == "update"
            and action.path == Path("HKCU/Environment") / AGENT_FEED_HOME_ENV
        ):
            remove_windows_user_env()
            applied.append(WriteAction(action.path, "updated", action.detail))
        elif action.action == "update" and action.path.exists():
            current = action.path.read_text(encoding="utf-8")
            next_text = remove_managed_block(current)
            if current == next_text:
                applied.append(WriteAction(action.path, "skip", "shell config is current"))
            else:
                backup_path = backup_file(action.path)
                shutil.copy2(action.path, backup_path)
                action.path.write_text(next_text, encoding="utf-8")
                applied.append(
                    WriteAction(
                        action.path,
                        "updated",
                        f"removed {AGENT_FEED_HOME_ENV}; backup: {backup_path}",
                    )
                )
        elif action.action == "delete" and action.path.exists():
            if action.path.is_dir():
                shutil.rmtree(action.path)
            else:
                action.path.unlink()
            applied.append(WriteAction(action.path, "deleted", action.detail))
        elif action.action == "skip":
            applied.append(action)

    if resolved_shell == "powershell" and sys.platform == "win32":
        os.environ.pop(AGENT_FEED_HOME_ENV, None)
    return applied


def setup_agent_feed_home(
    *,
    home: Path | None,
    target: Path | None,
    shell: str,
    dry_run: bool,
    force: bool = False,
) -> EnvSetupResult:
    resolved_shell, shell_error = resolve_shell(shell)
    resolved_home = home.expanduser() if home is not None else suggested_agent_feed_home(target)
    config_file = resolved_home / CONFIG_FILE_NAME
    if shell_error or resolved_shell is None:
        return EnvSetupResult(
            home=resolved_home,
            config_file=config_file,
            shell=shell,
            actions=(),
            errors=(shell_error or "unsupported shell",),
        )

    errors = home_boundary_errors(resolved_home, target)
    current_home = current_agent_feed_home()
    if current_home is not None and current_home != resolved_home and not force:
        errors.append(
            f"{AGENT_FEED_HOME_ENV} is already set to {current_home}; pass --force to replace it"
        )
    if config_file.exists():
        errors.extend(validate_config_shape(config_file))
    if errors:
        return EnvSetupResult(
            home=resolved_home,
            config_file=config_file,
            shell=resolved_shell,
            actions=(),
            errors=tuple(errors),
        )

    actions: list[WriteAction] = []
    config_action = ensure_config_file(config_file, dry_run=dry_run)
    if config_action is not None:
        actions.append(config_action)

    if resolved_shell == "powershell" and sys.platform == "win32":
        actions.append(
            WriteAction(
                path=Path("HKCU/Environment") / AGENT_FEED_HOME_ENV,
                action="would update" if dry_run else "update",
                detail=f"set user environment variable to {resolved_home}",
            )
        )
        if not dry_run:
            set_windows_user_env(resolved_home)
    elif resolved_shell == "powershell":
        actions.append(
            WriteAction(
                path=Path("PowerShell user environment"),
                action="skip",
                detail=shell_export_text(resolved_home, resolved_shell),
            )
        )
    else:
        config_path = shell_config_path(resolved_shell)
        if config_path is None:
            return EnvSetupResult(
                home=resolved_home,
                config_file=config_file,
                shell=resolved_shell,
                actions=tuple(actions),
                errors=(f"unsupported shell: {resolved_shell}",),
            )
        shell_action = update_shell_config(
            config_path,
            managed_env_block(resolved_home, resolved_shell),
            dry_run=dry_run,
        )
        if shell_action is not None:
            actions.append(shell_action)

    if not dry_run:
        os.environ[AGENT_FEED_HOME_ENV] = str(resolved_home)

    return EnvSetupResult(
        home=resolved_home,
        config_file=config_file,
        shell=resolved_shell,
        actions=tuple(actions),
        errors=(),
    )


def home_boundary_errors(home: Path, target: Path | None) -> list[str]:
    if target is None:
        return []
    try:
        home.resolve().relative_to(target.resolve())
    except ValueError:
        return []
    return [f"{AGENT_FEED_HOME_ENV} home points inside the current project ({target.resolve()})"]


def ensure_config_file(config_file: Path, *, dry_run: bool) -> WriteAction | None:
    legacy_file = legacy_config_path(config_file)
    if config_file.exists() or legacy_file.exists():
        _state, errors, used_legacy = read_existing_or_legacy_config(config_file)
        if errors:
            return WriteAction(
                path=config_file,
                action="blocked",
                detail="external Agent Feed config is invalid",
            )
        if used_legacy:
            action = "would update" if dry_run else "update"
            if not dry_run:
                migrate_legacy_config(config_file)
            return WriteAction(
                path=config_file,
                action=action,
                detail="migrate external Agent Feed config to config.json",
            )
        return WriteAction(
            path=config_file,
            action="skip",
            detail="external Agent Feed config exists",
        )
    action = "would create" if dry_run else "create"
    if not dry_run:
        write_config_file(config_file)
    return WriteAction(path=config_file, action=action, detail="external Agent Feed config")


def write_config_file(config_file: Path) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json_text(default_trust_config()),
        encoding="utf-8",
    )
    legacy_file = legacy_config_path(config_file)
    if legacy_file.exists():
        legacy_file.unlink()


def migrate_legacy_config(config_file: Path) -> None:
    state, errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if errors:
        return
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json_text(state), encoding="utf-8")
    legacy_file = legacy_config_path(config_file)
    if legacy_file.exists():
        legacy_file.unlink()


def update_shell_config(path: Path, block: str, *, dry_run: bool) -> WriteAction | None:
    existed = path.exists()
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    next_text = replace_or_append_block(current, block)
    if current == next_text:
        return WriteAction(path=path, action="skip", detail="shell config is current")
    action = "would update" if existed else "would create"
    if not dry_run:
        if existed:
            backup_path = backup_file(path)
            shutil.copy2(path, backup_path)
            detail = f"set {AGENT_FEED_HOME_ENV}; backup: {backup_path}"
        else:
            detail = f"set {AGENT_FEED_HOME_ENV}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(next_text, encoding="utf-8")
        return WriteAction(path=path, action="update" if existed else "create", detail=detail)
    return WriteAction(path=path, action=action, detail=f"set {AGENT_FEED_HOME_ENV}")


def replace_or_append_block(current: str, block: str) -> str:
    start = current.find(MANAGED_START)
    end = current.find(MANAGED_END)
    if start != -1 and end != -1 and end > start:
        end += len(MANAGED_END)
        suffix = current[end:]
        if suffix.startswith("\n"):
            suffix = suffix[1:]
        prefix = current[:start].rstrip()
        pieces = [piece for piece in (prefix, block.rstrip(), suffix.lstrip()) if piece]
        return "\n\n".join(pieces) + "\n"
    separator = "\n\n" if current and not current.endswith("\n\n") else ""
    return f"{current}{separator}{block}"


def remove_shell_config_block(path: Path, *, dry_run: bool) -> WriteAction | None:
    if not path.exists():
        return WriteAction(path, "skip", "shell config is absent")
    current = path.read_text(encoding="utf-8")
    next_text = remove_managed_block(current)
    if current == next_text:
        return WriteAction(path, "skip", "agent-feed env block is absent")
    return WriteAction(
        path,
        "would update" if dry_run else "update",
        detail=f"remove {AGENT_FEED_HOME_ENV} managed block",
    )


def remove_managed_block(current: str) -> str:
    start = current.find(MANAGED_START)
    end = current.find(MANAGED_END)
    if start == -1 or end == -1 or end <= start:
        return current
    end += len(MANAGED_END)
    suffix = current[end:]
    if suffix.startswith("\n"):
        suffix = suffix[1:]
    prefix = current[:start].rstrip()
    pieces = [piece for piece in (prefix, suffix.lstrip()) if piece]
    return ("\n\n".join(pieces) + "\n") if pieces else ""


def backup_file(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return path.with_name(f"{path.name}.bak-agent-feed-{stamp}")


def set_windows_user_env(home: Path) -> None:
    if sys.platform != "win32":
        return

    import winreg  # type: ignore[import-not-found, unused-ignore]

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, AGENT_FEED_HOME_ENV, 0, winreg.REG_EXPAND_SZ, str(home))


def remove_windows_user_env() -> None:
    if sys.platform != "win32":
        return

    import winreg  # type: ignore[import-not-found, unused-ignore]

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        try:
            winreg.DeleteValue(key, AGENT_FEED_HOME_ENV)
        except FileNotFoundError:
            return


def json_text(data: dict[str, object]) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
