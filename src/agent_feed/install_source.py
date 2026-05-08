"""Detect Agent Feed install source and check source-specific latest versions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

import httpx

import agent_feed
from agent_feed import __version__


PYPI_PACKAGE = "agent-feed"
NPM_PACKAGE = "@yysjjd/agent-feed"
BREW_FORMULA_URL = (
    "https://raw.githubusercontent.com/fqmyysjjd/homebrew-tap/main/Formula/agent-feed.rb"
)
DEFAULT_TIMEOUT = 2.5


@dataclass(frozen=True)
class InstallSource:
    kind: str
    label: str
    registry: str | None
    update_command: str | None


@dataclass(frozen=True)
class UpdateNotice:
    current_version: str
    latest_version: str
    source: InstallSource


def detect_install_source(
    *,
    env: Mapping[str, str] | None = None,
    executable: Path | None = None,
    package_file: Path | None = None,
) -> InstallSource:
    """Detect the package manager that launched this Agent Feed process."""
    effective_env = env if env is not None else os.environ
    explicit = effective_env.get("AGENT_FEED_INSTALL_SOURCE", "").strip().lower()
    if explicit:
        return source_from_kind(explicit)

    executable = executable or Path(sys.argv[0]).resolve()
    package_file = package_file or agent_feed_package_path()
    candidates = tuple(normalized_path_text(path) for path in (executable, package_file) if path)
    joined = "\n".join(candidates)

    if package_file and is_source_checkout(package_file):
        return source_from_kind("source")
    if "node_modules/@yysjjd/agent-feed" in joined:
        return source_from_kind("npm")
    if "/.local/share/uv/tools/agent-feed/" in joined or "/uv/tools/agent-feed/" in joined:
        return source_from_kind("uv")
    if "/pipx/venvs/agent-feed/" in joined:
        return source_from_kind("pipx")
    if "/cellar/agent-feed/" in joined:
        return source_from_kind("brew")
    return source_from_kind("pypi")


def normalized_path_text(path: Path) -> str:
    return str(path).replace("\\", "/").lower()


def source_from_kind(kind: str) -> InstallSource:
    normalized = kind.strip().lower().replace("_", "-")
    if normalized in {"npm", "node"}:
        return InstallSource(
            kind="npm",
            label="npm",
            registry="npm",
            update_command=f"npm install -g {NPM_PACKAGE}@latest",
        )
    if normalized in {"uv", "uv-tool"}:
        return InstallSource(
            kind="uv",
            label="uv tool",
            registry="pypi",
            update_command=f"uv tool upgrade {PYPI_PACKAGE}",
        )
    if normalized == "pipx":
        return InstallSource(
            kind="pipx",
            label="pipx",
            registry="pypi",
            update_command=f"pipx upgrade {PYPI_PACKAGE}",
        )
    if normalized in {"brew", "homebrew"}:
        return InstallSource(
            kind="brew",
            label="Homebrew",
            registry="brew",
            update_command="brew update && brew upgrade fqmyysjjd/tap/agent-feed",
        )
    if normalized in {"source", "checkout", "dev"}:
        return InstallSource(
            kind="source",
            label="source checkout",
            registry=None,
            update_command=None,
        )
    return InstallSource(
        kind="pypi",
        label="Python package",
        registry="pypi",
        update_command=f"{python_command()} -m pip install --upgrade {PYPI_PACKAGE}",
    )


def agent_feed_package_path() -> Path | None:
    if not agent_feed.__file__:
        return None
    return Path(agent_feed.__file__).resolve()


def is_source_checkout(package_file: Path) -> bool:
    parts = package_file.parts
    if "src" not in parts:
        return False
    for parent in package_file.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src/agent_feed").is_dir():
            return True
    return False


def python_command() -> str:
    executable = Path(sys.executable).name or "python"
    if executable.startswith("python"):
        return executable
    return "python"


def latest_update_notice(
    *,
    current_version: str = __version__,
    source: InstallSource | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> UpdateNotice | None:
    source = source or detect_install_source()
    if source.registry is None:
        return None
    latest = fetch_latest_version(source, timeout=timeout)
    if latest is None:
        return None
    if is_newer_version(latest, current_version):
        return UpdateNotice(current_version=current_version, latest_version=latest, source=source)
    return None


def fetch_latest_version(source: InstallSource, *, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            if source.registry == "npm":
                package = quote(NPM_PACKAGE, safe="")
                response = client.get(f"https://registry.npmjs.org/{package}")
                response.raise_for_status()
                latest = response.json().get("dist-tags", {}).get("latest")
                return latest if isinstance(latest, str) and latest else None
            if source.registry == "pypi":
                response = client.get(f"https://pypi.org/pypi/{PYPI_PACKAGE}/json")
                response.raise_for_status()
                latest = response.json().get("info", {}).get("version")
                return latest if isinstance(latest, str) and latest else None
            if source.registry == "brew":
                response = client.get(BREW_FORMULA_URL)
                response.raise_for_status()
                return parse_brew_formula_version(response.text)
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    return None


def parse_brew_formula_version(formula: str) -> str | None:
    match = re.search(r"agent_feed-([0-9][A-Za-z0-9_.!+-]*)\.tar\.gz", formula)
    if match:
        return match.group(1)
    match = re.search(r"agent-feed(?:/archive/refs/tags/|@|==)v?([0-9][A-Za-z0-9_.!+-]*)", formula)
    return match.group(1) if match else None


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_parts = version_parts(candidate)
    current_parts = version_parts(current)
    if not candidate_parts or not current_parts:
        return False
    width = max(len(candidate_parts), len(current_parts))
    candidate_parts = candidate_parts + (0,) * (width - len(candidate_parts))
    current_parts = current_parts + (0,) * (width - len(current_parts))
    return candidate_parts > current_parts


def version_parts(version: str) -> tuple[int, ...]:
    match = re.match(r"^\s*v?(\d+(?:\.\d+)*)", version)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))
