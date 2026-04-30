#!/usr/bin/env sh
set -eu

# Check AI-engineering assets that are easy to drift during agent-assisted work.
# This script prefers ripgrep when available, but falls back to POSIX find+grep.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SCRIPT_NAME="check-agent-assets"

fail() {
  echo "$SCRIPT_NAME: ERROR: $*" >&2
  echo "$SCRIPT_NAME: Fix the issue above, then rerun: sh .agents/scripts/verify-agent-dev.sh protocol" >&2
  exit 1
}

say() {
  printf '%s\n' "$SCRIPT_NAME: $*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

need_cmd grep
need_cmd diff
need_cmd python3

cd "$ROOT_DIR"

for required_dir in .agents/skills .agents/rules .agents/project .agents/domain .agents/scripts; do
  if [ ! -d "$required_dir" ]; then
    fail "missing $required_dir. Restore generated AI engineering assets before checking."
  fi
done

say "Checking skill names..."

for skill_file in .agents/skills/*/SKILL.md; do
  skill_dir=$(basename "$(dirname "$skill_file")")
  skill_name=$(sed -n 's/^name: //p' "$skill_file" | head -n 1)

  if [ -z "$skill_name" ]; then
    fail "missing frontmatter name in $skill_file. Add a 'name: $skill_dir' line."
  fi

  if [ "$skill_dir" != "$skill_name" ]; then
    fail "skill directory and name differ: dir=$skill_dir name=$skill_name."
  fi

  if ! printf '%s\n' "$skill_name" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'; then
    fail "skill name is not lowercase kebab-case: $skill_name."
  fi

  word_count=$(printf '%s\n' "$skill_name" | awk -F- '{print NF}')
  if [ "$word_count" -gt 3 ]; then
    fail "skill name has more than three words: $skill_name."
  fi
done

say "Checking client adapters..."

if [ -d .codex/skills ]; then
  say "Found legacy .codex/skills mirror; Codex uses .agents/skills directly."
fi

if [ -e CLAUDE.md ] && [ ! -f CLAUDE.md ]; then
  fail "CLAUDE.md exists but is not a file."
fi

if [ -f CLAUDE.md ]; then
  if ! grep -q '<!-- agent-feed:managed adapter=claude version=1 -->' CLAUDE.md; then
    fail "CLAUDE.md exists but is not a managed Agent Feed adapter."
  fi
  if ! grep -q '@AGENTS.md' CLAUDE.md; then
    fail "CLAUDE.md must import @AGENTS.md."
  fi
fi

if [ -e .claude/skills ] && [ ! -d .claude/skills ]; then
  fail ".claude/skills exists but is not a directory."
fi

if [ -d .claude/skills ]; then
  if ! diff_output=$(diff -qr .agents/skills .claude/skills); then
    printf '%s\n' "$diff_output" >&2
    fail ".claude/skills is out of sync. Run: sh .agents/scripts/sync-agent-assets.sh"
  fi
fi

if [ -e .cursor/rules/agent-feed.mdc ] && [ ! -f .cursor/rules/agent-feed.mdc ]; then
  fail ".cursor/rules/agent-feed.mdc exists but is not a file."
fi

if [ -f .cursor/rules/agent-feed.mdc ]; then
  if ! grep -q '<!-- agent-feed:managed adapter=cursor version=1 -->' .cursor/rules/agent-feed.mdc; then
    fail ".cursor/rules/agent-feed.mdc is not a managed Agent Feed adapter."
  fi
  if ! grep -q 'alwaysApply: true' .cursor/rules/agent-feed.mdc; then
    fail ".cursor/rules/agent-feed.mdc must set alwaysApply: true."
  fi
fi

say "Checking .agents path references and indexes..."

python3 - <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(".").resolve()
errors: list[str] = []
path_pattern = re.compile(r"\.agents/[A-Za-z0-9_.*/<>-]+")
skip_parts = {".git", "node_modules", ".venv"}
optional_local_paths = {".agents/session-state/current.json"}

for md in root.rglob("*.md"):
    rel = md.relative_to(root)
    if any(part in skip_parts for part in rel.parts):
        continue
    text = md.read_text(encoding="utf-8")
    for match in path_pattern.findall(text):
        path_text = match.rstrip(".,。)，):")
        if any(token in path_text for token in ("*", "<", ">", "YYYYMMDD")):
            continue
        if path_text in optional_local_paths:
            continue
        if not (root / path_text).exists():
            errors.append(f"{rel}: missing referenced path {path_text}")

agents_readme = (root / ".agents/README.md").read_text(encoding="utf-8")
for rule_file in sorted((root / ".agents/rules").glob("*.md")):
    if rule_file.name not in agents_readme:
        errors.append(f".agents/README.md does not list rule {rule_file.name}")

project_readme = (root / ".agents/project/README.md").read_text(encoding="utf-8")
for heading in ("## Boundary", "## Maintenance Contract", "## Current Project Constraints"):
    if heading not in project_readme:
        errors.append(f".agents/project/README.md missing required heading {heading}")
for project_file in sorted((root / ".agents/project").glob("*.md")):
    if project_file.name == "README.md":
        continue
    if project_file.name not in project_readme:
        errors.append(f".agents/project/README.md does not list {project_file.name}")

if errors:
    print("check-agent-assets: ERROR: structural checks failed", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    print("Fix stale links or README indexes, then rerun protocol verification.", file=sys.stderr)
    sys.exit(1)

state_root = root / ".agents/session-state"
if state_root.exists():
    for state_file in sorted(state_root.glob("*.json")):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"check-agent-assets: ERROR: {state_file} invalid JSON at "
                f"line {exc.lineno}, column {exc.colno}",
                file=sys.stderr,
            )
            sys.exit(1)

        if state_file.name == "schema.json":
            continue
        if not isinstance(data, dict) or data.get("schema_version") != 2:
            print(
                f"check-agent-assets: ERROR: {state_file} must be a schema_version 2 object",
                file=sys.stderr,
            )
            sys.exit(1)
        if state_file.name == "current.json":
            sessions = data.get("sessions")
            if not isinstance(sessions, list):
                print(
                    "check-agent-assets: ERROR: .agents/session-state/current.json "
                    "sessions must be a list",
                    file=sys.stderr,
                )
                sys.exit(1)
            for index, session in enumerate(sessions):
                if not isinstance(session, dict):
                    print(
                        "check-agent-assets: ERROR: current.json "
                        f"sessions[{index}] must be an object",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                session_file = session.get("session_file")
                if not isinstance(session_file, str) or not (root / session_file).exists():
                    print(
                        "check-agent-assets: ERROR: current.json "
                        f"sessions[{index}].session_file is missing: {session_file}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
PY

say "Agent asset checks passed"
