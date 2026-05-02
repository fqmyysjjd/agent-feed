"""External trust state for Agent Feed assets."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_feed import __version__
from agent_feed.models import WriteAction
from agent_feed.skill_index import read_frontmatter
from agent_feed.templates import standard_template_root

AGENT_FEED_HOME_ENV = "AGENT_FEED_HOME"
CONFIG_FILE_NAME = "config.json"
LEGACY_CONFIG_FILE_NAME = "agent-feed.json"
MANAGED_SCRIPT_PATHS = (
    ".agents/scripts/check-agent-assets.sh",
    ".agents/scripts/check-agent-trust.sh",
    ".agents/scripts/index-skills.sh",
    ".agents/scripts/sync-agent-assets.sh",
    ".agents/scripts/verify-agent-dev.sh",
)


@dataclass(frozen=True)
class TrustAsset:
    kind: str
    name: str
    path: Path
    source: str
    trust: str
    sha256: str


@dataclass(frozen=True)
class TrustIssue:
    kind: str
    name: str
    path: Path
    current_sha256: str
    allowed_sha256: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class TrustReport:
    target: Path
    config_file: Path | None
    missing_state: bool
    issues: tuple[TrustIssue, ...]
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors and not self.missing_state and not self.issues


def check_asset_trust(root: Path, *, kinds: set[str] | None = None) -> TrustReport:
    config_file, errors = trust_config_path()
    if errors:
        return TrustReport(root, config_file, False, (), tuple(errors))
    if config_file is None:
        return TrustReport(root, None, False, (), (agent_feed_home_required_message(),))
    local_errors = project_local_config_errors(root, config_file)
    if local_errors:
        return TrustReport(root, config_file, False, (), tuple(local_errors))
    if not config_file.exists() and not legacy_config_path(config_file).exists():
        return TrustReport(root, config_file, True, ())
    config_errors = validate_config_shape(config_file)
    if config_errors:
        return TrustReport(root, config_file, False, (), tuple(config_errors))

    state, state_errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return TrustReport(root, config_file, False, (), tuple(state_errors))
    project = project_trust_state(state, root)
    if project is None:
        return TrustReport(root, config_file, True, ())

    entries = project.get("assets", {})
    if not isinstance(entries, dict):
        return TrustReport(
            root,
            config_file,
            False,
            (),
            (f"{config_file} project entry assets must be a JSON object",),
        )

    issues: list[TrustIssue] = []
    for asset in current_assets(root):
        if kinds is not None and asset.kind not in kinds:
            continue
        rel_path = asset.path.as_posix()
        entry = entries.get(rel_path)
        if not isinstance(entry, dict):
            issues.append(
                TrustIssue(
                    kind=asset.kind,
                    name=asset.name,
                    path=asset.path,
                    current_sha256=asset.sha256,
                    allowed_sha256=(),
                    reason="missing trust entry",
                )
            )
            continue
        allowed = tuple(
            value for value in entry.get("allowed_sha256", []) if isinstance(value, str)
        )
        if asset.sha256 not in allowed:
            issues.append(
                TrustIssue(
                    kind=asset.kind,
                    name=asset.name,
                    path=asset.path,
                    current_sha256=asset.sha256,
                    allowed_sha256=allowed,
                    reason="trusted hash mismatch",
                )
            )
    return TrustReport(root, config_file, False, tuple(issues))


def asset_trust_errors(root: Path, *, kinds: set[str] | None = None) -> list[str]:
    report = check_asset_trust(root, kinds=kinds)
    if report.errors:
        return list(report.errors)
    if report.missing_state:
        config_text = str(report.config_file) if report.config_file else f"${AGENT_FEED_HOME_ENV}"
        return [
            f"missing external Agent Feed trust state for {root}; expected {config_text}. "
            "Review current AI assets, then run: agent-feed index-skills -y"
        ]
    errors: list[str] = []
    for issue in report.issues:
        errors.append(
            f"{issue.path}: {issue.reason}. Highest-priority Agent Feed rule requires "
            "stopping before this asset is used. Inspect with agent-feed preview; "
            "if intentional, accept with agent-feed index-skills -y."
        )
    return errors


def sync_asset_trust(
    root: Path,
    *,
    dry_run: bool,
    accept_changed: bool,
    prune_missing: bool = True,
    project_name: str | None = None,
) -> tuple[list[WriteAction], list[str]]:
    config_file, errors = trust_config_path()
    if errors:
        return [], errors
    if config_file is None:
        return [], [agent_feed_home_required_message()]
    local_errors = project_local_config_errors(root, config_file)
    if local_errors:
        return [], local_errors

    state, state_errors, used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return [], state_errors
    projects = state.setdefault("projects", {})
    if not isinstance(projects, dict):
        return [], [f"{config_file} projects must be a JSON object"]

    key = project_key(root)
    project = projects.get(key)
    if not isinstance(project, dict):
        project = {
            "project_root": str(root.resolve()),
            "project_name": project_name or root.name,
            "assets": {},
        }
        projects[key] = project

    project["project_root"] = str(root.resolve())
    if project_name:
        project["project_name"] = project_name
    project["agent_feed_version"] = __version__

    entries = project.setdefault("assets", {})
    if not isinstance(entries, dict):
        return [], [f"{config_file} project {key} assets must be a JSON object"]

    errors = []
    changed = not config_file.exists() or used_legacy
    current_paths: set[str] = set()
    for asset in current_assets(root):
        rel_path = asset.path.as_posix()
        current_paths.add(rel_path)
        entry = entries.get(rel_path)
        if not isinstance(entry, dict):
            entries[rel_path] = asset_entry(asset)
            changed = True
            continue

        allowed = entry.setdefault("allowed_sha256", [])
        if not isinstance(allowed, list):
            return [], [f"{config_file} entry {rel_path} allowed_sha256 must be a list"]
        if asset.sha256 not in allowed:
            if not accept_changed:
                errors.append(
                    f"{asset.path}: trusted hash changed. Inspect with agent-feed preview "
                    "before accepting with agent-feed index-skills -y."
                )
                continue
            allowed.append(asset.sha256)
            changed = True

        for entry_key, value in asset_entry(asset).items():
            if entry_key == "allowed_sha256":
                continue
            if entry.get(entry_key) != value:
                entry[entry_key] = value
                changed = True

    if prune_missing:
        for rel_path in list(entries):
            if rel_path not in current_paths:
                del entries[rel_path]
                changed = True

    state["schema_version"] = 1
    state["agent_feed_version"] = __version__

    if errors:
        return [], errors
    if not changed and config_file.exists():
        return [
            WriteAction(path=config_file, action="skip", detail="external trust is current")
        ], []

    expected = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    action = "update" if config_file.exists() else "create"
    if dry_run:
        return [
            WriteAction(
                path=config_file,
                action=f"would {action}",
                detail="external Agent Feed trust config",
            )
        ], []

    write_user_config(config_file, expected)
    return [
        WriteAction(
            path=config_file,
            action=action,
            detail="recorded trusted AI asset hashes outside the project",
        )
    ], []


def trust_preview_actions(root: Path) -> list[WriteAction]:
    report = check_asset_trust(root)
    if report.errors:
        return [
            WriteAction(
                path=root,
                action="blocked",
                detail=error,
            )
            for error in report.errors
        ]
    if report.missing_state:
        path = report.config_file or root
        return [
            WriteAction(
                path=path,
                action="review",
                detail="missing external trust state; run agent-feed index-skills -y after review",
            )
        ]
    actions: list[WriteAction] = []
    for issue in report.issues:
        diff = asset_diff(root, issue.path)
        if not diff:
            diff = f"{issue.path}: current content does not match trusted Agent Feed state."
        actions.append(
            WriteAction(
                path=root / issue.path,
                action="review",
                detail="Agent Feed asset changed; highest-priority rule requires stopping",
                diff=diff,
            )
        )
    return actions


def trust_config_path() -> tuple[Path | None, list[str]]:
    raw_home = os.environ.get(AGENT_FEED_HOME_ENV, "").strip()
    if not raw_home:
        return None, [agent_feed_home_required_message()]
    home = Path(raw_home).expanduser()
    return home / CONFIG_FILE_NAME, []


def resolve_config_path(home: Path) -> Path:
    current = home / CONFIG_FILE_NAME
    legacy = home / LEGACY_CONFIG_FILE_NAME
    if current.exists() or not legacy.exists():
        return current
    return legacy


def legacy_config_path(path: Path) -> Path:
    return path.parent / LEGACY_CONFIG_FILE_NAME


def project_local_config_errors(root: Path, config_file: Path) -> list[str]:
    root_path = root.resolve()
    config_path = config_file.resolve()
    if config_path.is_relative_to(root_path):
        return [
            f"{AGENT_FEED_HOME_ENV} points inside the current project ({root_path}). "
            "Use an external Agent Feed home so trusted AI asset hashes are not stored "
            "in the repository."
        ]
    return []


def agent_feed_home_required_message() -> str:
    recommended = recommended_agent_feed_home()
    return (
        f"{AGENT_FEED_HOME_ENV} is required before Agent Feed can verify or accept "
        "trusted AI assets. No project-local trust fallback is used. "
        f"Recommended user-level home: {recommended}. "
        "Run: agent-feed env setup. "
        f'macOS/Linux: export AGENT_FEED_HOME="$HOME/.agent-feed". '
        "Windows PowerShell: [Environment]::SetEnvironmentVariable("
        "'AGENT_FEED_HOME', (Join-Path $env:APPDATA 'agent-feed'), 'User')."
    )


def recommended_agent_feed_home() -> Path:
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "").strip()
        if appdata:
            return Path(appdata).expanduser() / "agent-feed"
    return Path.home() / ".agent-feed"


def project_trust_uninstall_plan(root: Path, *, dry_run: bool) -> list[WriteAction]:
    config_file, errors = trust_config_path()
    if errors or config_file is None:
        return []
    state, state_errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return [
            WriteAction(
                path=config_file,
                action="skip",
                detail="external trust config is invalid; project trust state not changed",
            )
        ]
    project = project_trust_state(state, root)
    if project is None:
        return []
    return [
        WriteAction(
            path=config_file,
            action="would update" if dry_run else "update",
            detail="remove external trust state for this project",
        )
    ]


def remove_project_trust_state(root: Path) -> list[WriteAction]:
    config_file, errors = trust_config_path()
    if errors or config_file is None:
        return []
    state, state_errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return [
            WriteAction(
                path=config_file,
                action="skip",
                detail="external trust config is invalid; project trust state not changed",
            )
        ]
    projects = state.get("projects")
    if not isinstance(projects, dict) or project_key(root) not in projects:
        return []
    del projects[project_key(root)]
    state["schema_version"] = 1
    state["agent_feed_version"] = __version__
    write_user_config(
        config_file,
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    return [
        WriteAction(
            path=config_file,
            action="updated",
            detail="removed external trust state for this project",
        )
    ]


def cleanup_missing_project_entries(
    *,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    config_file, errors = trust_config_path()
    if errors or config_file is None:
        return [], []

    state, state_errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return [], state_errors

    projects = state.get("projects")
    if not isinstance(projects, dict):
        return [], [f"{config_file} projects must be a JSON object"]

    missing_keys = [
        key
        for key, value in projects.items()
        if isinstance(key, str) and isinstance(value, dict) and not Path(key).exists()
    ]
    if not missing_keys:
        return [], []

    detail = "remove stale project entries: " + ", ".join(sorted(missing_keys))
    if dry_run:
        return [WriteAction(path=config_file, action="would update", detail=detail)], []

    for key in missing_keys:
        del projects[key]
    state["schema_version"] = 1
    state["agent_feed_version"] = __version__
    write_user_config(
        config_file,
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    return [WriteAction(path=config_file, action="update", detail=detail)], []


def current_assets(root: Path) -> list[TrustAsset]:
    assets: list[TrustAsset] = []
    skill_root = root / ".agents/skills"
    if skill_root.exists():
        for skill_file in sorted(skill_root.glob("*/SKILL.md")):
            rel_path = skill_file.relative_to(root)
            frontmatter = read_frontmatter(skill_file)
            assets.append(
                TrustAsset(
                    kind="skill",
                    name=frontmatter.get("name", skill_file.parent.name),
                    path=rel_path,
                    source=frontmatter.get("source", "unknow"),
                    trust=frontmatter.get("trust", "custom"),
                    sha256=sha256_file(skill_file),
                )
            )

    for rel_text in MANAGED_SCRIPT_PATHS:
        path = root / rel_text
        if path.exists() and path.is_file():
            assets.append(
                TrustAsset(
                    kind="script",
                    name=Path(rel_text).stem,
                    path=Path(rel_text),
                    source="agent-feed",
                    trust="core",
                    sha256=sha256_file(path),
                )
            )
    return assets


def asset_entry(asset: TrustAsset) -> dict[str, Any]:
    return {
        "kind": asset.kind,
        "name": asset.name,
        "source": asset.source,
        "trust": asset.trust,
        "allowed_sha256": [asset.sha256],
    }


def default_trust_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "agent_feed_version": __version__,
        "settings": {
            "github_token": "",
        },
        "projects": {},
    }


def read_trust_config(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return default_trust_config(), [
            f"{path} invalid JSON at line {exc.lineno}, column {exc.colno}"
        ]
    if not isinstance(data, dict):
        return default_trust_config(), [f"{path} must be a JSON object"]
    return data, []


def validate_config_shape(path: Path) -> list[str]:
    state, errors, _used_legacy = read_existing_or_legacy_config(path)
    if errors:
        return errors
    settings = state.get("settings", {})
    if not isinstance(settings, dict):
        return [f"{path} settings must be a JSON object"]
    github_token = settings.get("github_token")
    if github_token is not None and not isinstance(github_token, str):
        return [f"{path} settings.github_token must be a string when present"]
    projects = state.get("projects")
    if not isinstance(projects, dict):
        return [f"{path} projects must be a JSON object"]
    return []


def configured_github_token(root: Path | None = None) -> tuple[str | None, list[str]]:
    config_file, errors = settings_config_path(root)
    if errors:
        return None, errors
    if not config_file.exists() and not legacy_config_path(config_file).exists():
        return None, []
    shape_errors = validate_config_shape(config_file)
    if shape_errors:
        return None, shape_errors
    state, state_errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return None, state_errors
    settings = state.get("settings", {})
    if not isinstance(settings, dict):
        return None, [f"{config_file} settings must be a JSON object"]
    token = settings.get("github_token")
    if not isinstance(token, str) or not token.strip():
        return None, []
    return token.strip(), []


def save_github_token(token: str, root: Path | None = None) -> tuple[list[WriteAction], list[str]]:
    config_file, errors = settings_config_path(root)
    if errors:
        return [], errors

    state, state_errors, _used_legacy = read_existing_or_legacy_config(config_file)
    if state_errors:
        return [], state_errors

    settings = state.setdefault("settings", {})
    if not isinstance(settings, dict):
        return [], [f"{config_file} settings must be a JSON object"]

    normalized = token.strip()
    if not normalized:
        return [], ["GitHub token cannot be empty"]

    previous = settings.get("github_token")
    settings["github_token"] = normalized
    state["schema_version"] = 1
    state["agent_feed_version"] = __version__

    write_user_config(
        config_file,
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    action = "update" if isinstance(previous, str) and previous else "create"
    return [
        WriteAction(
            path=config_file,
            action=action,
            detail="saved GitHub token in the user-level Agent Feed config",
        )
    ], []


def settings_config_path(root: Path | None = None) -> tuple[Path, list[str]]:
    config_file, errors = trust_config_path()
    if not errors and config_file is not None:
        if root is not None:
            local_errors = project_local_config_errors(root, config_file)
            if local_errors:
                return config_file, local_errors
        return config_file, []
    return recommended_agent_feed_home() / CONFIG_FILE_NAME, []


def read_existing_or_legacy_config(path: Path) -> tuple[dict[str, Any], list[str], bool]:
    legacy_path = legacy_config_path(path)
    if path.exists():
        state, errors = read_trust_config(path)
        return state, errors, False
    if legacy_path.exists():
        state, errors = read_trust_config(legacy_path)
        return state, errors, True
    return default_trust_config(), [], False


def write_user_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    legacy_path = legacy_config_path(path)
    if path.name == CONFIG_FILE_NAME and legacy_path.exists():
        legacy_path.unlink()
    if os.name != "nt":
        path.chmod(0o600)


def project_key(root: Path) -> str:
    return str(root.resolve())


def project_trust_state(state: dict[str, Any], root: Path) -> dict[str, Any] | None:
    projects = state.get("projects")
    if not isinstance(projects, dict):
        return None
    project = projects.get(project_key(root))
    return project if isinstance(project, dict) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def asset_diff(root: Path, rel_path: Path) -> str:
    git_diff = git_command(root, "diff", "--", rel_path.as_posix())
    if git_diff:
        return git_diff
    staged_diff = git_command(root, "diff", "--cached", "--", rel_path.as_posix())
    if staged_diff:
        return staged_diff

    template_file = standard_template_root().joinpath(*rel_path.parts)
    current_file = root / rel_path
    if template_file.is_file() and current_file.is_file():
        return unified_diff(
            rel_path,
            current_file.read_text(encoding="utf-8"),
            template_file.read_text(encoding="utf-8"),
            expected_label="template",
        )
    return ""


def git_command(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def unified_diff(path: Path, current: str, expected: str, *, expected_label: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            expected.splitlines(),
            fromfile=f"{path} (current)",
            tofile=f"{path} ({expected_label})",
            lineterm="",
        )
    )
