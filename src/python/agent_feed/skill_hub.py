"""Curated remote skill hub support."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import httpx

from agent_feed.models import WriteAction

GITHUB_API = "https://api.github.com"
DEFAULT_TIMEOUT = 20.0


@dataclass(frozen=True)
class SkillHub:
    key: str
    name: str
    owner: str
    repo: str
    branch: str
    skills_path: str
    url: str
    description: str


@dataclass(frozen=True)
class RemoteSkill:
    hub: SkillHub
    name: str
    path: str
    url: str
    description: str


@dataclass(frozen=True)
class RemoteSkillFile:
    path: str
    content: str


@dataclass(frozen=True)
class RemoteSkillPackage:
    skill: RemoteSkill
    files: tuple[RemoteSkillFile, ...]

    @property
    def destination_name(self) -> str:
        return self.skill.name


CURATED_HUBS: tuple[SkillHub, ...] = (
    SkillHub(
        key="openai",
        name="OpenAI Skills",
        owner="openai",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/openai/skills",
        description="OpenAI's public skills repository.",
    ),
    SkillHub(
        key="anthropic",
        name="Anthropic Skills",
        owner="anthropics",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/anthropics/skills",
        description="Anthropic's public skills repository.",
    ),
    SkillHub(
        key="trailofbits",
        name="Trail of Bits Skills",
        owner="trailofbits",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/trailofbits/skills",
        description="Security-focused public skills from Trail of Bits.",
    ),
)


def search_remote_skills(
    keyword: str,
    *,
    token: str | None = None,
    hubs: tuple[SkillHub, ...] = CURATED_HUBS,
) -> list[RemoteSkill]:
    terms = [term.lower() for term in keyword.split() if term.strip()]
    skills: list[RemoteSkill] = []
    errors: list[str] = []
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        for hub in hubs:
            try:
                for skill in list_hub_skills(client, hub, token=token):
                    haystack = f"{skill.name} {skill.description} {hub.name}".lower()
                    if not terms or all(term in haystack for term in terms):
                        skills.append(skill)
            except httpx.HTTPStatusError as exc:
                errors.append(f"{hub.name}: {format_http_status_error(exc)}")
            except httpx.HTTPError as exc:
                errors.append(f"{hub.name}: {exc}")
            except ImportError as exc:
                errors.append(f"{hub.name}: {format_import_error(exc)}")
    if errors and not skills:
        joined = "; ".join(errors)
        raise RuntimeError(f"Could not load curated skill hubs: {joined}")
    return sorted(skills, key=lambda item: (item.hub.name.lower(), item.name.lower()))


def list_hub_skills(
    client: httpx.Client,
    hub: SkillHub,
    *,
    token: str | None = None,
) -> list[RemoteSkill]:
    entries = github_tree(client, hub, token=token)
    skills: list[RemoteSkill] = []
    for entry in entries:
        path = str(entry.get("path", ""))
        if entry.get("type") != "blob" or Path(path).name != "SKILL.md":
            continue
        if hub.skills_path and not path.startswith(f"{hub.skills_path}/"):
            continue
        skill_path = Path(path).parent.as_posix()
        name = Path(skill_path).name
        description = read_remote_description(client, hub, skill_path, token=token)
        skills.append(
            RemoteSkill(
                hub=hub,
                name=name,
                path=skill_path,
                url=f"{hub.url}/tree/{hub.branch}/{skill_path}",
                description=description,
            )
        )
    return skills


def read_remote_description(
    client: httpx.Client,
    hub: SkillHub,
    skill_path: str,
    *,
    token: str | None = None,
) -> str:
    for file_name in ("SKILL.md", "README.md"):
        try:
            content = github_file_text(client, hub, f"{skill_path}/{file_name}", token=token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                continue
            raise
        frontmatter = parse_frontmatter(content)
        if frontmatter.get("description"):
            return frontmatter["description"]
        heading = first_markdown_heading(content)
        if heading:
            return heading
    return ""


def fetch_remote_skill(skill: RemoteSkill, *, token: str | None = None) -> RemoteSkillPackage:
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        try:
            files = tuple(fetch_tree_files(client, skill.hub, skill.path, token=token))
        except ImportError as exc:
            raise RuntimeError(format_import_error(exc)) from exc
    return RemoteSkillPackage(skill=skill, files=files)


def fetch_tree_files(
    client: httpx.Client,
    hub: SkillHub,
    path: str,
    *,
    root: str | None = None,
    token: str | None = None,
) -> list[RemoteSkillFile]:
    root_path = root or path
    files: list[RemoteSkillFile] = []
    for entry in github_contents(client, hub, path, token=token):
        entry_type = entry.get("type")
        entry_path = str(entry["path"])
        if entry_type == "dir":
            files.extend(fetch_tree_files(client, hub, entry_path, root=root_path, token=token))
        elif entry_type == "file":
            rel_path = Path(entry_path).relative_to(root_path).as_posix()
            files.append(
                RemoteSkillFile(
                    path=rel_path,
                    content=github_file_text(client, hub, entry_path, token=token),
                )
            )
    return files


def install_remote_skill_package(
    target: Path,
    package: RemoteSkillPackage,
    *,
    dry_run: bool,
) -> tuple[list[WriteAction], list[str]]:
    skill_dir = target / ".agents/skills" / package.destination_name
    if not (target / ".agents/skills").is_dir():
        return [], ["missing .agents/skills; run agent-feed init before installing skills"]
    if skill_dir.exists():
        return [], [f"{skill_dir} already exists"]

    actions: list[WriteAction] = []
    for remote_file in package.files:
        destination = skill_dir / remote_file.path
        content = normalize_skill_content(package, remote_file)
        actions.append(
            WriteAction(
                path=destination,
                action="would create" if dry_run else "create",
                detail=f"from {package.skill.hub.name}",
            )
        )
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
    return actions, []


def normalize_skill_content(package: RemoteSkillPackage, remote_file: RemoteSkillFile) -> str:
    content = remote_file.content
    if remote_file.path == "SKILL.md":
        return normalize_skill_frontmatter(content, package.skill)
    return content


def normalize_skill_frontmatter(content: str, skill: RemoteSkill) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content

    closing = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing = index
            break
    if closing is None:
        return content

    body = list(lines)
    key_lines: dict[str, int] = {}
    for index in range(1, closing):
        if ":" not in body[index]:
            continue
        key, _value = body[index].split(":", 1)
        key_lines[key.strip()] = index

    metadata = {
        "source": f"hub:{skill.hub.key}",
        "trust": "custom",
    }
    insert_at = closing
    for key, value in metadata.items():
        if key in key_lines:
            body[key_lines[key]] = f"{key}: {value}"
        else:
            body.insert(insert_at, f"{key}: {value}")
            insert_at += 1
    normalized = "\n".join(body)
    if content.endswith("\n"):
        normalized += "\n"
    return normalized


def preview_skill_tree(package: RemoteSkillPackage) -> str:
    lines = [
        f"{package.destination_name}/",
        *[f"  {file.path}" for file in package.files],
    ]
    return "\n".join(lines)


def github_contents(
    client: httpx.Client,
    hub: SkillHub,
    path: str,
    *,
    token: str | None = None,
) -> list[dict[str, Any]]:
    response = client.get(
        f"{GITHUB_API}/repos/{hub.owner}/{hub.repo}/contents/{path}",
        params={"ref": hub.branch},
        headers=github_headers(token=token),
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise RuntimeError(f"Expected directory listing for {hub.owner}/{hub.repo}/{path}")


def github_tree(
    client: httpx.Client,
    hub: SkillHub,
    *,
    token: str | None = None,
) -> list[dict[str, Any]]:
    response = client.get(
        f"{GITHUB_API}/repos/{hub.owner}/{hub.repo}/git/trees/{hub.branch}",
        params={"recursive": "1"},
        headers=github_headers(token=token),
    )
    response.raise_for_status()
    data = response.json()
    tree = data.get("tree") if isinstance(data, dict) else None
    if isinstance(tree, list):
        return [item for item in tree if isinstance(item, dict)]
    raise RuntimeError(f"Expected recursive tree for {hub.owner}/{hub.repo}")


def github_file_text(
    client: httpx.Client,
    hub: SkillHub,
    path: str,
    *,
    token: str | None = None,
) -> str:
    response = client.get(
        f"{GITHUB_API}/repos/{hub.owner}/{hub.repo}/contents/{path}",
        params={"ref": hub.branch},
        headers=github_headers(token=token),
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected file response for {hub.owner}/{hub.repo}/{path}")
    encoded = data.get("content")
    if not isinstance(encoded, str):
        raise RuntimeError(f"Missing content for {hub.owner}/{hub.repo}/{path}")
    return base64.b64decode(encoded).decode("utf-8")


def parse_frontmatter(content: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def first_markdown_heading(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return ""


def github_headers(*, token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "agent-feed-skill-hub",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resolved_token = (token or os.environ.get("GITHUB_TOKEN", "")).strip()
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"
    return headers


def format_http_status_error(exc: httpx.HTTPStatusError) -> str:
    status = exc.response.status_code
    if status == 403 and exc.response.headers.get("x-ratelimit-remaining") == "0":
        reset = exc.response.headers.get("x-ratelimit-reset")
        suffix = f" reset={reset}" if reset else ""
        return (
            "GitHub API rate limit reached. "
            "Set GITHUB_TOKEN in your shell or put the token in settings.github_token "
            f"inside the user-level Agent Feed config.{suffix}"
        )
    if status == 404:
        return f"GitHub path not found: {exc.request.url}"
    return f"GitHub request failed with HTTP {status}: {exc.request.url}"


def format_import_error(exc: ImportError) -> str:
    message = str(exc)
    if "socksio" in message.lower() or "SOCKS proxy" in message:
        return (
            "SOCKS proxy support is missing. Upgrade Agent Feed so it installs "
            "httpx[socks], or install socksio in the same environment."
        )
    return message
