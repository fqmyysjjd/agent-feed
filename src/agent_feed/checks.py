"""Protocol checks for Agent Feed projects."""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_feed.adapters import claude, codex, cursor
from agent_feed.models import Check, CheckReport, ProjectStatus

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
AGENTS_PATH_PATTERN = re.compile(r"\.agents/[A-Za-z0-9_.*/<>-]+")


def run_checks(root: Path, checks: tuple[Check, ...]) -> CheckReport:
    report = CheckReport(target=root, checks=checks)
    for check in checks:
        if check == Check.STRUCTURE:
            report.errors.extend(validate_structure(root))
        elif check == Check.SKILLS:
            report.errors.extend(validate_skills(root))
        elif check == Check.REFERENCES:
            report.errors.extend(validate_references_and_indexes(root))
        elif check == Check.SESSION:
            report.errors.extend(validate_session_state_files(root))
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
    codex_errors, codex_warnings = codex.check(root)
    claude_errors, claude_warnings = claude.check(root)
    cursor_errors, cursor_warnings = cursor.check(root)
    warnings = [*codex_warnings, *claude_warnings, *cursor_warnings]
    errors = [*canonical_errors, *codex_errors, *claude_errors, *cursor_errors]
    return ProjectStatus(
        target=root,
        canonical_installed=not canonical_errors,
        codex_ready=not codex_errors,
        claude_ready=not claude_errors,
        cursor_ready=not cursor_errors,
        legacy_codex_mirror=(root / ".codex/skills").exists(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_structure(root: Path) -> list[str]:
    required_paths = [
        "AGENTS.md",
        ".agents/README.md",
        ".agents/rules/outcome-boundary.md",
        ".agents/rules/decision-gates.md",
        ".agents/rules/context-loading.md",
        ".agents/rules/session-state.md",
        ".agents/rules/testing-gates.md",
        ".agents/rules/development-workflow.md",
        ".agents/rules/review-gates.md",
        ".agents/project/README.md",
        ".agents/project/verification-profile.md",
        ".agents/domain/README.md",
        ".agents/skills",
        ".agents/scripts/check-agent-assets.sh",
        ".agents/scripts/sync-agent-assets.sh",
        ".agents/scripts/verify-agent-dev.sh",
    ]
    return [
        f"missing required path: {rel_path}"
        for rel_path in required_paths
        if not (root / rel_path).exists()
    ]


def validate_scripts(root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path in [
        ".agents/scripts/check-agent-assets.sh",
        ".agents/scripts/sync-agent-assets.sh",
        ".agents/scripts/verify-agent-dev.sh",
    ]:
        path = root / rel_path
        if not path.exists():
            errors.append(f"missing script: {rel_path}")
        elif not path.stat().st_mode & 0o111:
            errors.append(f"script is not executable: {rel_path}")
    return errors


def validate_skills(root: Path) -> list[str]:
    errors: list[str] = []
    skill_root = root / ".agents/skills"
    if not skill_root.exists():
        return ["missing .agents/skills"]

    for skill_file in sorted(skill_root.glob("*/SKILL.md")):
        skill_name = skill_file.parent.name
        frontmatter_name = read_skill_name(skill_file)
        if frontmatter_name != skill_name:
            errors.append(
                f"{skill_file}: frontmatter name must match directory name "
                f"({frontmatter_name!r} != {skill_name!r})"
            )
        if not SKILL_NAME_PATTERN.match(skill_name):
            errors.append(f"{skill_file}: skill name must be lowercase kebab-case")
        if len(skill_name.split("-")) > 3:
            errors.append(f"{skill_file}: skill name must be at most three words")
    return errors


def read_skill_name(skill_file: Path) -> str:
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("name: "):
            return line.removeprefix("name: ").strip()
    return ""


def validate_references_and_indexes(root: Path) -> list[str]:
    errors: list[str] = []
    skip_parts = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "build",
        "dist",
        "node_modules",
        "__pycache__",
    }
    optional_paths = {".agents/session-state/current.json"}

    for markdown_file in sorted(root.rglob("*.md")):
        rel_path = markdown_file.relative_to(root)
        if any(part in skip_parts for part in rel_path.parts):
            continue
        text = markdown_file.read_text(encoding="utf-8")
        for match in AGENTS_PATH_PATTERN.findall(text):
            path_text = match.rstrip(".,。)，):")
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
        for project_file in sorted((root / ".agents/project").glob("*.md")):
            if project_file.name != "README.md" and project_file.name not in project_readme_text:
                errors.append(f".agents/project/README.md does not list {project_file.name}")

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


def validate_session_state_files(root: Path) -> list[str]:
    errors: list[str] = []
    state_root = root / ".agents/session-state"
    if not state_root.exists():
        return errors

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
            validate_session_state(state_file, data, errors)

    return errors


def validate_session_state(path: Path, data: object, errors: list[str]) -> None:
    obj = require_object(path, data, errors)
    if obj is None:
        return

    required = [
        "schema_version",
        "session_id",
        "conversation_identity",
        "continuity",
        "created_at",
        "updated_at",
        "repository",
        "purpose",
        "topics",
    ]
    require_keys(path, obj, required, errors)
    if obj.get("schema_version") != 2:
        errors.append(f"{path}: schema_version must be 2")

    identity = require_nested_object(path, obj, "conversation_identity", errors)
    if identity is not None:
        require_keys(
            path, identity, ["source", "external_thread_id", "session_alias", "resume_hint"], errors
        )

    continuity = require_nested_object(path, obj, "continuity", errors)
    if continuity is not None:
        require_keys(
            path,
            continuity,
            [
                "current_user_goal",
                "active_task_boundary",
                "active_topic_ids",
                "last_handoff_summary",
                "next_required_action",
            ],
            errors,
        )
        require_string_list(path, continuity, "active_topic_ids", errors)

    topics = obj.get("topics")
    if not isinstance(topics, list):
        errors.append(f"{path}: topics must be a list")
        return

    topic_ids: set[str] = set()
    for index, topic in enumerate(topics):
        if not isinstance(topic, dict):
            errors.append(f"{path}: topics[{index}] must be an object")
            continue
        require_keys(
            path,
            topic,
            [
                "topic_id",
                "title",
                "status",
                "context",
                "conclusion",
                "next_action",
                "blocking_questions",
                "related_files",
                "updated_at",
            ],
            errors,
            prefix=f"topics[{index}]",
        )
        if topic.get("status") not in {"active", "blocked", "ready_for_action"}:
            errors.append(f"{path}: topics[{index}].status is invalid")
        topic_id = topic.get("topic_id")
        if isinstance(topic_id, str):
            if topic_id in topic_ids:
                errors.append(f"{path}: duplicate topic_id {topic_id}")
            topic_ids.add(topic_id)
        require_string_list(path, topic, "blocking_questions", errors, prefix=f"topics[{index}]")
        require_string_list(path, topic, "related_files", errors, prefix=f"topics[{index}]")

    if continuity is not None:
        active_topic_ids = continuity.get("active_topic_ids")
        if isinstance(active_topic_ids, list):
            for topic_id in active_topic_ids:
                if isinstance(topic_id, str) and topic_id not in topic_ids:
                    errors.append(f"{path}: continuity.active_topic_ids references missing topic {topic_id}")


def validate_current_session_registry(
    path: Path, data: object, errors: list[str], root: Path
) -> None:
    obj = require_object(path, data, errors)
    if obj is None:
        return

    require_keys(
        path,
        obj,
        ["schema_version", "updated_at", "repository", "active_session_ids", "sessions"],
        errors,
    )
    if obj.get("schema_version") != 2:
        errors.append(f"{path}: schema_version must be 2")
    require_string_list(path, obj, "active_session_ids", errors)
    sessions = obj.get("sessions")
    if not isinstance(sessions, list):
        errors.append(f"{path}: sessions must be a list")
        return

    session_ids: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            errors.append(f"{path}: sessions[{index}] must be an object")
            continue
        require_keys(
            path,
            session,
            [
                "session_id",
                "session_file",
                "conversation_identity",
                "current_user_goal",
                "active_topic_ids",
                "updated_at",
            ],
            errors,
            prefix=f"sessions[{index}]",
        )
        require_string_list(path, session, "active_topic_ids", errors, prefix=f"sessions[{index}]")
        session_id = session.get("session_id")
        if isinstance(session_id, str):
            if session_id in session_ids:
                errors.append(f"{path}: duplicate sessions[{index}].session_id {session_id}")
            session_ids.add(session_id)

        identity = require_nested_object(
            path, session, "conversation_identity", errors
        )
        if identity is not None:
            require_keys(
                path,
                identity,
                ["source", "external_thread_id", "session_alias", "resume_hint"],
                errors,
                prefix=f"sessions[{index}].conversation_identity",
            )

        session_file = session.get("session_file")
        if not isinstance(session_file, str) or not session_file:
            errors.append(f"{path}: sessions[{index}].session_file must be a non-empty string")
            continue
        session_path = Path(session_file)
        resolved_session_path = session_path if session_path.is_absolute() else root / session_path
        if not resolved_session_path.exists():
            errors.append(
                f"{path}: sessions[{index}].session_file does not exist: {session_file}"
            )

    active_session_ids = obj.get("active_session_ids")
    if isinstance(active_session_ids, list):
        for session_id in active_session_ids:
            if isinstance(session_id, str) and session_id not in session_ids:
                errors.append(f"{path}: active_session_ids references missing session {session_id}")


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
