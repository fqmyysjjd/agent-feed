#!/usr/bin/env sh
set -eu

# Unified verification entry for AI-assisted development work.
# Reads .agents/agent-feed.json verification_profile at runtime.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SCRIPT_NAME="verify-agent-dev"
cd "$ROOT_DIR"

if [ -z "${UV_CACHE_DIR:-}" ]; then
  UV_CACHE_DIR="${TMPDIR:-/tmp}/agent-feed-uv-cache"
  export UV_CACHE_DIR
fi

if [ -t 1 ] || [ -t 2 ]; then
  AF_RED=$(printf '\033[31m')
  AF_GREEN=$(printf '\033[32m')
  AF_YELLOW=$(printf '\033[33m')
  AF_BLUE=$(printf '\033[34m')
  AF_CYAN=$(printf '\033[36m')
  AF_BOLD=$(printf '\033[1m')
  AF_DIM=$(printf '\033[2m')
  AF_RESET=$(printf '\033[0m')
else
  AF_RED=""
  AF_GREEN=""
  AF_YELLOW=""
  AF_BLUE=""
  AF_CYAN=""
  AF_BOLD=""
  AF_DIM=""
  AF_RESET=""
fi

fail() {
  printf '%s%s: %sERROR:%s %s\n' "$AF_RED" "$SCRIPT_NAME" "$AF_BOLD" "$AF_RESET$AF_RED" "$*" >&2
  printf '%s' "$AF_RESET" >&2
  exit 1
}

say() {
  printf '%s%s:%s %s\n' "$AF_CYAN" "$SCRIPT_NAME" "$AF_RESET" "$*"
}

path_text() {
  printf '%s%s%s' "$AF_BLUE" "$1" "$AF_RESET"
}

command_text() {
  printf '%s%s%s%s' "$AF_GREEN" "$AF_BOLD" "$1" "$AF_RESET"
}

warn() {
  printf '%s%s: WARNING:%s %s\n' "$AF_YELLOW" "$SCRIPT_NAME" "$AF_RESET" "$*" >&2
}

config_value() {
  key="$1"
  python_code='import json,sys; data=json.load(open(".agents/agent-feed.json", encoding="utf-8")); value=data.get(sys.argv[1], ""); print(value if isinstance(value, str) else "")'
  node_code='const fs=require("fs"); const data=JSON.parse(fs.readFileSync(".agents/agent-feed.json", "utf8")); const value=data[process.argv[1]]; if (typeof value === "string") console.log(value)'
  if command -v python3 >/dev/null 2>&1 && python3 -c "$python_code" "$key"; then
    return 0
  fi
  if command -v python >/dev/null 2>&1 && python -c "$python_code" "$key"; then
    return 0
  fi
  if command -v node >/dev/null 2>&1 && node -e "$node_code" "$key"; then
    return 0
  fi
  sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' .agents/agent-feed.json | sed -n '1p'
}

verification_profile() {
  profile=$(config_value verification_profile || true)
  if [ -z "$profile" ]; then
    config_path=$(path_text ".agents/agent-feed.json")
    command=$(command_text "agent-feed config set verification_profile <python|node|custom|none>")
    fail "missing $config_path verification_profile. Run $command."
  fi
  printf '%s\n' "$profile"
}

usage() {
  verify_command=$(command_text "sh .agents/scripts/verify-agent-dev.sh <scope>")
  config_path=$(path_text ".agents/agent-feed.json")
  config_command=$(command_text "agent-feed config set verification_profile <python|node|custom|none>")
  cat <<USAGE
Usage: $verify_command

Scopes:
  docs      Check AI engineering docs, links, session-state JSON, and skill mirrors.
  code      Run the selected code verification gate.
  full      Run docs checks and the selected code verification gate.

The code gate reads $config_path verification_profile at runtime.
Change it with: $config_command
USAGE
}

run_step() {
  desc="$1"
  shift

  say "Running: $desc"
  "$@" || fail "$desc failed. Fix the failure above before claiming this verification scope passed."
}

run_docs() {
  run_step "AI asset trust check" sh .agents/scripts/check-agent-trust.sh
  run_step "AI docs and asset consistency checks" sh .agents/scripts/check-agent-assets.sh
}

run_optional_python_module() {
  module_name="$1"
  desc="$2"
  shift 2
  if [ "${PYTHON_RUNNER:-}" = "uv" ]; then
    if uv run python -m "$module_name" --version >/dev/null 2>&1; then
      run_step "$desc" env -u AGENT_FEED_HOME uv run python -m "$module_name" "$@"
    else
      warn "Skipping $desc: $module_name is not installed in this project environment."
    fi
  elif env -u AGENT_FEED_HOME "$PYTHON_RUNNER" -m "$module_name" --version >/dev/null 2>&1; then
    run_step "$desc" env -u AGENT_FEED_HOME "$PYTHON_RUNNER" -m "$module_name" "$@"
  else
    warn "Skipping $desc: $module_name is not installed in this project environment."
  fi
}

run_python_code() {
  if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ] && [ ! -f "requirements.txt" ] && [ ! -f "pytest.ini" ]; then
    say "No common Python project marker found; continuing because the python profile was selected."
  fi
  if command -v uv >/dev/null 2>&1; then
    PYTHON_RUNNER="uv"
    run_step "pytest" env -u AGENT_FEED_HOME uv run python -m pytest
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_RUNNER="python3"
    run_step "pytest" env -u AGENT_FEED_HOME python3 -m pytest
  elif command -v python >/dev/null 2>&1; then
    PYTHON_RUNNER="python"
    run_step "pytest" env -u AGENT_FEED_HOME python -m pytest
  else
    fail "python profile requires uv, python3, or python. Install one or choose the custom profile."
  fi

  run_optional_python_module ruff "ruff check" check \
    --exclude .agents/skills \
    --exclude .claude/skills \
    --exclude .feed-backup \
    .
  run_optional_python_module mypy "mypy" \
    --exclude '(^|/)(\.agents/skills|\.claude/skills|\.feed-backup)/' \
    .
}

has_npm_script() {
  script_name="$1"
  node -e "const pkg=require('./package.json'); process.exit(pkg.scripts && pkg.scripts[process.argv[1]] ? 0 : 1)" "$script_name"
}

run_optional_npm_script() {
  script_name="$1"
  if has_npm_script "$script_name"; then
    run_step "$NODE_PM run $script_name" "$NODE_PM" run "$script_name"
  else
    package_path=$(path_text "package.json")
    warn "Skipping $(command_text "$NODE_PM run $script_name"): $package_path has no $script_name script."
  fi
}

run_node_code() {
  if [ ! -f "package.json" ]; then
    fail "node profile requires package.json. Choose a Node project root or switch to custom."
  fi
  if ! command -v node >/dev/null 2>&1; then
    fail "node profile requires node. Install node or switch to custom."
  fi
  if command -v pnpm >/dev/null 2>&1; then
    NODE_PM="pnpm"
  elif command -v npm >/dev/null 2>&1; then
    NODE_PM="npm"
  else
    fail "node profile requires pnpm or npm. Install one or switch to custom."
  fi

  run_step "$NODE_PM test" "$NODE_PM" test
  run_optional_npm_script lint
  run_optional_npm_script typecheck
  run_optional_npm_script build
}

run_custom_code() {
  commands_file=".agents/project/verification-commands.sh"
  if [ ! -f "$commands_file" ]; then
    commands_path=$(path_text "$commands_file")
    fail "custom profile selected but $commands_path is missing. Restore it or add run_project_code_checks()."
  fi

  . "$commands_file"

  if ! command -v run_project_code_checks >/dev/null 2>&1; then
    commands_path=$(path_text "$commands_file")
    fail "custom profile requires run_project_code_checks() in $commands_path."
  fi

  run_step "custom code verification" run_project_code_checks
}

run_code() {
  profile=$(verification_profile)
  say "Verification profile: $profile"
  case "$profile" in
    python)
      run_python_code
      ;;
    node)
      run_node_code
      ;;
    custom)
      run_custom_code
      ;;
    none)
      fail "no code verification profile configured. Use docs scope, or choose/configure a project verification profile before claiming code verification passed."
      ;;
    *)
      config_path=$(path_text ".agents/agent-feed.json")
      fail "unknown verification_profile in $config_path: $profile"
      ;;
  esac
}

if [ "$#" -ne 1 ]; then
  usage >&2
  exit 2
fi

case "$1" in
  docs)
    say "Selected scope: docs"
    run_docs
    ;;
  code)
    say "Selected scope: code"
    run_code
    ;;
  full)
    say "Selected scope: full"
    run_docs
    run_code
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    printf '%s%s: %sERROR:%s unknown scope: %s%s\n' "$AF_RED" "$SCRIPT_NAME" "$AF_BOLD" "$AF_RESET$AF_RED" "$1" "$AF_RESET" >&2
    usage >&2
    exit 2
    ;;
esac

say "Verification passed for scope: $1"
