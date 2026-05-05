from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def test_sync_release_version_updates_release_metadata(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    worktree = tmp_path / "repo"
    shutil.copytree(root, worktree, ignore=shutil.ignore_patterns(".git", ".venv", "dist"))

    result = subprocess.run(
        [sys.executable, "scripts/sync-release-version.py", "v2.3.4"],
        cwd=worktree,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Synced release metadata to 2.3.4" in result.stdout
    assert 'version = "2.3.4"' in (worktree / "pyproject.toml").read_text()
    assert '__version__ = "2.3.4"' in (
        worktree / "src/agent_feed/__init__.py"
    ).read_text()

    package = json.loads((worktree / "package.json").read_text())
    package_lock = json.loads((worktree / "package-lock.json").read_text())
    assert package["name"] == "@yysjjd/agent-feed"
    assert package["version"] == "2.3.4"
    assert package_lock["name"] == "@yysjjd/agent-feed"
    assert package_lock["version"] == "2.3.4"
    assert package_lock["packages"][""]["name"] == "@yysjjd/agent-feed"
    assert package_lock["packages"][""]["version"] == "2.3.4"
