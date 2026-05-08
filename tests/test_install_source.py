from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx
import pytest

from agent_feed.install_source import (
    InstallSource,
    detect_install_source,
    fetch_latest_version,
    is_newer_version,
    parse_brew_formula_version,
    source_from_kind,
)


def test_detect_install_source_prefers_explicit_env() -> None:
    source = detect_install_source(env={"AGENT_FEED_INSTALL_SOURCE": "npm"})

    assert source.kind == "npm"
    assert source.registry == "npm"
    assert source.update_command == "npm install -g @yysjjd/agent-feed@latest"


def test_detect_install_source_from_common_paths(tmp_path: Path) -> None:
    assert (
        detect_install_source(
            env={},
            executable=tmp_path / ".local/share/uv/tools/agent-feed/bin/agent-feed",
            package_file=tmp_path / ".local/share/uv/tools/agent-feed/lib/python3.12/site-packages/agent_feed/__init__.py",
        ).kind
        == "uv"
    )
    assert (
        detect_install_source(
            env={},
            executable=tmp_path / ".local/bin/agent-feed",
            package_file=tmp_path / "pipx/venvs/agent-feed/lib/python3.12/site-packages/agent_feed/__init__.py",
        ).kind
        == "pipx"
    )
    assert (
        detect_install_source(
            env={},
            executable=tmp_path / "bin/agent-feed",
            package_file=tmp_path / "Cellar/agent-feed/1.2.3/libexec/lib/python3.12/site-packages/agent_feed/__init__.py",
        ).kind
        == "brew"
    )
    assert (
        detect_install_source(
            env={},
            executable=tmp_path / "bin/agent-feed",
            package_file=tmp_path / "lib/node_modules/@yysjjd/agent-feed/.agent-feed-python/lib/python3.12/site-packages/agent_feed/__init__.py",
        ).kind
        == "npm"
    )


def test_detect_install_source_from_source_checkout(tmp_path: Path) -> None:
    package_file = tmp_path / "src/agent_feed/__init__.py"
    package_file.parent.mkdir(parents=True)
    package_file.write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'agent-feed'\n", encoding="utf-8")

    assert detect_install_source(env={}, executable=tmp_path / ".venv/bin/agent-feed", package_file=package_file).kind == "source"


def test_update_commands_match_install_source() -> None:
    assert source_from_kind("uv").update_command == "uv tool upgrade agent-feed"
    assert source_from_kind("pipx").update_command == "pipx upgrade agent-feed"
    assert source_from_kind("brew").update_command == "brew update && brew upgrade fqmyysjjd/tap/agent-feed"
    assert source_from_kind("pypi").update_command


def test_version_comparison_is_semver_numeric() -> None:
    assert is_newer_version("1.2.0", "1.1.9")
    assert is_newer_version("1.1.10", "1.1.9")
    assert not is_newer_version("1.1.5", "1.1.5")
    assert not is_newer_version("1.1.4", "1.1.5")
    assert not is_newer_version("not-a-version", "1.1.5")


def test_parse_brew_formula_version_from_pypi_sdist_url() -> None:
    formula = 'url "https://files.pythonhosted.org/packages/agent_feed-1.2.3.tar.gz"'

    assert parse_brew_formula_version(formula) == "1.2.3"


def test_fetch_latest_version_for_npm_and_pypi(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[str] = []

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            return None

        def get(self, url: str) -> httpx.Response:
            requests.append(url)
            request = httpx.Request("GET", url)
            if "registry.npmjs.org" in url:
                return httpx.Response(200, request=request, json={"dist-tags": {"latest": "2.0.0"}})
            return httpx.Response(200, request=request, json={"info": {"version": "3.0.0"}})

    monkeypatch.setattr(httpx, "Client", FakeClient)

    assert fetch_latest_version(InstallSource("npm", "npm", "npm", "cmd")) == "2.0.0"
    assert fetch_latest_version(InstallSource("uv", "uv tool", "pypi", "cmd")) == "3.0.0"
    assert any("%40yysjjd%2Fagent-feed" in request for request in requests)
