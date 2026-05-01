"""Non-destructive update planning for installed Agent Feed assets."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any

from agent_feed import __version__
from agent_feed.models import VerificationProfile, WriteAction
from agent_feed.templates import canonical_write_plan


METADATA_PATH = Path(".agents/agent-feed.json")
PROJECT_NAME_SUFFIX = " AI Development Instructions"
PROFILE_PATTERN = re.compile(r"Verification profile:\s*([a-z0-9_-]+)", re.IGNORECASE)


def is_installed(root: Path) -> bool:
    return (root / "AGENTS.md").is_file() and (root / ".agents").is_dir()


def installed_version(root: Path) -> str | None:
    data = read_metadata(root)
    value = data.get("agent_feed_version")
    return value if isinstance(value, str) and value else None


def read_metadata(root: Path) -> dict[str, Any]:
    path = root / METADATA_PATH
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def infer_project_name(root: Path) -> str:
    metadata = read_metadata(root)
    project_name = metadata.get("project_name")
    if isinstance(project_name, str) and project_name.strip():
        return project_name.strip()

    agents_md = root / "AGENTS.md"
    if agents_md.is_file():
        for line in agents_md.read_text(encoding="utf-8").splitlines():
            if not line.startswith("# "):
                continue
            heading = line.removeprefix("# ").strip()
            if heading.endswith(PROJECT_NAME_SUFFIX):
                return heading[: -len(PROJECT_NAME_SUFFIX)].strip() or root.name
            return heading or root.name

    return root.name


def infer_verification_profile(root: Path) -> VerificationProfile:
    metadata = read_metadata(root)
    profile = metadata.get("verification_profile")
    if isinstance(profile, str):
        parsed = parse_profile(profile)
        if parsed is not None:
            return parsed

    for path in [
        root / ".agents/scripts/verify-agent-dev.sh",
        root / ".agents/project/verification-profile.md",
    ]:
        if not path.is_file():
            continue
        match = PROFILE_PATTERN.search(path.read_text(encoding="utf-8"))
        if match:
            parsed = parse_profile(match.group(1))
            if parsed is not None:
                return parsed

    return VerificationProfile.PYTHON


def parse_profile(value: str) -> VerificationProfile | None:
    try:
        return VerificationProfile(value.strip().lower())
    except ValueError:
        return None


def update_plan(
    target: Path,
    *,
    project_name: str,
    verification_profile: VerificationProfile,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    if not is_installed(target):
        return [], ["missing Agent Feed installation; run agent-feed init first"]

    actions: list[WriteAction] = []
    errors: list[str] = []
    for path, expected in canonical_write_plan(
        target,
        project_name,
        verification_profile,
    ):
        rel_path = path.relative_to(target)
        if path.exists() and not path.is_file():
            errors.append(f"{rel_path} exists but is not a file")
            continue
        current = path.read_text(encoding="utf-8") if path.exists() and path.is_file() else None

        if current == expected:
            continue

        if current is None:
            actions.append(write_or_preview(path, expected, "create", dry_run=dry_run))
            continue

        diff = unified_diff(rel_path, current, expected)
        if is_user_maintained_path(rel_path):
            actions.append(
                WriteAction(
                    path=path,
                    action="skip",
                    detail="user-maintained; differs from current template; not overwritten",
                    diff=diff,
                )
            )
            continue

        actions.append(write_or_preview(path, expected, "update", dry_run=dry_run, diff=diff))

    if not actions:
        actions.append(
            WriteAction(
                path=target,
                action="skip",
                detail=f"canonical assets already match agent-feed {__version__}",
            )
        )

    return actions, errors


def write_or_preview(
    path: Path,
    content: str,
    action: str,
    *,
    dry_run: bool,
    diff: str = "",
) -> WriteAction:
    reported_action = f"would {action}" if dry_run else action
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if path.suffix == ".sh":
            path.chmod(0o755)
    return WriteAction(path=path, action=reported_action, diff=diff)


def is_user_maintained_path(path: Path) -> bool:
    return path.parts[:2] in {
        (".agents", "project"),
        (".agents", "domain"),
    }


def unified_diff(path: Path, current: str, expected: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            expected.splitlines(),
            fromfile=f"{path} (current)",
            tofile=f"{path} (template {__version__})",
            lineterm="",
        )
    )
