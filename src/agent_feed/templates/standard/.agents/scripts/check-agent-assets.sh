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
  diff_output=$(diff -qr .agents/skills .claude/skills || true)
  diff_output=$(printf '%s\n' "$diff_output" | grep -v '/.DS_Store' || true)
  if [ -n "$diff_output" ]; then
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
    allowed_types = {"decision", "constraint", "blocker", "handoff"}

    def fail_state(message: str) -> None:
        print(f"check-agent-assets: ERROR: {message}", file=sys.stderr)
        sys.exit(1)

    def require_string(obj: dict, key: str, label: str) -> None:
        if not isinstance(obj.get(key), str) or not obj.get(key):
            fail_state(f"{label}.{key} must be a non-empty string")

    def require_keys(obj: dict, keys: list[str], label: str) -> None:
        for key in keys:
            if key not in obj:
                fail_state(f"{label} missing {key}")

    for state_file in sorted(state_root.glob("*.json")):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail_state(f"{state_file} invalid JSON at line {exc.lineno}, column {exc.colno}")

        if state_file.name == "schema.json":
            continue
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            fail_state(f"{state_file} must be a schema_version 1 object")
        if state_file.name == "current.json":
            require_keys(data, ["updated_at", "sessions"], "current.json")
            require_string(data, "updated_at", "current.json")
            active_session_file = data.get("active_session_file")
            active_session_file_value = None
            if active_session_file is not None:
                if not isinstance(active_session_file, str) or not active_session_file:
                    fail_state("current.json.active_session_file must be a non-empty string")
                active_session_file_value = active_session_file
                if not (root / active_session_file).exists():
                    fail_state(
                        f"current.json.active_session_file is missing: {active_session_file}"
                    )
            sessions = data.get("sessions")
            if not isinstance(sessions, list):
                fail_state(".agents/session-state/current.json sessions must be a list")
            session_files: set[str] = set()
            for index, session in enumerate(sessions):
                if not isinstance(session, dict):
                    fail_state(f"current.json sessions[{index}] must be an object")
                label = f"current.json.sessions[{index}]"
                require_keys(session, ["file", "label", "updated_at"], label)
                for key in ("file", "label", "updated_at"):
                    require_string(session, key, label)
                session_file = session.get("file")
                if not isinstance(session_file, str) or not (root / session_file).exists():
                    fail_state(f"{label}.file is missing: {session_file}")
                if session_file in session_files:
                    fail_state(f"{label}.file is duplicated: {session_file}")
                session_files.add(session_file)
            if active_session_file_value is not None and active_session_file_value not in session_files:
                fail_state("current.json.active_session_file is not listed in sessions")
            continue

        require_keys(data, ["session", "current_task", "carry_forwards"], str(state_file))
        session = data.get("session")
        if not isinstance(session, dict):
            fail_state(f"{state_file} session must be an object")
        require_keys(session, ["id", "label", "updated_at"], f"{state_file}.session")
        for key in ("id", "label", "updated_at"):
            require_string(session, key, f"{state_file}.session")

        current_task = data.get("current_task")
        if not isinstance(current_task, dict):
            fail_state(f"{state_file} current_task must be an object")
        for key in ("goal", "current_step", "stop_condition", "next_action"):
            require_string(current_task, key, f"{state_file}.current_task")

        carry_forwards = data.get("carry_forwards")
        if not isinstance(carry_forwards, list):
            fail_state(f"{state_file} carry_forwards must be a list")
        if len(carry_forwards) > 7:
            fail_state(f"{state_file} carry_forwards must contain at most 7 items")
        carry_forward_ids: set[str] = set()
        for index, item in enumerate(carry_forwards):
            if not isinstance(item, dict):
                fail_state(f"{state_file} carry_forwards[{index}] must be an object")
            label = f"{state_file}.carry_forwards[{index}]"
            require_keys(
                item,
                ["id", "type", "content", "why_keep", "expires_when", "updated_at"],
                label,
            )
            for key in ("id", "type", "content", "why_keep", "expires_when", "updated_at"):
                require_string(item, key, label)
            if item.get("type") not in allowed_types:
                fail_state(f"{label}.type must be one of: {', '.join(sorted(allowed_types))}")
            item_id = item.get("id")
            if isinstance(item_id, str):
                if item_id in carry_forward_ids:
                    fail_state(f"{label}.id is duplicated: {item_id}")
                carry_forward_ids.add(item_id)
PY

say "Agent asset checks passed"
