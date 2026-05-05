#!/usr/bin/env python3
"""Update the Homebrew formula source URL, checksum, and Python resources."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


def canonical_resource_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def build_pip_report(package_spec: str, python_bin: str) -> dict[str, object]:
    report_path = Path(tempfile.gettempdir()) / "agent-feed-homebrew-pip-report.json"
    subprocess.run(
        [
            python_bin,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            f"--report={report_path}",
            package_spec,
        ],
        check=True,
    )
    return json.loads(report_path.read_text())


def fetch_release_file(package_name: str, version: str) -> tuple[str, str]:
    encoded_name = urllib.parse.quote(package_name, safe="")
    url = f"https://pypi.org/pypi/{encoded_name}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)

    for item in payload.get("urls", []):
        if item.get("packagetype") == "sdist":
            return item["url"], item["digests"]["sha256"]

    raise RuntimeError(f"No sdist found for {package_name}=={version}")


def collect_resources(report: dict[str, object], root_name: str) -> list[tuple[str, str, str]]:
    resources: list[tuple[str, str, str]] = []
    installs = report.get("install", [])
    if not isinstance(installs, list):
        raise RuntimeError("pip report is missing the install list")

    for item in installs:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            continue
        name = metadata.get("name")
        version = metadata.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue
        if canonical_resource_name(name) == canonical_resource_name(root_name):
            continue
        resource_name = canonical_resource_name(name)
        try:
            resource_url, resource_sha = fetch_release_file(name, version)
        except Exception:
            download_info = item.get("download_info")
            if not isinstance(download_info, dict):
                raise
            resource_url = download_info["url"]
            archive_info = download_info.get("archive_info")
            if not isinstance(archive_info, dict):
                raise RuntimeError(f"Missing archive info for {name}=={version}")
            hashes = archive_info.get("hashes")
            if not isinstance(hashes, dict) or "sha256" not in hashes:
                raise RuntimeError(f"Missing sha256 for {name}=={version}")
            resource_sha = hashes["sha256"]
        resources.append((resource_name, resource_url, resource_sha))

    resources.sort(key=lambda item: item[0])
    return resources


def render_resource_blocks(resources: list[tuple[str, str, str]]) -> str:
    blocks: list[str] = []
    for name, url, sha256 in resources:
        blocks.append(
            "\n".join(
                [
                    f'  resource "{name}" do',
                    f'    url "{url}"',
                    f'    sha256 "{sha256}"',
                    "  end",
                ]
            )
        )
    return "\n\n".join(blocks)


def update_formula_text(
    text: str,
    source_url: str,
    source_sha256: str,
    resource_blocks: str,
) -> str:
    updated = re.sub(
        r'(?m)^  url ".*"$',
        f'  url "{source_url}"',
        text,
        count=1,
    )
    updated = re.sub(
        r'(?m)^  sha256 ".*"$',
        f'  sha256 "{source_sha256}"',
        updated,
        count=1,
    )
    updated, count = re.subn(
        r'(?ms)(depends_on "python@[^"]+"\n\n)(.*?)(\n  def install)',
        lambda match: f'{match.group(1)}{resource_blocks}\n{match.group(3)}',
        updated,
        count=1,
    )
    if count != 1:
        raise RuntimeError("Could not replace Homebrew resource blocks")
    updated = re.sub(
        r'assert_match "agent-feed [^"]+", shell_output',
        'assert_match "agent-feed #{version}", shell_output',
        updated,
        count=1,
    )
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formula", required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--python-bin", default=sys.executable)
    args = parser.parse_args()

    report = build_pip_report(f"{args.package_name}=={args.version}", args.python_bin)
    resources = collect_resources(report, args.package_name)
    resource_blocks = render_resource_blocks(resources)

    formula_path = Path(args.formula)
    text = formula_path.read_text()
    updated = update_formula_text(text, args.source_url, args.source_sha256, resource_blocks)
    formula_path.write_text(updated)


if __name__ == "__main__":
    main()
