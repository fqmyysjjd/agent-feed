"""Template rendering and file writing."""

from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from agent_feed import __version__
from agent_feed.models import VerificationProfile, WriteAction
from agent_feed.verification_profiles import verification_context


def standard_template_root() -> Traversable:
    return resources.files("agent_feed").joinpath("templates/standard")


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


def canonical_write_plan(
    target: Path,
    project_name: str,
    verification_profile: VerificationProfile,
) -> list[tuple[Path, str]]:
    context = {
        "AGENT_FEED_VERSION": __version__,
        "PROJECT_NAME": project_name,
        **verification_context(verification_profile),
    }
    plan: list[tuple[Path, str]] = []
    for rel_path, template_file in sorted(
        walk_templates(standard_template_root()), key=lambda item: str(item[0])
    ):
        plan.append((target / rel_path, read_template(template_file, context)))
    return plan


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
