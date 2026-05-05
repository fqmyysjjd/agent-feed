"""Template rendering and file writing."""

from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable
import json
from pathlib import Path
from typing import cast

from agent_feed import __version__
from agent_feed.models import VerificationProfile, WriteAction
from agent_feed.project_settings import metadata_data
from agent_feed.session_schema import render_session_schema
from agent_feed.verification_profiles import verification_context


def standard_template_root() -> Traversable:
    packaged_root = resources.files("agent_feed").joinpath("templates/standard")
    if packaged_root.is_dir():
        return packaged_root

    source_root = Path(__file__).resolve().parent / "templates" / "standard"
    return cast(Traversable, source_root)


def walk_templates(root: Traversable, prefix: Path | None = None) -> list[tuple[Path, Traversable]]:
    rel_prefix = prefix or Path()
    files: list[tuple[Path, Traversable]] = []
    for child in root.iterdir():
        if child.name in {".DS_Store", "__pycache__"}:
            continue
        child_rel = rel_prefix / child.name
        if child.is_dir():
            files.extend(walk_templates(child, child_rel))
        elif child.is_file():
            files.append((child_rel, child))
    return files


def read_template(path: Traversable, context: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def render_metadata_template(
    target: Path,
    project_name: str,
    verification_profile: VerificationProfile,
) -> str:
    return (
        json.dumps(
            metadata_data(
                project_name=project_name,
                verification_profile=verification_profile,
                current_metadata=read_metadata_file(target),
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def canonical_write_plan(
    target: Path,
    project_name: str,
    verification_profile: VerificationProfile,
) -> list[tuple[Path, str]]:
    context = {
        "AGENT_FEED_VERSION": __version__,
        "PROJECT_NAME": project_name,
        "VERIFICATION_PROFILE": verification_profile.value,
        **verification_context(verification_profile),
    }
    plan: list[tuple[Path, str]] = []
    for rel_path, template_file in sorted(
        walk_templates(standard_template_root()), key=lambda item: str(item[0])
    ):
        content = (
            render_metadata_template(target, project_name, verification_profile)
            if rel_path == Path(".agents/agent-feed.json")
            else render_session_schema(target)
            if rel_path == Path(".agents/session-state/schema.json")
            else read_template(template_file, context)
        )
        plan.append((target / rel_path, content))
    return plan


def read_metadata_file(target: Path) -> dict[str, object]:
    path = target / ".agents/agent-feed.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def write_text(path: Path, content: str, *, dry_run: bool, force: bool) -> WriteAction:
    if path.exists() and not force:
        return WriteAction(path=path, action="skip", detail="already exists")

    action = "update" if path.exists() else "create"
    if dry_run:
        return WriteAction(path=path, action=f"would {action}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if path.suffix == ".sh":
        path.chmod(0o755)
    return WriteAction(path=path, action=action)
