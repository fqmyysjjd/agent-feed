"""Project-visible Agent Feed config operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_feed.models import VerificationProfile, WriteAction
from agent_feed.project_settings import metadata_settings_errors
from agent_feed.upgrade import METADATA_PATH, is_installed, read_metadata, unified_diff
from agent_feed.asset_trust import (
    missing_project_entries,
    project_local_config_errors,
    trust_config_path,
    validate_config_shape as validate_user_config_shape,
)


MUTABLE_TOP_LEVEL_KEYS = {"project_name", "verification_profile"}


@dataclass(frozen=True)
class ConfigCheckReport:
    target: Path
    project_config: Path
    user_config: Path | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def config_path(root: Path) -> Path:
    return root / METADATA_PATH


def read_config(root: Path) -> tuple[dict[str, Any], list[str]]:
    if not is_installed(root):
        return {}, ["missing Agent Feed installation; run agent-feed init first"]
    path = config_path(root)
    if not path.is_file():
        return {}, [f"missing {METADATA_PATH}; run agent-feed upgrade first"]
    data = read_metadata(root)
    if not data:
        return {}, [f"{METADATA_PATH} must be a JSON object"]
    return data, []


def get_config_value(root: Path, key: str | None) -> tuple[Any, list[str]]:
    data, errors = read_config(root)
    if errors:
        return None, errors
    if key is None or not key.strip():
        return data, []
    value, found = lookup_path(data, normalize_config_key(key))
    if not found:
        return None, [f"{METADATA_PATH} has no config key {key!r}"]
    return value, []


def set_config_value(
    root: Path,
    *,
    key: str,
    raw_value: str,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    data, errors = read_config(root)
    if errors:
        return [], errors

    normalized_key = normalize_config_key(key)
    key_errors = validate_mutable_key(normalized_key)
    if key_errors:
        return [], key_errors

    value = parse_config_value(raw_value)
    value_errors = validate_config_value(normalized_key, value)
    if value_errors:
        return [], value_errors

    next_data = json.loads(json.dumps(data))
    assign_path(next_data, normalized_key, value)
    shape_errors = validate_config_shape_data(next_data)
    if shape_errors:
        return [], shape_errors

    path = config_path(root)
    current = path.read_text(encoding="utf-8")
    expected = json.dumps(next_data, indent=2, ensure_ascii=False) + "\n"
    if current == expected:
        return [WriteAction(path=path, action="skip", detail="config is current")], []

    diff = unified_diff(METADATA_PATH, current, expected)
    if dry_run:
        return [WriteAction(path=path, action="would update", diff=diff)], []

    path.write_text(expected, encoding="utf-8")
    return [WriteAction(path=path, action="update", diff=diff)], []


def normalize_config_key(key: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in key.strip().split(".") if part.strip())
    if parts and parts[0] == "setting":
        return ("settings", *parts[1:])
    return parts


def lookup_path(data: dict[str, Any], path: tuple[str, ...]) -> tuple[Any, bool]:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def assign_path(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current: dict[str, Any] = data
    for part in path[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[path[-1]] = value


def validate_mutable_key(path: tuple[str, ...]) -> list[str]:
    if not path:
        return ["config key is required"]
    if path[0] in MUTABLE_TOP_LEVEL_KEYS and len(path) == 1:
        return []
    if path[0] == "settings" and len(path) >= 2:
        return []
    return [
        "config set supports project_name, verification_profile, and settings.* keys only"
    ]


def parse_config_value(raw: str) -> Any:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def validate_config_value(path: tuple[str, ...], value: Any) -> list[str]:
    dotted = ".".join(path)
    if dotted == "project_name":
        if isinstance(value, str) and value.strip():
            return []
        return ["project_name must be a non-empty string"]
    if dotted == "verification_profile":
        if isinstance(value, str):
            try:
                VerificationProfile(value.strip().lower())
            except ValueError:
                pass
            else:
                return []
        allowed = ", ".join(profile.value for profile in VerificationProfile)
        return [f"verification_profile must be one of {allowed}"]
    return []


def validate_config_shape_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "schema_version",
        "agent_feed_version",
        "template",
        "project_name",
        "verification_profile",
    ):
        if key not in data:
            errors.append(f"{METADATA_PATH} missing {key}")
    if data.get("schema_version") != 1:
        errors.append(f"{METADATA_PATH} schema_version must be 1")
    if data.get("template") != "standard":
        errors.append(f"{METADATA_PATH} template must be standard")
    if "verification_profile" in data:
        errors.extend(validate_config_value(("verification_profile",), data["verification_profile"]))
    if "project_name" in data:
        errors.extend(validate_config_value(("project_name",), data["project_name"]))
    errors.extend(metadata_settings_errors(data, label=str(METADATA_PATH)))
    return errors


def check_config(root: Path) -> ConfigCheckReport:
    project_path = config_path(root)
    errors: list[str] = []
    warnings: list[str] = []

    data, project_errors = read_config(root)
    if project_errors:
        errors.extend(project_errors)
    else:
        errors.extend(validate_config_shape_data(data))

    user_config, user_config_errors = trust_config_path()
    if user_config_errors:
        errors.extend(user_config_errors)
    elif user_config is not None:
        errors.extend(project_local_config_errors(root, user_config))
        if user_config.exists() or user_config.with_name("agent-feed.json").exists():
            errors.extend(validate_user_config_shape(user_config))
        else:
            errors.append(
                f"missing user-level Agent Feed config: {user_config}. "
                "Run agent-feed env setup."
            )

    stale_entries, stale_errors = missing_project_entries()
    errors.extend(stale_errors)
    if stale_entries is not None:
        for project_root in stale_entries.project_roots:
            warnings.append(
                f"{stale_entries.config_file}: stale project entry points to missing directory "
                f"{project_root}"
            )

    return ConfigCheckReport(
        target=root,
        project_config=project_path,
        user_config=user_config,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
