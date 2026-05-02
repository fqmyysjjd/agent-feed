#!/usr/bin/env sh
set -eu

# Validate skills and managed scripts against $AGENT_FEED_HOME/config.json.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SCRIPT_NAME="check-agent-trust"
cd "$ROOT_DIR"

fail() {
  echo "$SCRIPT_NAME: ERROR: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd python3

if [ -z "${AGENT_FEED_HOME:-}" ]; then
  fail "AGENT_FEED_HOME is required. macOS/Linux: export AGENT_FEED_HOME=\"\$HOME/.agent-feed\". Windows PowerShell: [Environment]::SetEnvironmentVariable('AGENT_FEED_HOME', (Join-Path \$env:APPDATA 'agent-feed'), 'User')."
fi

TRUST_FILE="$AGENT_FEED_HOME/config.json"
LEGACY_TRUST_FILE="$AGENT_FEED_HOME/agent-feed.json"
if [ ! -f "$TRUST_FILE" ] && [ -f "$LEGACY_TRUST_FILE" ]; then
  TRUST_FILE="$LEGACY_TRUST_FILE"
fi

python3 - "$TRUST_FILE" "$ROOT_DIR" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

trust_file = Path(sys.argv[1])
root = Path(sys.argv[2]).resolve()

try:
    trust_file.resolve().relative_to(root)
except ValueError:
    pass
else:
    print(
        "check-agent-trust: ERROR: AGENT_FEED_HOME points inside the current project. "
        "Use an external Agent Feed home so trusted AI asset hashes are not stored in the repository.",
        file=sys.stderr,
    )
    sys.exit(1)

if not trust_file.exists():
    print(f"check-agent-trust: ERROR: missing {trust_file}", file=sys.stderr)
    print("Run `agent-feed index-skills -y` after reviewing current AI assets.", file=sys.stderr)
    sys.exit(1)

try:
    state = json.loads(trust_file.read_text(encoding="utf-8"))
except json.JSONDecodeError as exc:
    print(f"check-agent-trust: ERROR: invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

projects = state.get("projects")
if not isinstance(projects, dict):
    print("check-agent-trust: ERROR: projects must be a JSON object", file=sys.stderr)
    sys.exit(1)

project = projects.get(str(root))
if not isinstance(project, dict):
    print(f"check-agent-trust: ERROR: missing trust state for {root}", file=sys.stderr)
    print("Run `agent-feed index-skills -y` after reviewing current AI assets.", file=sys.stderr)
    sys.exit(1)

assets = project.get("assets")
if not isinstance(assets, dict):
    print("check-agent-trust: ERROR: assets must be a JSON object", file=sys.stderr)
    sys.exit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


paths = []
paths.extend(sorted(Path(".agents/skills").glob("*/SKILL.md")))
for text in [
    ".agents/scripts/check-agent-assets.sh",
    ".agents/scripts/check-agent-trust.sh",
    ".agents/scripts/index-skills.sh",
    ".agents/scripts/sync-agent-assets.sh",
    ".agents/scripts/verify-agent-dev.sh",
]:
    path = Path(text)
    if path.exists():
        paths.append(path)

errors = []
for path in paths:
    rel = path.as_posix()
    entry = assets.get(rel)
    current = sha256(path)
    if not isinstance(entry, dict):
        errors.append(f"{rel}: missing trust entry")
        continue
    allowed = entry.get("allowed_sha256")
    if not isinstance(allowed, list) or current not in allowed:
        errors.append(f"{rel}: trusted hash mismatch")

if errors:
    print("check-agent-trust: ERROR: Agent Feed asset trust check failed", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    print(
        "Highest-priority Agent Feed rule requires stopping before these files are used. "
        "Inspect with `agent-feed preview`; if intentional, accept with `agent-feed index-skills -y`.",
        file=sys.stderr,
    )
    sys.exit(1)

print("check-agent-trust: trust check passed")
PY
