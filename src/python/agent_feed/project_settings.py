"""Project-level Agent Feed settings stored in .agents/agent-feed.json."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_feed import __version__
from agent_feed.models import VerificationProfile

DEFAULT_SESSION_MAX_CARRY_FORWARDS = 7
DEFAULT_SKILL_SOURCE = "unknow"
DEFAULT_SKILL_TRUST = "custom"
VALID_DEFAULT_SKILL_TRUST = {"reviewed", "custom"}
DEFAULT_CLAUDE_REQUIRED_SNIPPETS = (
    "@AGENTS.md",
    ".claude/skills",
    ".agents/",
)


@dataclass(frozen=True)
class SessionStateSettings:
    max_carry_forwards: int = DEFAULT_SESSION_MAX_CARRY_FORWARDS


@dataclass(frozen=True)
class SkillSettings:
    default_import_source: str = DEFAULT_SKILL_SOURCE
    default_import_trust: str = DEFAULT_SKILL_TRUST


@dataclass(frozen=True)
class ClaudeSettings:
    required_snippets: tuple[str, ...] = DEFAULT_CLAUDE_REQUIRED_SNIPPETS


@dataclass(frozen=True)
class AgentFeedSettings:
    session_state: SessionStateSettings = SessionStateSettings()
    skills: SkillSettings = SkillSettings()
    claude: ClaudeSettings = ClaudeSettings()


def default_settings_data() -> dict[str, Any]:
    return {
        "session_state": {
            "max_carry_forwards": DEFAULT_SESSION_MAX_CARRY_FORWARDS,
        },
        "skills": {
            "default_import_source": DEFAULT_SKILL_SOURCE,
            "default_import_trust": DEFAULT_SKILL_TRUST,
        },
        "claude": {
            "required_snippets": list(DEFAULT_CLAUDE_REQUIRED_SNIPPETS),
        },
    }


def metadata_data(
    *,
    project_name: str,
    verification_profile: VerificationProfile,
    current_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_metadata = current_metadata or {}
    current_settings = current_metadata.get("settings")
    settings = merge_settings(current_settings if isinstance(current_settings, dict) else {})
    return {
        "schema_version": 1,
        "agent_feed_version": __version__,
        "template": "standard",
        "project_name": project_name,
        "verification_profile": verification_profile.value,
        "settings": settings,
        "managed_paths": [
            "AGENTS.md",
            ".agents/README.md",
            ".agents/agent-feed.json",
            ".agents/rules/",
            ".agents/skills/",
            ".agents/scripts/",
            ".agents/agents/README.md",
            ".agents/session-state/README.md",
            ".agents/session-state/schema.json",
            ".agents/session-state/.gitignore",
        ],
        "user_maintained_paths": [
            ".agents/project/",
            ".agents/domain/",
        ],
    }


def merge_settings(overrides: dict[str, Any]) -> dict[str, Any]:
    merged = default_settings_data()

    session_state = overrides.get("session_state")
    if isinstance(session_state, dict):
        max_carry = session_state.get("max_carry_forwards")
        if isinstance(max_carry, int) and max_carry >= 1:
            merged["session_state"]["max_carry_forwards"] = max_carry

    skills = overrides.get("skills")
    if isinstance(skills, dict):
        source = skills.get("default_import_source")
        if isinstance(source, str) and source.strip():
            merged["skills"]["default_import_source"] = source.strip()

        trust = skills.get("default_import_trust")
        if isinstance(trust, str) and trust.strip() and trust.strip() in VALID_DEFAULT_SKILL_TRUST:
            merged["skills"]["default_import_trust"] = trust.strip()

    claude = overrides.get("claude")
    if isinstance(claude, dict):
        snippets = claude.get("required_snippets")
        if isinstance(snippets, list) and snippets:
            normalized = [item for item in snippets if isinstance(item, str) and item]
            if normalized:
                merged["claude"]["required_snippets"] = normalized

    return merged


def read_project_settings(root: Path) -> AgentFeedSettings:
    from agent_feed.upgrade import read_metadata

    return settings_from_metadata(read_metadata(root))


def settings_from_metadata(metadata: dict[str, Any]) -> AgentFeedSettings:
    settings = metadata.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}

    session_state_raw = object_value(settings, "session_state")
    max_carry_forwards = int_value(
        session_state_raw,
        "max_carry_forwards",
        DEFAULT_SESSION_MAX_CARRY_FORWARDS,
    )

    skills_raw = object_value(settings, "skills")
    default_import_source = str_value(
        skills_raw,
        "default_import_source",
        DEFAULT_SKILL_SOURCE,
    )
    default_import_trust = str_value(
        skills_raw,
        "default_import_trust",
        DEFAULT_SKILL_TRUST,
    )
    if default_import_trust not in VALID_DEFAULT_SKILL_TRUST:
        default_import_trust = DEFAULT_SKILL_TRUST

    claude_raw = object_value(settings, "claude")
    required_snippets = string_tuple_value(
        claude_raw,
        "required_snippets",
        DEFAULT_CLAUDE_REQUIRED_SNIPPETS,
    )

    return AgentFeedSettings(
        session_state=SessionStateSettings(max_carry_forwards=max_carry_forwards),
        skills=SkillSettings(
            default_import_source=default_import_source,
            default_import_trust=default_import_trust,
        ),
        claude=ClaudeSettings(required_snippets=required_snippets),
    )


def metadata_settings_errors(metadata: dict[str, Any], *, label: str) -> list[str]:
    settings = metadata.get("settings", {})
    if settings is None:
        return []
    if not isinstance(settings, dict):
        return [f"{label} settings must be a JSON object"]

    errors: list[str] = []
    session_state = settings.get("session_state")
    if session_state is not None:
        if not isinstance(session_state, dict):
            errors.append(f"{label} settings.session_state must be a JSON object")
        elif "max_carry_forwards" in session_state:
            max_carry = session_state.get("max_carry_forwards")
            if not isinstance(max_carry, int) or max_carry < 1:
                errors.append(
                    f"{label} settings.session_state.max_carry_forwards must be a positive integer"
                )

    skills = settings.get("skills")
    if skills is not None:
        if not isinstance(skills, dict):
            errors.append(f"{label} settings.skills must be a JSON object")
        else:
            if "default_import_source" in skills:
                source = skills.get("default_import_source")
                if not isinstance(source, str) or not source.strip():
                    errors.append(
                        f"{label} settings.skills.default_import_source must be a non-empty string"
                    )
            if "default_import_trust" in skills:
                trust = skills.get("default_import_trust")
                if not isinstance(trust, str) or trust not in VALID_DEFAULT_SKILL_TRUST:
                    allowed = ", ".join(sorted(VALID_DEFAULT_SKILL_TRUST))
                    errors.append(
                        f"{label} settings.skills.default_import_trust must be one of {allowed}"
                    )

    claude = settings.get("claude")
    if claude is not None:
        if not isinstance(claude, dict):
            errors.append(f"{label} settings.claude must be a JSON object")
        elif "required_snippets" in claude:
            snippets = claude.get("required_snippets")
            if not isinstance(snippets, list) or not snippets:
                errors.append(f"{label} settings.claude.required_snippets must be a list")
            elif not all(isinstance(item, str) and item for item in snippets):
                errors.append(
                    f"{label} settings.claude.required_snippets must contain non-empty strings"
                )
    return errors


def object_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def int_value(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key)
    return value if isinstance(value, int) and value >= 1 else default


def str_value(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def string_tuple_value(
    data: dict[str, Any],
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list):
        return default
    strings = tuple(item for item in value if isinstance(item, str) and item)
    return strings or default
