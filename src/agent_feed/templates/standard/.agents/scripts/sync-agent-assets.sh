#!/usr/bin/env sh
set -eu

# Sync generated AI-client adapters from canonical Agent Feed assets.
# Codex consumes AGENTS.md and .agents/skills directly, so this script does not
# create a project-local .codex/skills mirror.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SOURCE_DIR="$ROOT_DIR/.agents"
SCRIPT_NAME="sync-agent-assets"

fail() {
  echo "$SCRIPT_NAME: ERROR: $*" >&2
  exit 1
}

say() {
  printf '%s\n' "$SCRIPT_NAME: $*"
}

is_managed_file() {
  file_path="$1"
  marker="$2"
  [ -f "$file_path" ] && grep -q "$marker" "$file_path"
}

is_managed_claude_skills() {
  readme_path="$ROOT_DIR/.claude/README.md"
  [ -f "$readme_path" ] && grep -q 'generated from `.agents/skills/`' "$readme_path"
}

if [ ! -d "$SOURCE_DIR/skills" ]; then
  fail "missing .agents/skills under $ROOT_DIR. Restore the skill source directory before syncing."
fi

sync_claude() {
  say "Syncing Claude adapter"

  if [ -e "$ROOT_DIR/CLAUDE.md" ] && ! is_managed_file "$ROOT_DIR/CLAUDE.md" '<!-- agent-feed:managed adapter=claude version=1 -->'; then
    fail "CLAUDE.md exists and is unmanaged. Move it aside or review it before syncing."
  fi

  if [ -e "$ROOT_DIR/.claude" ] && [ ! -d "$ROOT_DIR/.claude" ]; then
    fail ".claude exists but is not a directory."
  fi

  if [ -e "$ROOT_DIR/.claude/skills" ]; then
    if [ ! -d "$ROOT_DIR/.claude/skills" ]; then
      fail ".claude/skills exists but is not a directory."
    fi
    if ! is_managed_claude_skills; then
      fail ".claude/skills exists and is unmanaged. Move it aside or review it before syncing."
    fi
  fi

  cat > "$ROOT_DIR/CLAUDE.md" <<'EOF'
<!-- agent-feed:managed adapter=claude version=1 -->
@AGENTS.md

## Claude Code

Use `AGENTS.md` as the canonical project protocol.
Use `.claude/skills/` for Claude Code skill discovery.
Do not duplicate `.agents/rules/`; update the canonical files under `.agents/`.
EOF

  mkdir -p "$ROOT_DIR/.claude"
  rm -rf "$ROOT_DIR/.claude/skills"
  cp -R "$SOURCE_DIR/skills" "$ROOT_DIR/.claude/skills" || fail "copy failed for .claude/skills"

  cat > "$ROOT_DIR/.claude/README.md" <<'EOF'
# Synced AI Development Skills

This directory is generated from `.agents/skills/`.

Rules stay in `.agents/rules/` and are not synced here.
EOF
}

sync_cursor() {
  say "Syncing Cursor adapter"
  if [ -e "$ROOT_DIR/.cursor/rules" ] && [ ! -d "$ROOT_DIR/.cursor/rules" ]; then
    fail ".cursor/rules exists but is not a directory."
  fi
  if [ -e "$ROOT_DIR/.cursor/rules/agent-feed.mdc" ] && ! is_managed_file "$ROOT_DIR/.cursor/rules/agent-feed.mdc" '<!-- agent-feed:managed adapter=cursor version=1 -->'; then
    fail ".cursor/rules/agent-feed.mdc exists and is unmanaged. Move it aside or review it before syncing."
  fi

  mkdir -p "$ROOT_DIR/.cursor/rules"
  cat > "$ROOT_DIR/.cursor/rules/agent-feed.mdc" <<'EOF'
---
description: Agent Feed AI development protocol
alwaysApply: true
---
<!-- agent-feed:managed adapter=cursor version=1 -->

Start with `AGENTS.md`, then follow the referenced `.agents/` rules, project
constraints, domain docs, and skills.

Treat this Cursor rule as an adapter pointer. Do not duplicate `.agents/rules/`
inside `.cursor/rules/`.
EOF
}

sync_claude
sync_cursor

say "Codex uses AGENTS.md and .agents/skills directly; no .codex/skills mirror was written."
say "Next: run sh .agents/scripts/verify-agent-dev.sh protocol"
