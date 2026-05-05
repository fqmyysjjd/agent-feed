"""Legacy AI instruction backup and migration guidance."""

from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from agent_feed.adapters import claude, cursor
from agent_feed.models import VerificationProfile, WriteAction
from agent_feed.templates import canonical_write_plan


BACKUP_ROOT = Path(".feed-backup")
MIGRATION_GUIDE_NAME = "AI_MIGRATION_GUIDE.md"
MANIFEST_NAME = "manifest.json"

LEGACY_FILE_PATHS = (
    Path("AGENTS.md"),
    Path("AGENTS.local.md"),
    Path("CLAUDE.md"),
    Path(".cursorrules"),
    Path(".cursor/rules/agent-feed.mdc"),
)

LEGACY_DIR_PATHS = (
    Path(".agents"),
    Path(".claude/skills"),
    Path(".codex/skills"),
    Path(".cursor/rules"),
)


@dataclass(frozen=True)
class LegacyAsset:
    rel_path: Path
    kind: str


def backup_legacy_ai_assets(
    target: Path,
    *,
    project_name: str,
    verification_profile: VerificationProfile,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    """Move pre-existing AI instruction assets aside before init writes canonical files."""
    assets, errors = find_legacy_ai_assets(target)
    if errors or not assets:
        return [], errors

    backup_dir = next_backup_dir(target)
    actions: list[WriteAction] = []
    manifest_entries: list[dict[str, str]] = []
    for asset in assets:
        source = target / asset.rel_path
        destination = backup_dir / asset.rel_path
        actions.append(
            WriteAction(
                path=source,
                action="would backup" if dry_run else "backup",
                detail=f"-> {destination.relative_to(target).as_posix()}",
            )
        )
        manifest_entries.append(
            {
                "path": asset.rel_path.as_posix(),
                "kind": asset.kind,
                "destination": destination.relative_to(target).as_posix(),
            }
        )
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            prune_empty_parents(source.parent, stop=target)

    manifest = render_manifest(
        project_name=project_name,
        assets=manifest_entries,
        project_domain_scaffolded=project_domain_scaffolded(
            target,
            project_name=project_name,
            verification_profile=verification_profile,
        ),
    )
    guide = render_migration_guide(manifest)

    actions.extend(
        [
            write_backup_text(
                backup_dir / MANIFEST_NAME,
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                dry_run=dry_run,
            ),
            write_backup_text(
                backup_dir / MIGRATION_GUIDE_NAME,
                guide,
                dry_run=dry_run,
            ),
        ]
    )
    return actions, []


def backup_actions_include(actions: list[WriteAction], rel_path: Path, *, target: Path) -> bool:
    """Return whether a planned backup covers a target-relative path."""
    path = target / rel_path
    return any(
        action.action in {"backup", "would backup"}
        and (action.path == path or is_relative_to(path, action.path))
        for action in actions
    )


def find_legacy_ai_assets(target: Path) -> tuple[list[LegacyAsset], list[str]]:
    assets: list[LegacyAsset] = []
    errors: list[str] = []

    for rel_path in LEGACY_FILE_PATHS:
        path = target / rel_path
        if not path.exists():
            continue
        if not path.is_file():
            errors.append(f"{rel_path.as_posix()} exists but is not a file")
            continue
        if is_generated_adapter(path):
            continue
        assets.append(LegacyAsset(rel_path=rel_path, kind="file"))

    for rel_path in LEGACY_DIR_PATHS:
        path = target / rel_path
        if not path.exists():
            continue
        if not path.is_dir():
            errors.append(f"{rel_path.as_posix()} exists but is not a directory")
            continue
        if not any(path.iterdir()):
            continue
        if rel_path == Path(".claude/skills") and claude.is_managed_skill_mirror(path.parent):
            continue
        assets.append(LegacyAsset(rel_path=rel_path, kind="directory"))

    return dedupe_nested_assets(assets), errors


def dedupe_nested_assets(assets: list[LegacyAsset]) -> list[LegacyAsset]:
    ordered = sorted(assets, key=lambda item: (len(item.rel_path.parts), item.rel_path.as_posix()))
    kept: list[LegacyAsset] = []
    for asset in ordered:
        if any(is_relative_to(asset.rel_path, existing.rel_path) for existing in kept):
            continue
        kept.append(asset)
    return kept


def is_generated_adapter(path: Path) -> bool:
    if path.name == "CLAUDE.md":
        try:
            missing = claude.missing_required_snippets(path, root=path.parent)
        except OSError:
            return False
        return not missing
    if path.name == "agent-feed.mdc":
        return cursor.is_managed_cursor_rule(path)
    return False


def next_backup_dir(target: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = target / BACKUP_ROOT / stamp
    candidate = base
    counter = 2
    while candidate.exists():
        candidate = target / BACKUP_ROOT / f"{stamp}-{counter}"
        counter += 1
    return candidate


def write_backup_text(path: Path, content: str, *, dry_run: bool) -> WriteAction:
    if dry_run:
        return WriteAction(path=path, action="would create", detail="legacy migration record")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return WriteAction(path=path, action="create", detail="legacy migration record")


def prune_empty_parents(path: Path, *, stop: Path) -> None:
    current = path
    while current != stop and is_relative_to(current, stop):
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def project_domain_scaffolded(
    target: Path,
    *,
    project_name: str,
    verification_profile: VerificationProfile,
) -> bool:
    expected = {
        path.relative_to(target): content
        for path, content in canonical_write_plan(target, project_name, verification_profile)
        if path.relative_to(target).parts[:2] in {
            (".agents", "project"),
            (".agents", "domain"),
        }
    }
    for rel_path, expected_content in expected.items():
        path = target / rel_path
        if path.is_file() and path.read_text(encoding="utf-8") != expected_content:
            return False
    return True


def render_manifest(
    *,
    project_name: str,
    assets: list[dict[str, str]],
    project_domain_scaffolded: bool,
) -> dict[str, object]:
    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_name": project_name,
        "purpose": "legacy-ai-instruction-backup",
        "project_domain_scaffolded": project_domain_scaffolded,
        "assets": assets,
        "ai_migration_policy": {
            "target_layers": [".agents/project/", ".agents/domain/"],
            "must_preserve": [
                "decisive project AI workflows",
                "architecture and source layout boundaries",
                "verification and review requirements",
                "security, persistence, trace, and release constraints",
                "stable domain concepts, contracts, and source-of-truth ownership",
            ],
            "must_stop_for_user": [
                "a decisive legacy rule conflicts with Agent Feed generic workflow",
                "a legacy rule is redundant but removing it could affect the AI development loop",
                "evidence is insufficient to decide whether a legacy rule still applies",
                "project/domain files are already user-maintained instead of scaffold-only",
            ],
        },
    }


def render_migration_guide(manifest: dict[str, object]) -> str:
    assets = manifest.get("assets")
    asset_entries = assets if isinstance(assets, list) else []
    asset_lines = "\n".join(
        f"- `{entry['path']}` -> `{entry['destination']}`"
        for entry in asset_entries
        if isinstance(entry, dict)
    )
    scaffold_text = (
        "Project/domain files appear to be scaffold-only, so AI may migrate supported facts "
        "directly into `.agents/project/` and `.agents/domain/`."
        if manifest.get("project_domain_scaffolded")
        else "Project/domain files appear user-maintained, so AI must not overwrite them. "
        "Produce a migration report and ask before editing."
    )
    return f"""# Legacy AI Instruction Migration Guide

Agent Feed moved pre-existing AI instruction assets into this backup before installing
the canonical protocol.

## Backed Up Assets

{asset_lines}

## Migration Policy

{scaffold_text}

AI assistants must follow these rules before using or migrating the backup:

1. Read every backed-up file that can affect AI development behavior.
2. Preserve every decisive workflow, project rule, verification rule, security rule,
   architecture boundary, domain concept, contract, and source-of-truth rule.
3. Move reusable generic guidance only when it is not already covered by Agent Feed.
4. Prefer `.agents/project/` for repository-specific engineering constraints.
5. Prefer `.agents/domain/` for stable concepts, contracts, and ownership facts.
6. Do not copy stale, duplicated, or conflicting instructions blindly.
7. Stop and ask the user when removing, rewriting, or merging a legacy rule could
   affect the AI development loop or future project results.
8. Record uncertain items as assumptions instead of presenting them as facts.

After migration, run `sh .agents/scripts/verify-agent-dev.sh docs`.
"""


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
