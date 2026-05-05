#!/usr/bin/env python3
"""Sync release metadata from a version string or GitHub release tag."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text()
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Expected one version match in {path}")
    path.write_text(updated)


def sync_package_json(path: Path, version: str) -> None:
    data = json.loads(path.read_text())
    data["version"] = version
    if path.name == "package-lock.json":
        data["name"] = "@yysjjd/agent-feed"
        packages = data.get("packages", {})
        if "" in packages:
            packages[""]["name"] = "@yysjjd/agent-feed"
            packages[""]["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version_or_tag")
    args = parser.parse_args()

    version = args.version_or_tag.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]+)?", version):
        raise SystemExit(f"Invalid release version: {args.version_or_tag}")

    replace_once(
        ROOT / "pyproject.toml",
        r'(?m)^version = "[^"]+"$',
        f'version = "{version}"',
    )
    replace_once(
        ROOT / "src/agent_feed/__init__.py",
        r'(?m)^__version__ = "[^"]+"$',
        f'__version__ = "{version}"',
    )
    replace_once(
        ROOT / ".agents/agent-feed.json",
        r'(?m)^  "agent_feed_version": "[^"]+",$',
        f'  "agent_feed_version": "{version}",',
    )
    sync_package_json(ROOT / "package.json", version)
    sync_package_json(ROOT / "package-lock.json", version)

    print(f"Synced release metadata to {version}")


if __name__ == "__main__":
    main()
