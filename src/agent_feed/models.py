"""Shared models for Agent Feed commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Client(StrEnum):
    CODEX = "codex"
    CLAUDE = "claude"
    CURSOR = "cursor"


class Check(StrEnum):
    STRUCTURE = "structure"
    CONFIG = "config"
    SKILLS = "skills"
    REFERENCES = "references"
    SESSION = "session"
    SCRIPTS = "scripts"
    CODEX = "codex"
    CLAUDE = "claude"
    CURSOR = "cursor"


class VerificationProfile(StrEnum):
    PYTHON = "python"
    NODE = "node"
    CUSTOM = "custom"
    NONE = "none"


CLIENTS = tuple(Client)
DEFAULT_CLIENTS = CLIENTS
CHECKS = tuple(Check)
DEFAULT_CHECKS = CHECKS
VERIFICATION_PROFILES = tuple(VerificationProfile)
DEFAULT_VERIFICATION_PROFILE = VerificationProfile.PYTHON


@dataclass(frozen=True)
class WriteAction:
    path: Path
    action: str
    detail: str = ""
    diff: str = ""
    persistent: bool = False

    @property
    def severity(self) -> str:
        if self.action in {"blocked", "review"}:
            return "warning"
        if self.action.startswith("would"):
            return "preview"
        if self.action in {"skip"}:
            return "neutral"
        return "success"


@dataclass
class CheckReport:
    target: Path
    checks: tuple[Check, ...]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class ProjectStatus:
    target: Path
    canonical_installed: bool
    codex_ready: bool
    claude_ready: bool
    cursor_ready: bool
    legacy_codex_mirror: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
