"""Protocol checks for Agent Feed projects."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from agent_feed import __version__
from agent_feed.adapters import claude, codex, cursor
from agent_feed.asset_trust import asset_trust_errors
from agent_feed.config import check_config
from agent_feed.install_source import is_older_version
from agent_feed.models import Check, CheckReport, ProjectStatus
from agent_feed.project_settings import (
    DEFAULT_SKILL_TRUST,
    metadata_settings_errors,
    read_project_settings,
)
from agent_feed.skill_index import (
    VALID_SKILL_TRUST,
    read_frontmatter,
    skill_index_errors,
)
from agent_feed.upgrade import installed_version

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
AGENTS_PATH_PATTERN = re.compile(r"\.agents/[A-Za-z0-9_.*/<>-]+")
SESSION_CARRY_FORWARD_TYPES = {"decision", "constraint", "blocker", "handoff"}
SESSION_EXPIRY_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2})?(?:Z|[+-][0-9]{2}:?[0-9]{2})?)?\b"
)
RECALL_INDEX_REQUIRED_TERMS = ("owns", "read when", "evidence")
RECALL_FILE_REQUIRED_HEADINGS = ("## Owns", "## Read When", "## Evidence")
# Files that the standard template ships and is responsible for keeping
# structured. User-authored files under .agents/project/ and .agents/domain/
# only need to be listed in the README index so the AI can route to them.
STANDARD_TEMPLATE_PROJECT_FILES = frozenset(
    {"architecture-boundaries.md", "milestones.md", "project-structure.md"}
)
STANDARD_TEMPLATE_DOMAIN_FILES = frozenset(
    {"concepts.md", "contracts.md", "source-of-truth.md"}
)


def run_checks(root: Path, checks: tuple[Check, ...]) -> CheckReport:
    report = CheckReport(target=root, checks=checks)
    for check in checks:
        if check == Check.STRUCTURE:
            report.errors.extend(validate_structure(root))
        elif check == Check.CONFIG:
            config_report = check_config(root)
            report.errors.extend(config_report.errors)
            report.warnings.extend(config_report.warnings)
        elif check == Check.SKILLS:
            report.errors.extend(validate_skills(root))
        elif check == Check.REFERENCES:
            report.errors.extend(validate_references_and_indexes(root))
        elif check == Check.SESSION:
            errors, warnings = validate_session_state_report(root)
            report.errors.extend(errors)
            report.warnings.extend(warnings)
        elif check == Check.SCRIPTS:
            report.errors.extend(validate_scripts(root))
        elif check == Check.CODEX:
            errors, warnings = codex.check(root)
            report.errors.extend(errors)
            report.warnings.extend(warnings)
        elif check == Check.CLAUDE:
            errors, warnings = claude.check(root)
            report.errors.extend(errors)
            report.warnings.extend(warnings)
        elif check == Check.CURSOR:
            errors, warnings = cursor.check(root)
            report.errors.extend(errors)
            report.warnings.extend(warnings)
    return report


def collect_status(root: Path) -> ProjectStatus:
    canonical_errors = validate_structure(root)
    trust_errors = asset_trust_errors(root)
    skill_errors, skill_warnings = validate_skills_report(root, include_trust=False)
    codex_errors, codex_warnings = codex.check(root)
    configured = configured_clients(root)
    if "claude" in configured:
        claude_errors, claude_warnings = claude.check(root)
    else:
        claude_errors, claude_warnings = [], []
    if "cursor" in configured:
        cursor_errors, cursor_warnings = cursor.check(root)
    else:
        cursor_errors, cursor_warnings = [], []
    warnings = [
        *downgrade_warnings(root),
        *skill_warnings,
        *codex_warnings,
        *claude_warnings,
        *cursor_warnings,
    ]
    errors = [
        *canonical_errors,
        *trust_errors,
        *skill_errors,
        *codex_errors,
        *claude_errors,
        *cursor_errors,
    ]
    return ProjectStatus(
        target=root,
        canonical_installed=not canonical_errors and not trust_errors,
        codex_ready=not codex_errors,
        claude_ready="claude" in configured and not claude_errors,
        cursor_ready="cursor" in configured and not cursor_errors,
        legacy_codex_mirror=(root / ".codex/skills").exists(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def downgrade_warnings(root: Path) -> list[str]:
    version = installed_version(root)
    if not version or not is_older_version(__version__, version):
        return []
    return [
        (
            f"Downgrade risk: project was managed by Agent Feed {version}, "
            f"but this CLI is {__version__}. Update the CLI before running upgrade."
        )
    ]


def configured_clients(root: Path) -> set[str]:
    configured = {"codex"}
    if (root / "CLAUDE.md").exists() or (root / ".claude/skills").exists():
        configured.add("claude")
    if (root / ".cursor/rules/agent-feed.mdc").exists():
        configured.add("cursor")
    return configured


def validate_structure(root: Path) -> list[str]:
    required_paths = [
        "AGENTS.md",
        ".agents/agent-feed.json",
        ".agents/README.md",
        ".agents/rules/outcome-boundary.md",
        ".agents/rules/decision-gates.md",
        ".agents/rules/context-loading.md",
        ".agents/rules/session-state.md",
        ".agents/rules/testing-gates.md",
        ".agents/rules/engineering-architecture.md",
        ".agents/rules/development-workflow.md",
        ".agents/rules/review-gates.md",
        ".agents/project/README.md",
        ".agents/project/verification-commands.sh",
        ".agents/domain/README.md",
        ".agents/skills",
        ".agents/skills/README.md",
        ".agents/scripts/check-agent-assets.sh",
        ".agents/scripts/check-agent-trust.sh",
        ".agents/scripts/index-skills.sh",
        ".agents/scripts/sync-agent-assets.sh",
        ".agents/scripts/verify-agent-dev.sh",
    ]
    errors = [
        f"missing required path: {rel_path}"
        for rel_path in required_paths
        if not (root / rel_path).exists()
    ]
    arch_rule = ".agents/rules/engineering-architecture.md"
    if any(error.endswith(arch_rule) for error in errors) and (root / ".agents/agent-feed.json").exists():
        errors.append(
            f"hint: {arch_rule} was added in a newer Agent Feed release; "
            "run `agent-feed upgrade` to install it before re-running checks."
        )
    return errors + validate_agent_feed_metadata(root)


def validate_agent_feed_metadata(root: Path) -> list[str]:
    metadata_file = root / ".agents/agent-feed.json"
    if not metadata_file.exists():
        return []
    try:
        data = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f".agents/agent-feed.json invalid JSON at line {exc.lineno}, column {exc.colno}"]
    if not isinstance(data, dict):
        return [".agents/agent-feed.json must be a JSON object"]

    errors: list[str] = []
    for key in [
        "schema_version",
        "agent_feed_version",
        "template",
        "project_name",
        "verification_profile",
    ]:
        if key not in data:
            errors.append(f".agents/agent-feed.json missing {key}")
    if data.get("schema_version") != 1:
        errors.append(".agents/agent-feed.json schema_version must be 1")
    if data.get("template") != "standard":
        errors.append(".agents/agent-feed.json template must be standard")
    if "verification_profile" in data:
        from agent_feed.models import VerificationProfile

        try:
            VerificationProfile(str(data["verification_profile"]).strip().lower())
        except ValueError:
            allowed = ", ".join(profile.value for profile in VerificationProfile)
            errors.append(f".agents/agent-feed.json verification_profile must be one of {allowed}")
    errors.extend(metadata_settings_errors(data, label=".agents/agent-feed.json"))
    return errors


def validate_scripts(root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path in [
        ".agents/scripts/check-agent-assets.sh",
        ".agents/scripts/check-agent-trust.sh",
        ".agents/scripts/index-skills.sh",
        ".agents/scripts/sync-agent-assets.sh",
        ".agents/scripts/verify-agent-dev.sh",
    ]:
        path = root / rel_path
        if not path.exists():
            errors.append(f"missing script: {rel_path}")
        elif os.name != "nt" and not path.stat().st_mode & 0o111:
            errors.append(f"script is not executable: {rel_path}")
    errors.extend(asset_trust_errors(root, kinds={"script"}))
    return errors


def validate_skills(root: Path) -> list[str]:
    errors, _warnings = validate_skills_report(root)
    return errors


def validate_skills_report(
    root: Path, *, include_trust: bool = True
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    skill_root = root / ".agents/skills"
    if not skill_root.exists():
        return ["missing .agents/skills"], warnings

    for skill_file in sorted(skill_root.glob("*/SKILL.md")):
        skill_name = skill_file.parent.name
        frontmatter = read_frontmatter(skill_file)
        frontmatter_name = frontmatter.get("name", "")
        if frontmatter_name != skill_name:
            errors.append(
                f"{skill_file}: frontmatter name must match directory name "
                f"({frontmatter_name!r} != {skill_name!r})"
            )
        if not SKILL_NAME_PATTERN.match(skill_name):
            errors.append(f"{skill_file}: skill name must be lowercase kebab-case")
        if len(skill_name.split("-")) > 3:
            errors.append(f"{skill_file}: skill name must be at most three words")
        for key in ("description", "source", "trust"):
            if not frontmatter.get(key):
                errors.append(f"{skill_file}: frontmatter missing {key}")
        if frontmatter.get("trust", DEFAULT_SKILL_TRUST) not in VALID_SKILL_TRUST:
            errors.append(f"{skill_file}: trust must be one of core, reviewed, custom")
    if include_trust:
        errors.extend(asset_trust_errors(root, kinds={"skill"}))
    errors.extend(skill_index_errors(root))
    return errors, warnings


def validate_references_and_indexes(root: Path) -> list[str]:
    errors: list[str] = []
    skip_parts = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".feed-backup",
        "build",
        "dist",
        "node_modules",
        "__pycache__",
    }
    optional_paths = {".agents/session-state/current.json"}
    reference_roots = {
        Path("AGENTS.md"),
        Path("CLAUDE.md"),
        Path(".cursor/rules/agent-feed.mdc"),
        Path(".agents"),
    }

    for markdown_file in active_reference_markdown_files(root, reference_roots):
        rel_path = markdown_file.relative_to(root)
        if any(part in skip_parts for part in rel_path.parts):
            continue
        text = markdown_file.read_text(encoding="utf-8")
        for match in AGENTS_PATH_PATTERN.findall(text):
            path_text = match.rstrip(".,):")
            if any(token in path_text for token in ("*", "<", ">", "{{", "}}", "YYYYMMDD")):
                continue
            if path_text in optional_paths:
                continue
            if not (root / path_text).exists():
                errors.append(f"{rel_path}: missing referenced path {path_text}")

    agents_readme = root / ".agents/README.md"
    if agents_readme.exists():
        agents_readme_text = agents_readme.read_text(encoding="utf-8")
        for rule_file in sorted((root / ".agents/rules").glob("*.md")):
            if rule_file.name not in agents_readme_text:
                errors.append(f".agents/README.md does not list rule {rule_file.name}")

    project_readme = root / ".agents/project/README.md"
    if project_readme.exists():
        project_readme_text = project_readme.read_text(encoding="utf-8")
        for heading in [
            "## Boundary",
            "## Maintenance Contract",
            "## Current Project Constraints",
        ]:
            if heading not in project_readme_text:
                errors.append(f".agents/project/README.md missing required heading {heading}")
        errors.extend(
            validate_recall_index(
                root=root,
                directory=".agents/project",
                readme_text=project_readme_text,
                strict_files=STANDARD_TEMPLATE_PROJECT_FILES,
            )
        )

    domain_readme = root / ".agents/domain/README.md"
    if domain_readme.exists():
        domain_readme_text = domain_readme.read_text(encoding="utf-8")
        for heading in [
            "## Core Concepts",
            "## Use Cases",
        ]:
            if heading not in domain_readme_text:
                errors.append(f".agents/domain/README.md missing required heading {heading}")
        errors.extend(
            validate_recall_index(
                root=root,
                directory=".agents/domain",
                readme_text=domain_readme_text,
                strict_files=STANDARD_TEMPLATE_DOMAIN_FILES,
            )
        )

    agents_md = root / "AGENTS.md"
    if agents_md.exists():
        agents_md_text = agents_md.read_text(encoding="utf-8")
        for required_rule in [
            ".agents/rules/outcome-boundary.md",
            ".agents/rules/decision-gates.md",
            ".agents/rules/context-loading.md",
            ".agents/rules/session-state.md",
            ".agents/rules/testing-gates.md",
        ]:
            if required_rule not in agents_md_text:
                errors.append(f"AGENTS.md does not reference required rule {required_rule}")

    return errors


def validate_recall_index(
    *,
    root: Path,
    directory: str,
    readme_text: str,
    strict_files: frozenset[str],
) -> list[str]:
    """Validate the README recall index for ``directory``.

    ``strict_files`` lists template-shipped files that must use the structured
    table-row entry and the standard ``## Owns`` / ``## Read When`` /
    ``## Evidence`` headings. Files outside this set are user-authored: they
    only need to be listed in the README so the AI can route to them.
    """

    errors: list[str] = []
    readme_lower = readme_text.lower()
    for term in RECALL_INDEX_REQUIRED_TERMS:
        if term not in readme_lower:
            errors.append(f"{directory}/README.md missing recall index term {term!r}")

    for indexed_file in sorted((root / directory).glob("*.md")):
        if indexed_file.name == "README.md":
            continue
        index_entry = recall_index_entry(readme_text, indexed_file.name)
        if index_entry is None:
            errors.append(f"{directory}/README.md does not list {indexed_file.name}")
            continue
        if indexed_file.name not in strict_files:
            continue
        if not recall_index_entry_is_structured(index_entry):
            errors.append(
                f"{directory}/README.md entry for {indexed_file.name} must be a "
                "table row with File, Owns, Read when, and Evidence expectation"
            )
        file_text = indexed_file.read_text(encoding="utf-8")
        for heading in RECALL_FILE_REQUIRED_HEADINGS:
            if heading not in file_text:
                errors.append(f"{directory}/{indexed_file.name} missing required heading {heading}")
    return errors


def recall_index_entry(readme_text: str, file_name: str) -> str | None:
    for line in readme_text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") or stripped.startswith("- ")):
            continue
        if f"`{file_name}`" in stripped:
            return line.strip()
    return None


def recall_index_entry_is_structured(line: str) -> bool:
    if not line.startswith("|") or not line.endswith("|"):
        return False
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    return len(cells) >= 4 and all(cells[:4])


def active_reference_markdown_files(root: Path, reference_roots: set[Path]) -> list[Path]:
    files: list[Path] = []
    for reference_root in sorted(reference_roots):
        path = root / reference_root
        if path.is_file() and path.suffix == ".md":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def validate_session_state_files(root: Path) -> list[str]:
    errors, _warnings = validate_session_state_report(root)
    return errors


def validate_session_state_report(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    state_root = root / ".agents/session-state"
    if not state_root.exists():
        return errors, warnings

    for state_file in sorted(state_root.glob("*.json")):
        if state_file.name == "schema.json":
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{state_file}: invalid JSON at line {exc.lineno}, column {exc.colno}")
            continue

        if state_file.name == "current.json":
            validate_current_session_registry(state_file, data, errors, root)
        else:
            validate_session_state(state_file, data, errors, warnings)

    return errors, warnings


def validate_session_state(
    path: Path, data: object, errors: list[str], warnings: list[str]
) -> None:
    obj = require_object(path, data, errors)
    if obj is None:
        return

    require_keys(path, obj, ["schema_version", "session", "current_task", "carry_forwards"], errors)
    if obj.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")

    session = require_nested_object(path, obj, "session", errors)
    if session is not None:
        require_keys(path, session, ["id", "label", "updated_at"], errors, prefix="session")
        require_non_empty_string(path, session, "id", errors, prefix="session")
        require_non_empty_string(path, session, "label", errors, prefix="session")
        require_non_empty_string(path, session, "updated_at", errors, prefix="session")
        if "thread_id" in session and not isinstance(session.get("thread_id"), str):
            errors.append(f"{path}: session.thread_id must be a string")
        if "title_history" in session:
            require_string_list(path, session, "title_history", errors, prefix="session")

    current_task = require_nested_object(path, obj, "current_task", errors)
    if current_task is not None:
        for key in ["goal", "current_step", "stop_condition", "next_action"]:
            require_non_empty_string(path, current_task, key, errors, prefix="current_task")

    carry_forwards = obj.get("carry_forwards")
    if not isinstance(carry_forwards, list):
        errors.append(f"{path}: carry_forwards must be a list")
        return

    max_carry_forwards = read_project_settings(
        path.parent.parent.parent
    ).session_state.max_carry_forwards
    if len(carry_forwards) > max_carry_forwards:
        errors.append(f"{path}: carry_forwards must contain at most {max_carry_forwards} items")

    carry_forward_ids: set[str] = set()
    for index, item in enumerate(carry_forwards):
        prefix = f"carry_forwards[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: {prefix} must be an object")
            continue
        require_keys(
            path,
            item,
            ["id", "type", "content", "why_keep", "expires_when", "updated_at"],
            errors,
            prefix=prefix,
        )
        for key in ["id", "type", "content", "why_keep", "expires_when", "updated_at"]:
            require_non_empty_string(path, item, key, errors, prefix=prefix)
        item_type = item.get("type")
        if isinstance(item_type, str) and item_type not in SESSION_CARRY_FORWARD_TYPES:
            allowed = ", ".join(sorted(SESSION_CARRY_FORWARD_TYPES))
            errors.append(f"{path}: {prefix}.type must be one of: {allowed}")
        item_id = item.get("id")
        if isinstance(item_id, str):
            if item_id in carry_forward_ids:
                errors.append(f"{path}: duplicate carry_forwards id {item_id}")
            carry_forward_ids.add(item_id)
        expires_when = item.get("expires_when")
        if isinstance(expires_when, str) and session_expiry_is_past(expires_when):
            item_label = item_id if isinstance(item_id, str) and item_id else str(index)
            warnings.append(
                f"{path}: carry_forwards[{index}] {item_label!r} appears expired "
                f"by expires_when ({expires_when}); clean it or promote it before final handoff"
            )


def session_expiry_is_past(value: str) -> bool:
    match = SESSION_EXPIRY_PATTERN.search(value)
    if match is None:
        return False
    token = match.group(0).replace(" ", "T")
    if len(token) == 10:
        try:
            expiry_date = datetime.fromisoformat(token).date()
        except ValueError:
            return False
        return expiry_date < datetime.now().date()

    try:
        expiry = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None:
        return expiry < datetime.now()
    return expiry.astimezone(timezone.utc) < datetime.now(timezone.utc)


def validate_current_session_registry(
    path: Path, data: object, errors: list[str], root: Path
) -> None:
    obj = require_object(path, data, errors)
    if obj is None:
        return

    require_keys(path, obj, ["schema_version", "updated_at", "sessions"], errors)
    if obj.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    require_non_empty_string(path, obj, "updated_at", errors)

    active_session_file = obj.get("active_session_file")
    active_session_file_value: str | None = None
    if active_session_file is not None:
        if not isinstance(active_session_file, str) or not active_session_file:
            errors.append(f"{path}: active_session_file must be a non-empty string")
        else:
            active_session_file_value = active_session_file
            active_path = Path(active_session_file)
            resolved_active_path = active_path if active_path.is_absolute() else root / active_path
            if not resolved_active_path.exists():
                errors.append(f"{path}: active_session_file does not exist: {active_session_file}")

    sessions = obj.get("sessions")
    if not isinstance(sessions, list):
        errors.append(f"{path}: sessions must be a list")
        return

    session_files: set[str] = set()
    for index, session in enumerate(sessions):
        prefix = f"sessions[{index}]"
        if not isinstance(session, dict):
            errors.append(f"{path}: {prefix} must be an object")
            continue
        require_keys(path, session, ["file", "label", "updated_at"], errors, prefix=prefix)
        for key in ["file", "label", "updated_at"]:
            require_non_empty_string(path, session, key, errors, prefix=prefix)

        session_file = session.get("file")
        if not isinstance(session_file, str) or not session_file:
            continue
        session_path = Path(session_file)
        resolved_session_path = session_path if session_path.is_absolute() else root / session_path
        if not resolved_session_path.exists():
            errors.append(f"{path}: {prefix}.file does not exist: {session_file}")
        if session_file in session_files:
            errors.append(f"{path}: duplicate {prefix}.file {session_file}")
        session_files.add(session_file)

    if active_session_file_value is not None and active_session_file_value not in session_files:
        errors.append(f"{path}: active_session_file is not listed in sessions")


def require_object(path: Path, data: object, errors: list[str]) -> dict[str, object] | None:
    if isinstance(data, dict):
        return data
    errors.append(f"{path}: root must be a JSON object")
    return None


def require_nested_object(
    path: Path, obj: dict[str, object], key: str, errors: list[str]
) -> dict[str, object] | None:
    value = obj.get(key)
    if isinstance(value, dict):
        return value
    errors.append(f"{path}: {key} must be an object")
    return None


def require_keys(
    path: Path,
    obj: dict[str, object],
    keys: list[str],
    errors: list[str],
    *,
    prefix: str = "",
) -> None:
    for key in keys:
        if key not in obj:
            label = f"{prefix}.{key}" if prefix else key
            errors.append(f"{path}: missing {label}")


def require_string_list(
    path: Path,
    obj: dict[str, object],
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
) -> None:
    value = obj.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{path}: {label} must be a list of strings")


def require_non_empty_string(
    path: Path,
    obj: dict[str, object],
    key: str,
    errors: list[str],
    *,
    prefix: str = "",
) -> None:
    value = obj.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value:
        errors.append(f"{path}: {label} must be a non-empty string")
