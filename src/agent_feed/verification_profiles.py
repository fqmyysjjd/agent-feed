"""Verification profile rendering for generated protocol assets."""

from __future__ import annotations

from textwrap import dedent

from agent_feed.models import VerificationProfile


PROFILE_LABELS = {
    VerificationProfile.PYTHON: "Python",
    VerificationProfile.NODE: "Node",
    VerificationProfile.CUSTOM: "Custom commands",
    VerificationProfile.NONE: "Docs only",
}


def verification_context(profile: VerificationProfile) -> dict[str, str]:
    return {
        "VERIFY_AGENT_DEV_SH": verify_script(profile),
        "VERIFICATION_PROFILE_DOC": verification_doc(profile),
    }


def verify_script(profile: VerificationProfile) -> str:
    script = dedent(
        """\
        #!/usr/bin/env sh
        set -eu

        # Unified verification entry for AI-assisted development work.
        # Verification profile: __PROFILE__
        # Customize run_code for this repository's real test/lint/type/build commands.

        ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
        SCRIPT_NAME="verify-agent-dev"
        cd "$ROOT_DIR"

        if [ -z "${UV_CACHE_DIR:-}" ]; then
          UV_CACHE_DIR="${TMPDIR:-/tmp}/agent-feed-uv-cache"
          export UV_CACHE_DIR
        fi

        fail() {
          echo "$SCRIPT_NAME: ERROR: $*" >&2
          exit 1
        }

        say() {
          printf '%s\\n' "$SCRIPT_NAME: $*"
        }

        usage() {
          cat <<'USAGE'
        Usage: sh .agents/scripts/verify-agent-dev.sh <scope>

        Scopes:
          docs      Check AI engineering docs, links, session-state JSON, and skill mirrors.
          code      Run the selected code verification gate.
          full      Run docs checks and the selected code verification gate.

        Selected verification profile: __PROFILE__
        Edit .agents/scripts/verify-agent-dev.sh if this project's real commands differ.
        USAGE
        }

        run_step() {
          desc="$1"
          shift

          say "Running: $desc"
          "$@" || fail "$desc failed. Fix the failure above before claiming this verification scope passed."
        }

        run_docs() {
          run_step "AI docs and asset consistency checks" sh .agents/scripts/check-agent-assets.sh
        }

        __RUN_CODE__

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
            ;;
          *)
            echo "$SCRIPT_NAME: ERROR: unknown scope: $1" >&2
            usage >&2
            exit 2
            ;;
        esac

        say "Verification passed for scope: $1"
        """
    )
    return script.replace("__PROFILE__", profile.value).replace(
        "__RUN_CODE__", run_code_function(profile)
    )


def run_code_function(profile: VerificationProfile) -> str:
    if profile == VerificationProfile.PYTHON:
        return dedent(
            """\
            run_optional_python_module() {
              module_name="$1"
              desc="$2"
              shift 2
              if [ "${PYTHON_RUNNER:-}" = "uv" ]; then
                if uv run python -m "$module_name" --version >/dev/null 2>&1; then
                  run_step "$desc" uv run python -m "$module_name" "$@"
                else
                  say "Skipping $desc: $module_name is not installed in this project environment."
                fi
              elif "$PYTHON_RUNNER" -m "$module_name" --version >/dev/null 2>&1; then
                run_step "$desc" "$PYTHON_RUNNER" -m "$module_name" "$@"
              else
                say "Skipping $desc: $module_name is not installed in this project environment."
              fi
            }

            run_code() {
              if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ] && [ ! -f "requirements.txt" ] && [ ! -f "pytest.ini" ]; then
                say "No common Python project marker found; continuing because the python profile was selected."
              fi
              if command -v uv >/dev/null 2>&1; then
                PYTHON_RUNNER="uv"
                run_step "pytest" uv run python -m pytest
              elif command -v python3 >/dev/null 2>&1; then
                PYTHON_RUNNER="python3"
                run_step "pytest" python3 -m pytest
              elif command -v python >/dev/null 2>&1; then
                PYTHON_RUNNER="python"
                run_step "pytest" python -m pytest
              else
                fail "python profile requires uv, python3, or python. Install one or customize run_code()."
              fi

              run_optional_python_module ruff "ruff check" check .
              run_optional_python_module mypy "mypy" .
            }
            """
        ).rstrip()
    if profile == VerificationProfile.NODE:
        return dedent(
            """\
            has_npm_script() {
              script_name="$1"
              node -e "const pkg=require('./package.json'); process.exit(pkg.scripts && pkg.scripts[process.argv[1]] ? 0 : 1)" "$script_name"
            }

            run_optional_npm_script() {
              script_name="$1"
              if has_npm_script "$script_name"; then
                run_step "$NODE_PM run $script_name" "$NODE_PM" run "$script_name"
              else
                say "Skipping $NODE_PM run $script_name: package.json has no $script_name script."
              fi
            }

            run_code() {
              if [ ! -f "package.json" ]; then
                fail "node profile requires package.json. Choose a Node project root or customize run_code()."
              fi
              if ! command -v node >/dev/null 2>&1; then
                fail "node profile requires node. Install node or customize run_code()."
              fi
              if command -v pnpm >/dev/null 2>&1; then
                NODE_PM="pnpm"
              elif command -v npm >/dev/null 2>&1; then
                NODE_PM="npm"
              else
                fail "node profile requires pnpm or npm. Install one or customize run_code()."
              fi

              run_step "$NODE_PM test" "$NODE_PM" test
              run_optional_npm_script lint
              run_optional_npm_script typecheck
              run_optional_npm_script build
            }
            """
        ).rstrip()
    if profile == VerificationProfile.CUSTOM:
        return dedent(
            """\
            run_code() {
              fail "custom profile selected but code verification is not configured. Edit run_code() in .agents/scripts/verify-agent-dev.sh with this project's real test/lint/type/build commands."
            }
            """
        ).rstrip()
    return dedent(
        """\
        run_code() {
          fail "no code verification profile configured. Use docs scope, or choose/configure a project verification profile before claiming code verification passed."
        }
        """
    ).rstrip()


def verification_doc(profile: VerificationProfile) -> str:
    if profile == VerificationProfile.PYTHON:
        return dedent(
            """\
            This project uses the `python` verification profile.

            ## Common Project Markers

            The profile recognizes common Python markers such as `pyproject.toml`, `setup.py`,
            `requirements.txt`, or `pytest.ini`, but it does not require a specific Python package
            manager.

            Required runtime: `uv`, `python3`, or `python` available in the shell.

            ## Code Gate

            ```sh
            uv run python -m pytest  # preferred when uv is available
            python3 -m pytest        # fallback when uv is unavailable
            python -m pytest         # fallback when python3 is unavailable
            python -m ruff check .   # when ruff is installed
            python -m mypy .         # when mypy is installed
            ```

            If the repository uses a different Python test runner, package manager, or source
            layout, update `.agents/scripts/verify-agent-dev.sh` before claiming the code gate is
            configured.
            """
        ).rstrip()
    if profile == VerificationProfile.NODE:
        return dedent(
            """\
            This project uses the `node` verification profile.

            ## Expected Project Markers

            1. `package.json` at the project root.
            2. `node` and either `pnpm` or `npm` available in the shell.

            ## Code Gate

            ```sh
            pnpm test   # preferred when pnpm is available
            npm test    # fallback when pnpm is unavailable
            <pm> run lint       # when package.json defines lint
            <pm> run typecheck  # when package.json defines typecheck
            <pm> run build      # when package.json defines build
            ```

            If the repository uses yarn, vitest-only commands, turborepo, workspaces, or another
            source layout, update `.agents/scripts/verify-agent-dev.sh` before claiming the code
            gate is configured.
            """
        ).rstrip()
    if profile == VerificationProfile.CUSTOM:
        return dedent(
            """\
            This project uses the `custom` verification profile.

            ## Required Setup

            Edit `.agents/scripts/verify-agent-dev.sh` and replace `run_code()` with this
            repository's real test, lint, type-check, build, or smoke-test commands.

            Until `run_code()` is configured, `code` and `full` verification scopes must fail.
            """
        ).rstrip()
    return dedent(
        """\
        This project uses the `none` verification profile.

        ## Meaning

        Agent Feed will validate AI engineering docs and assets with the `docs` scope, but no code
        verification gate is configured.

        Do not claim code verification passed until a real project-specific `run_code()` gate is
        added to `.agents/scripts/verify-agent-dev.sh`.
        """
    ).rstrip()
