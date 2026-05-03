from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from click.testing import Result
from typer.testing import CliRunner

import agent_feed.cli as cli
from agent_feed.asset_trust import configured_github_token, recommended_agent_feed_home
from agent_feed.cli import app
from agent_feed.console import diff_line_style, render_diff
from agent_feed.models import DEFAULT_CLIENTS, Client
from agent_feed.skill_hub import (
    RemoteSkill,
    RemoteSkillFile,
    RemoteSkillPackage,
    SkillHub,
    format_http_status_error,
    github_headers,
    search_remote_skills,
)


runner = CliRunner()


def normalized_output(output: str) -> str:
    normalized = output.replace("\\\\", "/").replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def assert_output_mentions_path(output: str, rel_path: str) -> None:
    assert rel_path in normalized_output(output)


def assert_private_file_mode_when_supported(path: Path) -> None:
    if os.name != "nt":
        assert (path.stat().st_mode & 0o777) == 0o600


def invoke(args: list[str], tmp_path: Path, *, env: dict[str, str] | None = None) -> Result:
    trust_home = tmp_path.parent / f"{tmp_path.name}-agent-feed-home"
    merged_env = {"AGENT_FEED_HOME": str(trust_home), **(env or {})}
    return runner.invoke(app, args, env=merged_env)


def trust_config(tmp_path: Path) -> dict[str, Any]:
    data = json.loads(trust_config_path(tmp_path).read_text())
    if not isinstance(data, dict):
        raise AssertionError("trust config must be a JSON object")
    return data


def trust_config_path(tmp_path: Path) -> Path:
    return tmp_path.parent / f"{tmp_path.name}-agent-feed-home/config.json"


def legacy_trust_config_path(tmp_path: Path) -> Path:
    return tmp_path.parent / f"{tmp_path.name}-agent-feed-home/agent-feed.json"


def test_trust_home_is_required_and_external(tmp_path: Path) -> None:
    missing_env_non_interactive = runner.invoke(
        app,
        ["init", str(tmp_path), "--clients", "none", "--profile", "python", "--no-input"],
        env={"AGENT_FEED_HOME": ""},
    )
    assert missing_env_non_interactive.exit_code == 3, missing_env_non_interactive.output
    assert "AGENT_FEED_HOME is required" in missing_env_non_interactive.output
    assert "agent-feed env setup" in missing_env_non_interactive.output

    local_env = {"AGENT_FEED_HOME": str(tmp_path / ".agents")}
    local_result = runner.invoke(
        app,
        ["init", str(tmp_path), "--clients", "none", "--profile", "python"],
        env=local_env,
    )
    assert local_result.exit_code == 3, local_result.output
    assert "points inside the current project" in local_result.output
    assert not (tmp_path / "AGENTS.md").exists()


def test_init_can_auto_setup_missing_env_without_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    trust_home = tmp_path / "agent-feed-home"
    shell_home = tmp_path / "shell-home"

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr("agent_feed.env_setup.sys.platform", "linux")
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    monkeypatch.setattr(
        cli,
        "prompt_confirm",
        lambda _message, _default=True: pytest.fail("init should auto-setup missing env"),
    )

    result = runner.invoke(
        app,
        [
            "init",
            str(target),
            "--project-name",
            "Example",
            "--clients",
            "none",
            "--profile",
            "python",
            "--env-home",
            str(trust_home),
        ],
        env={
            "AGENT_FEED_HOME": "",
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
        },
    )

    assert result.exit_code == 0, result.output
    assert "Preparing external Agent Feed home" in result.output
    assert "Environment configured" in result.output
    assert (target / "AGENTS.md").exists()
    assert (trust_home / "config.json").exists()
    assert f'export AGENT_FEED_HOME="{trust_home}"' in (shell_home / ".bashrc").read_text(
        encoding="utf-8"
    )


def test_init_non_tty_requires_env_home_when_env_is_missing(tmp_path: Path) -> None:
    target = tmp_path / "project"

    result = runner.invoke(
        app,
        ["init", str(target), "--project-name", "Example", "--clients", "none", "--profile", "python"],
        env={
            "AGENT_FEED_HOME": "",
            "HOME": str(tmp_path / "shell-home"),
            "SHELL": "/bin/bash",
        },
    )

    assert result.exit_code == 3, result.output
    assert "AGENT_FEED_HOME is required" in result.output
    assert "Or rerun init with --env-home PATH" in result.output
    assert not (target / "AGENTS.md").exists()


def test_init_dry_run_can_preview_with_missing_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    trust_home = tmp_path / "agent-feed-home"
    shell_home = tmp_path / "shell-home"

    monkeypatch.setattr(cli, "can_prompt", lambda: True)

    result = runner.invoke(
        app,
        [
            "init",
            str(target),
            "--project-name",
            "Example",
            "--clients",
            "none",
            "--profile",
            "python",
            "--env-home",
            str(trust_home),
            "--dry-run",
        ],
        env={
            "AGENT_FEED_HOME": "",
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
        },
    )

    assert result.exit_code == 0, result.output
    assert "would create" in result.output
    assert not (target / "AGENTS.md").exists()
    assert not (trust_home / "config.json").exists()
    assert not (shell_home / ".bashrc").exists()


def test_env_setup_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path.parent / f"{tmp_path.name}-agent-feed-home"
    shell_home = tmp_path / "home"
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)

    print_result = runner.invoke(
        app,
        ["env", "print", "--home", str(home), "--shell", "bash"],
        env={"AGENT_FEED_HOME": ""},
    )
    assert print_result.exit_code == 0, print_result.output
    assert f'export AGENT_FEED_HOME="{home}"' in print_result.output

    dry_run = runner.invoke(
        app,
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(home),
            "--shell",
            "bash",
            "--dry-run",
        ],
        env={"AGENT_FEED_HOME": ""},
    )
    assert dry_run.exit_code == 0, dry_run.output
    assert "would create" in dry_run.output
    assert not (home / "config.json").exists()

    setup_result = runner.invoke(
        app,
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(home),
            "--shell",
            "bash",
        ],
        env={"HOME": str(shell_home), "AGENT_FEED_HOME": ""},
    )
    assert setup_result.exit_code == 0, setup_result.output
    assert (home / "config.json").exists()
    bashrc = shell_home / ".bashrc"
    assert bashrc.exists()
    assert "agent-feed env" in bashrc.read_text(encoding="utf-8")

    status_result = runner.invoke(
        app,
        ["env", "status", str(tmp_path)],
        env={"AGENT_FEED_HOME": str(home)},
    )
    assert status_result.exit_code == 0, status_result.output
    assert "environment is ready" in status_result.output


def test_default_agent_feed_home_is_user_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_feed.asset_trust.sys.platform", "linux")
    monkeypatch.delenv("APPDATA", raising=False)
    assert recommended_agent_feed_home() == Path.home() / ".agent-feed"

    monkeypatch.setattr("agent_feed.asset_trust.sys.platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\dev\AppData\Roaming")
    assert recommended_agent_feed_home() == Path(r"C:\Users\dev\AppData\Roaming") / "agent-feed"


def test_env_setup_uses_user_level_default_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_home = tmp_path.parent / "user-home-default"
    shell_home = workspace_home
    trust_home = workspace_home / ".agent-feed"
    monkeypatch.setattr("agent_feed.asset_trust.sys.platform", "linux")
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)

    setup_result = runner.invoke(
        app,
        ["env", "setup", str(tmp_path), "--shell", "bash"],
        env={
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
            "AGENT_FEED_HOME": "",
        },
    )

    assert setup_result.exit_code == 0, setup_result.output
    assert (trust_home / "config.json").exists()
    config = json.loads((trust_home / "config.json").read_text(encoding="utf-8"))
    assert config["settings"]["github_token"] == ""
    bashrc = shell_home / ".bashrc"
    assert bashrc.exists()
    assert f'export AGENT_FEED_HOME="{trust_home}"' in bashrc.read_text(encoding="utf-8")


def test_env_setup_requires_force_to_replace_existing_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell_home = tmp_path.parent / "user-home-force"
    old_home = shell_home / ".old-agent-feed"
    new_home = shell_home / ".agent-feed"
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)

    blocked = runner.invoke(
        app,
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(new_home),
            "--shell",
            "bash",
        ],
        env={
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
            "AGENT_FEED_HOME": str(old_home),
        },
    )

    assert blocked.exit_code == 3, blocked.output
    assert "AGENT_FEED_HOME is already set" in blocked.output
    assert "force" in blocked.output
    assert not (new_home / "config.json").exists()

    forced = runner.invoke(
        app,
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(new_home),
            "--shell",
            "bash",
            "--force",
        ],
        env={
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
            "AGENT_FEED_HOME": str(old_home),
        },
    )

    assert forced.exit_code == 0, forced.output
    assert (new_home / "config.json").exists()
    assert f'export AGENT_FEED_HOME="{new_home}"' in (shell_home / ".bashrc").read_text(
        encoding="utf-8"
    )


def test_env_setup_can_confirm_existing_home_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell_home = tmp_path.parent / "user-home-confirm-force"
    old_home = shell_home / ".old-agent-feed"
    new_home = shell_home / ".agent-feed"

    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(cli, "prompt_confirm", lambda _message, _default=True: True)

    result = runner.invoke(
        app,
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(new_home),
            "--shell",
            "bash",
        ],
        env={
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
            "AGENT_FEED_HOME": str(old_home),
        },
    )

    assert result.exit_code == 0, result.output
    assert (new_home / "config.json").exists()
    assert f'export AGENT_FEED_HOME="{new_home}"' in (shell_home / ".bashrc").read_text(
        encoding="utf-8"
    )


def test_env_uninstall_removes_shell_block_and_optional_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell_home = tmp_path.parent / "user-home-uninstall"
    home = shell_home / ".agent-feed"
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    setup_result = runner.invoke(
        app,
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(home),
            "--shell",
            "bash",
        ],
        env={"HOME": str(shell_home), "SHELL": "/bin/bash", "AGENT_FEED_HOME": ""},
    )
    assert setup_result.exit_code == 0, setup_result.output
    assert (home / "config.json").exists()

    blocked = runner.invoke(
        app,
        [
            "env",
            "uninstall",
            "--home",
            str(home),
            "--shell",
            "bash",
            "--remove-home",
            "--no-input",
        ],
        env={"HOME": str(shell_home), "SHELL": "/bin/bash", "AGENT_FEED_HOME": str(home)},
    )
    assert blocked.exit_code == 3, blocked.output
    assert "Pass -y" in blocked.output

    dry_run = runner.invoke(
        app,
        [
            "env",
            "uninstall",
            "--home",
            str(home),
            "--shell",
            "bash",
            "--remove-home",
            "--dry-run",
        ],
        env={"HOME": str(shell_home), "SHELL": "/bin/bash", "AGENT_FEED_HOME": str(home)},
    )
    assert dry_run.exit_code == 0, dry_run.output
    assert (home / "config.json").exists()

    uninstall_result = runner.invoke(
        app,
        [
            "env",
            "uninstall",
            "--home",
            str(home),
            "--shell",
            "bash",
            "--remove-home",
            "-y",
        ],
        env={"HOME": str(shell_home), "SHELL": "/bin/bash", "AGENT_FEED_HOME": str(home)},
    )
    assert uninstall_result.exit_code == 0, uninstall_result.output
    assert not home.exists()
    assert "agent-feed env" not in (shell_home / ".bashrc").read_text(encoding="utf-8")


def test_env_uninstall_without_changes_does_not_require_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shell_home = tmp_path.parent / "user-home-empty-uninstall"
    shell_home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    result = runner.invoke(
        app,
        ["env", "uninstall", "--shell", "bash", "--no-input"],
        env={
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
        },
    )

    assert result.exit_code == 0, result.output
    assert "No Agent Feed environment changes were found" in result.output
    assert "pass -y" not in result.output


def test_env_setup_commands_support_windows_powershell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent_feed.env_setup.sys.platform", "win32")
    monkeypatch.setattr("agent_feed.asset_trust.sys.platform", "win32")
    monkeypatch.setattr("agent_feed.env_setup.set_windows_user_env", lambda _home: None)
    monkeypatch.setattr("agent_feed.env_setup.remove_windows_user_env", lambda: None)
    appdata = tmp_path.parent / "windows-appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    home = appdata / "agent-feed"

    setup_result = runner.invoke(
        app,
        ["env", "setup", str(tmp_path), "--shell", "powershell"],
        env={"AGENT_FEED_HOME": ""},
    )

    assert setup_result.exit_code == 0, setup_result.output
    assert (home / "config.json").exists()
    assert "HKCU" in setup_result.output

    uninstall_result = runner.invoke(
        app,
        ["env", "uninstall", "--shell", "powershell", "-y"],
        env={"AGENT_FEED_HOME": str(home)},
    )

    assert uninstall_result.exit_code == 0, uninstall_result.output
    assert "uninstall complete" in uninstall_result.output


def test_interactive_init_can_setup_missing_env_and_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    trust_home = tmp_path / "agent-feed-home"
    shell_home = tmp_path / "shell-home"

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr("agent_feed.env_setup.sys.platform", "linux")
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    monkeypatch.setattr(cli, "print_welcome", lambda: None)
    monkeypatch.setattr(cli, "prompt_path_step", lambda _message, _default: target)
    monkeypatch.setattr(cli, "prompt_text_step", lambda _message, _default: "Example")
    monkeypatch.setattr(cli, "prompt_clients_step", lambda _default: ())
    monkeypatch.setattr(cli, "prompt_verification_profile_step", lambda default: default)
    monkeypatch.setattr(
        cli,
        "prompt_confirm",
        lambda _message, _default=True: pytest.fail("init should auto-setup missing env"),
    )
    monkeypatch.setattr(cli, "suggested_agent_feed_home", lambda _target=None: trust_home)

    result = runner.invoke(
        app,
        ["init"],
        env={
            "AGENT_FEED_HOME": "",
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
        },
    )

    assert result.exit_code == 0, result.output
    assert "Environment configured" in result.output
    assert "init complete" in result.output
    assert (target / "AGENTS.md").exists()
    assert (trust_home / "config.json").exists()
    assert "AGENT_FEED_HOME" in (shell_home / ".bashrc").read_text(encoding="utf-8")


def test_init_with_explicit_path_can_setup_missing_env_and_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    trust_home = tmp_path / "agent-feed-home"
    shell_home = tmp_path / "shell-home"

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr("agent_feed.env_setup.sys.platform", "linux")
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    monkeypatch.setattr(
        cli,
        "prompt_confirm",
        lambda _message, _default=True: pytest.fail("init should auto-setup missing env"),
    )
    monkeypatch.setattr(cli, "suggested_agent_feed_home", lambda _target=None: trust_home)

    result = runner.invoke(
        app,
        ["init", str(target), "--profile", "python"],
        env={
            "AGENT_FEED_HOME": "",
            "HOME": str(shell_home),
            "SHELL": "/bin/bash",
        },
    )

    assert result.exit_code == 0, result.output
    assert "Environment configured" in result.output
    assert "init complete" in result.output
    assert (target / "AGENTS.md").exists()
    assert (trust_home / "config.json").exists()
    assert "AGENT_FEED_HOME" in (shell_home / ".bashrc").read_text(encoding="utf-8")


def test_init_and_check(tmp_path: Path) -> None:
    version_result = invoke(["--version"], tmp_path)
    assert version_result.exit_code == 0, version_result.output
    assert "executable:" in version_result.output
    assert "package:" in version_result.output

    short_version_result = invoke(["-v"], tmp_path)
    assert short_version_result.exit_code == 0, short_version_result.output
    assert "agent-feed" in short_version_result.output

    help_result = invoke(["--help"], tmp_path)
    assert help_result.exit_code == 0, help_result.output
    assert "agent-feed" in help_result.output
    assert "Options" in help_result.output
    assert "Compatibility alias for --version" not in help_result.output
    assert "upgrade" in help_result.output
    assert "index-skills" in help_result.output
    assert "skill-hub" in help_result.output
    assert "sync-skill-index" not in help_result.output
    assert "update" not in help_result.output
    assert "sync-skills" not in help_result.output
    assert "welcome" not in help_result.output
    assert "--install-completion" not in help_result.output
    assert "--show-completion" not in help_result.output

    short_help_result = invoke(["-h"], tmp_path)
    assert short_help_result.exit_code == 0, short_help_result.output
    assert "index-skills" in short_help_result.output

    index_help = invoke(["index-skills", "--help"], tmp_path)
    assert index_help.exit_code == 0, index_help.output
    assert "-y" in index_help.output
    assert "--yes" not in index_help.output

    env_help = invoke(["env", "--help"], tmp_path)
    assert env_help.exit_code == 0, env_help.output
    assert "uninstall" in env_help.output
    assert "--force" not in env_help.output

    env_setup_help = invoke(["env", "setup", "--help"], tmp_path)
    assert env_setup_help.exit_code == 0, env_setup_help.output

    env_setup_force = invoke(
        [
            "env",
            "setup",
            str(tmp_path),
            "--home",
            str(tmp_path.parent / f"{tmp_path.name}-agent-feed-home"),
            "--shell",
            "bash",
            "--force",
            "--dry-run",
        ],
        tmp_path,
        env={"HOME": str(tmp_path / "help-home"), "AGENT_FEED_HOME": ""},
    )
    assert env_setup_force.exit_code == 0, env_setup_force.output
    assert "would create" in env_setup_force.output

    init_help = invoke(["init", "--help"], tmp_path)
    assert init_help.exit_code == 0, init_help.output

    init_env_home = tmp_path.parent / f"{tmp_path.name}-init-env-home"
    init_env_target = tmp_path / "init-env-target"
    init_env_home_result = runner.invoke(
        app,
        [
            "init",
            str(init_env_target),
            "--project-name",
            "Env Home Example",
            "--clients",
            "none",
            "--profile",
            "python",
            "--env-home",
            str(init_env_home),
            "--dry-run",
        ],
        env={"AGENT_FEED_HOME": "", "HOME": str(tmp_path / "init-help-home")},
    )
    assert init_env_home_result.exit_code == 0, init_env_home_result.output
    assert "would create" in init_env_home_result.output

    preview_help = invoke(["preview", "--help"], tmp_path)
    assert preview_help.exit_code == 0, preview_help.output
    assert "--diff" not in preview_help.output

    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    project_bootstrap = (tmp_path / ".agents/project/README.md").read_text(encoding="utf-8")
    domain_bootstrap = (tmp_path / ".agents/domain/README.md").read_text(encoding="utf-8")
    agents_text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Personalization Bootstrap" in project_bootstrap
    assert "Personalization Bootstrap" in domain_bootstrap
    assert "infer concrete project/domain guidance" in agents_text
    assert "repository evidence" in agents_text
    assert "Do not stage, commit, or push" in agents_text
    assert ".agents/rules/git-collaboration.md" in agents_text
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents/agent-feed.json").exists()
    assert not (tmp_path / ".agents/agent-feed.trust.json").exists()
    assert (tmp_path.parent / f"{tmp_path.name}-agent-feed-home/config.json").exists()
    trust_state = trust_config(tmp_path)
    assert str(tmp_path.resolve()) in trust_state["projects"]
    assert (tmp_path / ".agents/rules/outcome-boundary.md").exists()
    assert (tmp_path / ".agents/skills/README.md").exists()
    assert (tmp_path / ".agents/skills/concept-review/SKILL.md").exists()
    assert (tmp_path / ".agents/scripts/index-skills.sh").exists()
    assert (tmp_path / ".agents/scripts/check-agent-trust.sh").exists()
    assert not (tmp_path / ".agents/scripts/sync-skill-index.sh").exists()
    assert (tmp_path / ".agents/scripts/verify-agent-dev.sh").exists()
    project_readme = (tmp_path / ".agents/project/README.md").read_text(encoding="utf-8")
    assert "user-maintained project customization layer" in project_readme
    assert "## Maintenance Contract" in project_readme
    verify_script = (tmp_path / ".agents/scripts/verify-agent-dev.sh").read_text(encoding="utf-8")
    assert "Reads .agents/agent-feed.json verification_profile at runtime." in verify_script
    assert "docs      Same as protocol" not in verify_script
    assert "protocol|docs" not in verify_script
    assert "docs      Check AI engineering docs" in verify_script
    assert "Selected scope: protocol" not in verify_script
    skill_index = (tmp_path / ".agents/skills/README.md").read_text(encoding="utf-8")
    assert "`concept-review`" in skill_index
    assert "`project-review`" in skill_index
    assert "`agent-feed`" in skill_index
    assert "`core`" in skill_index
    assert "agent-feed:skill-fingerprint" not in skill_index
    assert not (tmp_path / "scripts").exists()
    assert not (tmp_path / ".codex/skills").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".claude/skills/project-development/SKILL.md").exists()
    assert (tmp_path / ".cursor/rules/agent-feed.mdc").exists()
    cursor_rule = (tmp_path / ".cursor/rules/agent-feed.mdc").read_text(encoding="utf-8")
    assert "@AGENTS.md" in cursor_rule
    assert "alwaysApply: true" in cursor_rule

    check_result = invoke(["check", str(tmp_path), "--no-input"], tmp_path)
    assert check_result.exit_code == 0, check_result.output

    check_all_result = invoke(["check", str(tmp_path), "-a"], tmp_path)
    assert check_all_result.exit_code == 0, check_all_result.output

    sync_conflict_result = invoke(
        ["sync", str(tmp_path), "-a", "--clients", "codex"],
        tmp_path,
    )
    assert sync_conflict_result.exit_code != 0
    assert "use either -a/--all or --clients" in sync_conflict_result.output

    trust_result = invoke(["check", str(tmp_path), "--checks", "scripts"], tmp_path)
    assert trust_result.exit_code == 0, trust_result.output

    status_result = invoke(["status", str(tmp_path)], tmp_path)
    assert status_result.exit_code == 0, status_result.output
    assert "Agent Feed Inspection" in status_result.output
    assert "Legacy .codex/skills" not in status_result.output

    removed_command_result = invoke(["sync-skill-index", str(tmp_path)], tmp_path)
    assert removed_command_result.exit_code != 0
    removed_sync_skills_result = invoke(["sync-skills", str(tmp_path)], tmp_path)
    assert removed_sync_skills_result.exit_code != 0
    removed_welcome_result = invoke(["welcome"], tmp_path)
    assert removed_welcome_result.exit_code != 0
    for command in ("sync", "upgrade", "check"):
        result = invoke([command, str(tmp_path), "--interactive"], tmp_path)
        assert result.exit_code != 0
        assert "No such option: --interactive" in result.output


def test_yes_requires_explicit_profile_when_path_is_implicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(
        cli,
        "prompt_path_step",
        lambda _message, _default: pytest.fail("init -y should not prompt for path"),
    )
    monkeypatch.chdir(tmp_path)

    result = invoke(["init", "-y", "--clients", "none"], tmp_path)

    assert result.exit_code == 3, result.output
    assert "choose a project verification profile explicitly" in result.output
    assert not (tmp_path / "AGENTS.md").exists()


def test_yes_skips_init_prompt_when_profile_is_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(
        cli,
        "prompt_path_step",
        lambda _message, _default: pytest.fail("init -y should not prompt for path"),
    )
    monkeypatch.setattr(
        cli,
        "prompt_verification_profile_step",
        lambda _default: pytest.fail("init -y should not prompt for profile"),
    )
    monkeypatch.chdir(tmp_path)

    result = invoke(["init", "-y", "--clients", "none", "--profile", "python"], tmp_path)

    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").exists()


def test_uninstall_removes_project_trust_state(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output
    assert str(tmp_path.resolve()) in trust_config(tmp_path)["projects"]

    dry_run = invoke(["uninstall", str(tmp_path), "--dry-run"], tmp_path)
    assert dry_run.exit_code == 0, dry_run.output
    assert "would update" in dry_run.output
    assert str(tmp_path.resolve()) in trust_config(tmp_path)["projects"]

    uninstall_result = invoke(["uninstall", str(tmp_path), "-y"], tmp_path)
    assert uninstall_result.exit_code == 0, uninstall_result.output
    assert not (tmp_path / ".agents").exists()
    assert str(tmp_path.resolve()) not in trust_config(tmp_path)["projects"]


def test_check_requires_selection_when_prompt_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(cli, "prompt_checks", lambda _default: ())
    result = runner.invoke(
        app,
        ["check", str(tmp_path)],
        env={"AGENT_FEED_HOME": str(tmp_path.parent / f"{tmp_path.name}-agent-feed-home")},
    )
    assert result.exit_code == 3, result.output
    assert "select at least one check" in result.output


def test_sync_with_explicit_path_prompts_for_missing_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(
        ["init", str(tmp_path), "--project-name", "Example", "--clients", "none", "--profile", "python"],
        tmp_path,
    )
    assert init_result.exit_code == 0, init_result.output

    selected: dict[str, tuple[Client, ...]] = {}
    monkeypatch.setattr(cli, "can_prompt", lambda: True)

    def choose_clients(default: tuple[Client, ...]) -> tuple[Client, ...]:
        selected["default"] = default
        return (Client.CURSOR,)

    monkeypatch.setattr(cli, "prompt_clients", choose_clients)
    captured: dict[str, object] = {}

    def fake_sync_clients(
        _target: Path,
        *,
        clients: tuple[Client, ...],
        dry_run: bool,
        force_generated: bool,
        prune_generated: bool = False,
    ) -> tuple[list[object], list[str]]:
        captured["clients"] = clients
        captured["flags"] = (dry_run, force_generated, prune_generated)
        return [], []

    monkeypatch.setattr(cli, "sync_clients", fake_sync_clients)

    result = invoke(["sync", str(tmp_path), "--dry-run"], tmp_path)

    assert result.exit_code == 0, result.output
    assert selected["default"] == tuple(DEFAULT_CLIENTS)
    assert captured["clients"] == (Client.CURSOR,)
    assert captured["flags"] == (True, False, False)


def test_sync_all_shortcut_selects_every_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(
        ["init", str(tmp_path), "--project-name", "Example", "--clients", "none", "--profile", "python"],
        tmp_path,
    )
    assert init_result.exit_code == 0, init_result.output

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(
        cli,
        "prompt_clients",
        lambda _default: pytest.fail("sync -a should skip the client prompt"),
    )
    captured: dict[str, object] = {}

    def fake_sync_clients(
        _target: Path,
        *,
        clients: tuple[Client, ...],
        dry_run: bool,
        force_generated: bool,
        prune_generated: bool = False,
    ) -> tuple[list[object], list[str]]:
        captured["clients"] = clients
        captured["flags"] = (dry_run, force_generated, prune_generated)
        return [], []

    monkeypatch.setattr(cli, "sync_clients", fake_sync_clients)

    result = invoke(["sync", str(tmp_path), "-a", "--dry-run"], tmp_path)

    assert result.exit_code == 0, result.output
    assert captured["clients"] == tuple(Client)
    assert captured["flags"] == (True, False, False)


def test_recommended_command_reads_like_a_sentence(tmp_path: Path) -> None:
    result = invoke(
        [
            "init",
            str(tmp_path),
            "--project-name",
            "Example",
            "--clients",
            "none",
            "--profile",
            "custom",
        ],
        tmp_path,
    )

    assert result.exit_code == 0, result.output
    assert "Custom verification needs project commands Edit" in result.output
    assert ".agents/project/verification-commands.sh, then run" in result.output
    assert ".agents/scripts/verify-agent-dev.sh code." in result.output


def test_status_interactive_v_key_prints_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    outcome_file = tmp_path / ".agents/rules/outcome-boundary.md"
    outcome_file.write_text("# Local stale rule\n", encoding="utf-8")

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(cli, "prompt_view_diff_key", lambda: True)

    result = invoke(["status", str(tmp_path)], tmp_path)
    assert result.exit_code == 0, result.output
    assert "Local stale rule" in result.output


def test_status_and_preview_default_to_installed_clients(tmp_path: Path) -> None:
    init_result = invoke(
        ["init", str(tmp_path), "--project-name", "Example", "--clients", "none", "--profile", "python"],
        tmp_path,
    )
    assert init_result.exit_code == 0, init_result.output

    status_result = invoke(["status", str(tmp_path)], tmp_path)
    assert status_result.exit_code == 0, status_result.output
    assert "CLAUDE.md" not in status_result.output
    assert ".cursor/rules/agent-feed.mdc" not in status_result.output
    json_status = invoke(["status", str(tmp_path), "--json"], tmp_path)
    assert json_status.exit_code == 0, json_status.output
    assert "Claude adapter missing" not in json_status.output
    assert "Cursor adapter missing" not in json_status.output

    preview_result = invoke(["preview", str(tmp_path)], tmp_path)
    assert preview_result.exit_code == 0, preview_result.output
    assert "CLAUDE.md" not in preview_result.output
    assert ".cursor/rules/agent-feed.mdc" not in preview_result.output

    explicit_result = invoke(["preview", str(tmp_path), "--clients", "all"], tmp_path)
    assert explicit_result.exit_code == 0, explicit_result.output
    actions, errors = cli.preview_actions(
        target=tmp_path,
        project_name=None,
        clients=tuple(Client),
        verification_profile=None,
    )
    assert not errors
    assert any(action.path == tmp_path / "CLAUDE.md" for action in actions)
    assert any(action.path == tmp_path / ".cursor/rules/agent-feed.mdc" for action in actions)

    upgrade_result = invoke(["upgrade", str(tmp_path)], tmp_path)
    assert upgrade_result.exit_code == 0, upgrade_result.output
    assert "CLAUDE.md" not in upgrade_result.output
    assert ".cursor/rules/agent-feed.mdc" not in upgrade_result.output


def test_diff_rendering_uses_red_green_styles() -> None:
    diff = "\n".join(
        [
            "diff --git a/file.txt b/file.txt",
            "--- a/file.txt",
            "+++ b/file.txt",
            "@@ -1 +1 @@",
            "-old line",
            "+new line",
            " unchanged",
        ]
    )
    rendered = render_diff(diff)
    styled_segments = [
        (rendered.plain[span.start : span.end], str(span.style)) for span in rendered.spans
    ]

    assert diff_line_style("--- a/file.txt") == "bold red"
    assert diff_line_style("+++ b/file.txt") == "bold green"
    assert diff_line_style("-old line") == "red"
    assert diff_line_style("+new line") == "green"
    assert diff_line_style("@@ -1 +1 @@") == "bold cyan"
    assert any(
        segment.startswith("-old line") and "red" in style for segment, style in styled_segments
    )
    assert any(
        segment.startswith("+new line") and "green" in style for segment, style in styled_segments
    )


def test_index_skills_updates_manual_skill_changes(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    skill_dir = tmp_path / ".agents/skills/custom-review"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                "name: custom-review",
                "description: Use when reviewing custom imported practices.",
                "source: local",
                "trust: custom",
                "---",
                "",
                "# Custom Review",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stale_check = invoke(["check", str(tmp_path), "--checks", "skills"], tmp_path)
    assert stale_check.exit_code == 1, stale_check.output
    assert ".agents/skills/README.md is stale" in stale_check.output

    sync_result = invoke(["index-skills", str(tmp_path)], tmp_path)
    assert sync_result.exit_code == 0, sync_result.output
    skill_index = (tmp_path / ".agents/skills/README.md").read_text(encoding="utf-8")
    assert "`custom-review`" in skill_index
    assert "`custom`" in skill_index
    assert "agent-feed:skill-fingerprint" not in skill_index
    trust_state = trust_config(tmp_path)
    project_assets = trust_state["projects"][str(tmp_path.resolve())]["assets"]
    assert ".agents/skills/custom-review/SKILL.md" in project_assets

    fresh_check = invoke(["check", str(tmp_path), "--checks", "skills"], tmp_path)
    assert fresh_check.exit_code == 0, fresh_check.output


def test_index_skills_adds_missing_source_and_trust(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    skill_dir = tmp_path / ".agents/skills/imported-review"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "\n".join(
            [
                "---",
                "name: imported-review",
                "description: Use when reviewing imported practices.",
                "---",
                "",
                "# Imported Review",
                "",
            ]
        ),
        encoding="utf-8",
    )

    index_result = invoke(["index-skills", str(tmp_path)], tmp_path)
    assert index_result.exit_code == 0, index_result.output
    skill_text = skill_file.read_text(encoding="utf-8")
    assert "source: unknow" in skill_text
    assert "trust: custom" in skill_text
    skill_index = (tmp_path / ".agents/skills/README.md").read_text(encoding="utf-8")
    assert (
        "| `imported-review` | Use when reviewing imported practices. | `unknow` | `custom` |"
        in skill_index
    )
    assert "agent-feed:skill-fingerprint" not in skill_index

    check_result = invoke(["check", str(tmp_path), "--checks", "skills"], tmp_path)
    assert check_result.exit_code == 0, check_result.output


def test_skill_hub_installs_selected_remote_skill_and_indexes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    hub = SkillHub(
        key="example",
        name="Example Hub",
        owner="example",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/example/skills",
        description="Example skills.",
    )
    remote_skill = RemoteSkill(
        hub=hub,
        name="remote-review",
        path="skills/remote-review",
        url="https://github.com/example/skills/tree/main/skills/remote-review",
        description="Use when testing remote skill install.",
    )
    package = RemoteSkillPackage(
        skill=remote_skill,
        files=(
            RemoteSkillFile(
                path="SKILL.md",
                content="\n".join(
                    [
                        "---",
                        "name: remote-review",
                        "description: Use when testing remote skill install.",
                        "source: upstream",
                        "trust: reviewed",
                        "---",
                        "",
                        "# Remote Review",
                        "",
                    ]
                ),
            ),
        ),
    )

    monkeypatch.setattr(cli, "search_remote_skills", lambda _keyword, token=None: [remote_skill])
    monkeypatch.setattr(cli, "fetch_remote_skill", lambda _skill, token=None: package)

    result = invoke(
        ["skill-hub", str(tmp_path), "--keyword", "review", "--no-input"],
        tmp_path,
    )

    assert result.exit_code == 0, result.output
    skill_file = tmp_path / ".agents/skills/remote-review/SKILL.md"
    assert skill_file.exists()
    skill_text = skill_file.read_text(encoding="utf-8")
    assert "source: hub:example" in skill_text
    assert "trust: custom" in skill_text
    skill_index = (tmp_path / ".agents/skills/README.md").read_text(encoding="utf-8")
    assert "`remote-review`" in skill_index
    assert "`hub:example`" in skill_index
    assert "`custom`" in skill_index
    project_assets = trust_config(tmp_path)["projects"][str(tmp_path.resolve())]["assets"]
    assert ".agents/skills/remote-review/SKILL.md" in project_assets


def test_skill_hub_discovers_skills_from_recursive_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hub = SkillHub(
        key="example",
        name="Example Hub",
        owner="example",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/example/skills",
        description="Example skills.",
    )

    monkeypatch.setattr(
        "agent_feed.skill_hub.github_tree",
        lambda _client, _hub, token=None: [
            {"type": "tree", "path": "skills/.curated"},
            {"type": "blob", "path": "skills/.curated/review-helper/SKILL.md"},
            {"type": "blob", "path": "docs/not-a-skill/SKILL.md"},
        ],
    )
    monkeypatch.setattr(
        "agent_feed.skill_hub.read_remote_description",
        lambda _client, _hub, _path, token=None: "Use when reviewing recursive skills.",
    )

    skills = search_remote_skills("review", hubs=(hub,))

    assert [skill.name for skill in skills] == ["review-helper"]
    assert skills[0].path == "skills/.curated/review-helper"


def test_skill_hub_github_headers_and_rate_limit_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    headers = github_headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["User-Agent"] == "agent-feed-skill-hub"

    request = httpx.Request("GET", "https://api.github.com/repos/example/skills")
    response = httpx.Response(
        403,
        request=request,
        headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "123"},
    )
    message = format_http_status_error(
        httpx.HTTPStatusError("rate limited", request=request, response=response)
    )

    assert "GitHub API rate limit reached" in message
    assert "settings.github_token" in message
    assert "GITHUB_TOKEN" in message


def test_skill_hub_uses_saved_user_level_github_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = trust_config_path(tmp_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "agent_feed_version": "0.1.1",
                "settings": {"github_token": "saved-token"},
                "projects": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    captured: dict[str, str | None] = {"token": None}
    remote_skill = RemoteSkill(
        hub=SkillHub(
            key="example",
            name="Example Hub",
            owner="example",
            repo="skills",
            branch="main",
            skills_path="skills",
            url="https://github.com/example/skills",
            description="Example skills.",
        ),
        name="saved-token-skill",
        path="skills/saved-token-skill",
        url="https://github.com/example/skills/tree/main/skills/saved-token-skill",
        description="Uses saved token.",
    )

    def fake_search(
        _keyword: str, *, token: str | None = None, hubs: Any = None
    ) -> list[RemoteSkill]:
        captured["token"] = token
        return [remote_skill]

    package = RemoteSkillPackage(
        skill=remote_skill,
        files=(
            RemoteSkillFile(
                path="SKILL.md",
                content="\n".join(
                    [
                        "---",
                        "name: saved-token-skill",
                        "description: Uses saved token.",
                        "---",
                        "",
                        "# Saved Token Skill",
                        "",
                    ]
                ),
            ),
        ),
    )

    monkeypatch.setattr(cli, "search_remote_skills", fake_search)
    monkeypatch.setattr(cli, "fetch_remote_skill", lambda _skill, token=None: package)

    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    result = invoke(["skill-hub", str(tmp_path), "--keyword", "saved", "--no-input"], tmp_path)
    assert result.exit_code == 0, result.output
    assert captured["token"] == "saved-token"


def test_skill_hub_prompts_for_token_and_saves_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    hub = SkillHub(
        key="example",
        name="Example Hub",
        owner="example",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/example/skills",
        description="Example skills.",
    )
    remote_skill = RemoteSkill(
        hub=hub,
        name="token-retry-skill",
        path="skills/token-retry-skill",
        url="https://github.com/example/skills/tree/main/skills/token-retry-skill",
        description="Retries with token.",
    )
    package = RemoteSkillPackage(
        skill=remote_skill,
        files=(
            RemoteSkillFile(
                path="SKILL.md",
                content="\n".join(
                    [
                        "---",
                        "name: token-retry-skill",
                        "description: Retries with token.",
                        "---",
                        "",
                        "# Token Retry Skill",
                        "",
                    ]
                ),
            ),
        ),
    )

    calls: list[str | None] = []

    def fake_search(
        _keyword: str, *, token: str | None = None, hubs: Any = None
    ) -> list[RemoteSkill]:
        calls.append(token)
        if token is None:
            raise RuntimeError("GitHub API rate limit reached. Try a token.")
        return [remote_skill]

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(cli, "prompt_secret", lambda _message: "entered-token")
    monkeypatch.setattr(
        cli,
        "prompt_skill_hub_selection",
        lambda _choices, on_preview: ["example:token-retry-skill"],
    )
    monkeypatch.setattr(cli, "search_remote_skills", fake_search)
    monkeypatch.setattr(cli, "fetch_remote_skill", lambda _skill, token=None: package)

    result = invoke(["skill-hub", str(tmp_path), "--keyword", "retry"], tmp_path)
    assert result.exit_code == 0, result.output
    assert calls == [None, "entered-token"]

    config = trust_config(tmp_path)
    assert config["settings"]["github_token"] == "entered-token"
    assert_private_file_mode_when_supported(trust_config_path(tmp_path))


def test_skill_hub_failure_help_shows_shell_commands_and_json_example() -> None:
    message = cli._skill_hub_failure_help("GitHub request failed with HTTP 403")

    assert 'export GITHUB_TOKEN="ghp_your_token_here"' in message
    assert '$env:GITHUB_TOKEN = "ghp_your_token_here"' in message
    assert '"github_token": "ghp_your_token_here"' in message
    assert "settings.github_token" in message
    assert "config.json" in message


def test_skill_hub_escape_from_selection_returns_to_keyword_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    hub = SkillHub(
        key="example",
        name="Example Hub",
        owner="example",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/example/skills",
        description="Example skills.",
    )
    first_skill = RemoteSkill(
        hub=hub,
        name="first-skill",
        path="skills/first-skill",
        url="https://github.com/example/skills/tree/main/skills/first-skill",
        description="First result.",
    )
    second_skill = RemoteSkill(
        hub=hub,
        name="second-skill",
        path="skills/second-skill",
        url="https://github.com/example/skills/tree/main/skills/second-skill",
        description="Second result.",
    )
    package = RemoteSkillPackage(
        skill=second_skill,
        files=(
            RemoteSkillFile(
                path="SKILL.md",
                content="\n".join(
                    [
                        "---",
                        "name: second-skill",
                        "description: Second result.",
                        "---",
                        "",
                        "# Second Skill",
                        "",
                    ]
                ),
            ),
        ),
    )

    keywords = iter(["first", "second"])
    searches: list[str] = []
    selections = iter([None, ["example:second-skill"]])

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(cli, "prompt_skill_hub_keyword", lambda _default="": next(keywords, None))

    def fake_search(
        keyword: str, *, token: str | None = None, hubs: Any = None
    ) -> list[RemoteSkill]:
        searches.append(keyword)
        return [first_skill] if keyword == "first" else [second_skill]

    monkeypatch.setattr(cli, "search_remote_skills", fake_search)
    monkeypatch.setattr(
        cli,
        "prompt_skill_hub_selection",
        lambda _choices, on_preview: next(selections),
    )
    monkeypatch.setattr(cli, "fetch_remote_skill", lambda _skill, token=None: package)

    result = invoke(["skill-hub", str(tmp_path)], tmp_path)
    assert result.exit_code == 0, result.output
    assert searches == ["first", "second"]
    assert "Returned to keyword search." in result.output
    assert (tmp_path / ".agents/skills/second-skill/SKILL.md").exists()


def test_skill_hub_preview_uses_feedback_loader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    hub = SkillHub(
        key="example",
        name="Example Hub",
        owner="example",
        repo="skills",
        branch="main",
        skills_path="skills",
        url="https://github.com/example/skills",
        description="Example skills.",
    )
    remote_skill = RemoteSkill(
        hub=hub,
        name="previewable-skill",
        path="skills/previewable-skill",
        url="https://github.com/example/skills/tree/main/skills/previewable-skill",
        description="Preview me.",
    )
    package = RemoteSkillPackage(
        skill=remote_skill,
        files=(
            RemoteSkillFile(
                path="SKILL.md",
                content="\n".join(
                    [
                        "---",
                        "name: previewable-skill",
                        "description: Preview me.",
                        "---",
                        "",
                        "# Previewable Skill",
                        "",
                    ]
                ),
            ),
        ),
    )

    calls: list[str] = []

    monkeypatch.setattr(cli, "can_prompt", lambda: True)
    monkeypatch.setattr(cli, "search_remote_skills", lambda _keyword, token=None: [remote_skill])

    def fake_fetch_with_feedback(
        skill: RemoteSkill,
        *,
        token: str | None,
        message: str,
    ) -> RemoteSkillPackage:
        calls.append(message)
        return package

    monkeypatch.setattr(cli, "_fetch_remote_skill_with_feedback", fake_fetch_with_feedback)

    def fake_selection(_choices: list[dict[str, Any]], on_preview: Any) -> list[str]:
        on_preview({"value": "example:previewable-skill"})
        return ["example:previewable-skill"]

    monkeypatch.setattr(cli, "prompt_skill_hub_selection", fake_selection)

    result = invoke(["skill-hub", str(tmp_path), "--keyword", "preview"], tmp_path)
    assert result.exit_code == 0, result.output
    assert "Loading preview for previewable-skill..." in calls
    assert "Downloading previewable-skill..." in calls


def test_skill_hub_token_config_falls_back_to_user_home_without_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_home = tmp_path / "home"
    config_path = user_home / ".agent-feed/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "agent_feed_version": "0.1.1",
                "settings": {"github_token": "home-token"},
                "projects": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("pathlib.Path.home", lambda: user_home)
    monkeypatch.setattr("agent_feed.asset_trust.sys.platform", "linux")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("AGENT_FEED_HOME", raising=False)
    token, errors = configured_github_token(tmp_path)

    assert errors == []
    assert token == "home-token"


def test_env_setup_migrates_legacy_external_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path.parent / f"{tmp_path.name}-legacy-agent-feed-home"
    shell_home = tmp_path / "shell-home"
    monkeypatch.setattr("pathlib.Path.home", lambda: shell_home)
    legacy_path = home / "agent-feed.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "agent_feed_version": "0.0.0",
                "settings": {"github_token": "ghu_legacy_token"},
                "projects": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["env", "setup", str(tmp_path), "--home", str(home), "--shell", "bash"],
        env={"HOME": str(tmp_path / "shell-home"), "AGENT_FEED_HOME": ""},
    )

    assert result.exit_code == 0, result.output
    assert (home / "config.json").exists()
    assert not legacy_path.exists()
    migrated = json.loads((home / "config.json").read_text(encoding="utf-8"))
    assert migrated["settings"]["github_token"] == "ghu_legacy_token"


def test_config_set_can_remove_stale_external_project_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    config_path = trust_config_path(tmp_path)
    state = json.loads(config_path.read_text(encoding="utf-8"))
    stale_root = tmp_path.parent / "deleted-project"
    state["projects"][str(stale_root)] = {
        "project_root": str(stale_root),
        "project_name": "Deleted Project",
        "assets": {},
    }
    config_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    prompt_messages: list[str] = []
    monkeypatch.setattr(cli, "can_prompt", lambda: True)

    def confirm_cleanup(message: str, _default: bool = True) -> bool:
        prompt_messages.append(message)
        return True

    monkeypatch.setattr(cli, "prompt_confirm", confirm_cleanup)

    result = invoke(
        [
            "config",
            "set",
            "--path",
            str(tmp_path),
            "settings.session_state.max_carry_forwards",
            "6",
        ],
        tmp_path,
    )

    assert result.exit_code == 0, result.output
    assert "Stale Project Entries" in result.output
    assert "Config checks passed" in result.output
    assert "no longer exist" in result.output
    assert "stale trust metadata" in result.output
    assert "user-level config" in result.output
    assert "touch project files" in result.output
    assert prompt_messages == [
        "Remove these stale project records from the user-level config?"
    ]
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert str(stale_root) not in updated["projects"]


def test_config_check_reports_project_shape_errors(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    metadata_path = tmp_path / ".agents/agent-feed.json"
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    del data["verification_profile"]
    metadata_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    config_result = invoke(["config", "check", "--path", str(tmp_path)], tmp_path)
    assert config_result.exit_code == 1, config_result.output
    assert "Config Diagnostics" in config_result.output
    assert "agent-feed.json" in config_result.output
    assert "verification_profile" in config_result.output

    check_result = invoke(["check", str(tmp_path), "--checks", "config"], tmp_path)
    assert check_result.exit_code == 1, check_result.output
    assert "agent-feed.json" in check_result.output
    assert "verification_profile" in check_result.output


def test_config_check_warns_for_stale_external_project_entries(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    config_path = trust_config_path(tmp_path)
    state = json.loads(config_path.read_text(encoding="utf-8"))
    stale_root = tmp_path.parent / "deleted-project"
    state["projects"][str(stale_root)] = {
        "project_root": str(stale_root),
        "project_name": "Deleted Project",
        "assets": {},
    }
    config_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    result = invoke(["config", "check", "--path", str(tmp_path)], tmp_path)
    assert result.exit_code == 0, result.output
    assert "Config Diagnostics" in result.output
    assert "stale project entry" in result.output
    assert "directory" in result.output
    assert "deleted-project" in result.output


def test_skill_body_change_reports_trust_drift_without_reindex(
    tmp_path: Path,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    skill_file = tmp_path / ".agents/skills/project-review/SKILL.md"
    skill_file.write_text(
        skill_file.read_text(encoding="utf-8") + "\nUnsafe extra instruction.\n",
        encoding="utf-8",
    )

    check_result = invoke(["check", str(tmp_path), "--checks", "skills"], tmp_path)
    assert check_result.exit_code == 1, check_result.output
    assert "trusted hash mismatch" in check_result.output

    status_result = invoke(["status", str(tmp_path), "--json"], tmp_path)
    assert status_result.exit_code == 0, status_result.output
    assert "trusted hash mismatch" in status_result.output

    preview_result = invoke(["preview", str(tmp_path), "--clients", "none"], tmp_path)
    assert preview_result.exit_code == 0, preview_result.output
    assert "Unsafe extra instruction." in preview_result.output

    accept_result = invoke(["index-skills", str(tmp_path), "-y"], tmp_path)
    assert accept_result.exit_code == 0, accept_result.output
    fresh_check = invoke(["check", str(tmp_path), "--checks", "skills"], tmp_path)
    assert fresh_check.exit_code == 0, fresh_check.output


def test_status_and_preview_report_git_skill_changes_for_reviewed_skills(
    tmp_path: Path,
) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    skill_dir = tmp_path / ".agents/skills/reviewed-flow"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "\n".join(
            [
                "---",
                "name: reviewed-flow",
                "description: Use when applying a reviewed local workflow.",
                "source: local",
                "trust: reviewed",
                "---",
                "",
                "# Reviewed Flow",
                "",
            ]
        ),
        encoding="utf-8",
    )
    index_result = invoke(["index-skills", str(tmp_path)], tmp_path)
    assert index_result.exit_code == 0, index_result.output
    git_init = invoke(["check", str(tmp_path), "--checks", "skills"], tmp_path)
    assert git_init.exit_code == 0, git_init.output

    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "baseline",
        ],
        check=True,
        capture_output=True,
    )

    skill_file.write_text(
        skill_file.read_text(encoding="utf-8") + "\nRisky changed instruction.\n",
        encoding="utf-8",
    )

    status_result = invoke(["status", str(tmp_path), "--json"], tmp_path)
    assert status_result.exit_code == 0, status_result.output
    assert "trusted hash mismatch" in status_result.output

    preview_result = invoke(["preview", str(tmp_path), "--clients", "none"], tmp_path)
    assert preview_result.exit_code == 0, preview_result.output
    assert "review" in preview_result.output
    assert "Risky changed instruction." in preview_result.output


def test_status_and_preview_report_managed_script_hash_changes(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    script_file = tmp_path / ".agents/scripts/check-agent-assets.sh"
    script_file.write_text(
        script_file.read_text(encoding="utf-8") + "\necho unsafe-script-change\n",
        encoding="utf-8",
    )

    status_result = invoke(["status", str(tmp_path), "--json"], tmp_path)
    assert status_result.exit_code == 0, status_result.output
    status_payload = json.loads(status_result.output)
    status_text = json.dumps(status_payload)
    assert "trusted hash mismatch" in status_text
    assert_output_mentions_path(status_text, ".agents/scripts/check-agent-assets.sh")

    script_check = invoke(["check", str(tmp_path), "--checks", "scripts"], tmp_path)
    assert script_check.exit_code == 1, script_check.output
    assert "trusted hash mismatch" in script_check.output

    preview_result = invoke(["preview", str(tmp_path), "--clients", "none"], tmp_path)
    assert preview_result.exit_code == 0, preview_result.output
    assert "unsafe-script-change" in preview_result.output


def test_preview_and_upgrade_diff_installed_protocol(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    outcome_file = tmp_path / ".agents/rules/outcome-boundary.md"
    original = outcome_file.read_text(encoding="utf-8")
    outcome_file.write_text("# Local stale rule\n", encoding="utf-8")

    project_file = tmp_path / ".agents/project/README.md"
    project_file.write_text("# User Project Rules\n", encoding="utf-8")
    extra_file = tmp_path / ".agents/local-note.md"
    extra_file.write_text("keep me\n", encoding="utf-8")
    (tmp_path / ".agents/agent-feed.json").unlink()

    preview_result = invoke(["preview", str(tmp_path), "--clients", "none"], tmp_path)
    assert preview_result.exit_code == 0, preview_result.output
    assert "would update" in preview_result.output
    assert "would create" in preview_result.output
    assert "Local stale rule" in preview_result.output
    assert ".agents/project/README.md" not in preview_result.output

    upgrade_result = invoke(["upgrade", str(tmp_path), "--clients", "none"], tmp_path)
    assert upgrade_result.exit_code == 0, upgrade_result.output
    assert "Diff details:" in upgrade_result.output
    assert outcome_file.read_text(encoding="utf-8") == original
    assert (tmp_path / ".agents/agent-feed.json").exists()
    assert project_file.read_text(encoding="utf-8") == "# User Project Rules\n"
    assert extra_file.exists()


def test_init_can_select_node_verification_profile(tmp_path: Path) -> None:
    init_result = invoke(
        [
            "init",
            str(tmp_path),
            "--project-name",
            "Node Example",
            "--clients",
            "none",
            "--profile",
            "node",
            "-y",
        ],
        tmp_path,
    )
    assert init_result.exit_code == 0, init_result.output

    script = (tmp_path / ".agents/scripts/verify-agent-dev.sh").read_text(encoding="utf-8")
    metadata = json.loads((tmp_path / ".agents/agent-feed.json").read_text(encoding="utf-8"))
    assert metadata["verification_profile"] == "node"
    assert "Reads .agents/agent-feed.json verification_profile at runtime." in script
    assert 'NODE_PM="pnpm"' in script
    assert 'NODE_PM="npm"' in script
    assert not (tmp_path / ".agents/project/verification-profile.md").exists()


def test_custom_verification_profile_uses_project_owned_command_hook(tmp_path: Path) -> None:
    init_result = invoke(
        [
            "init",
            str(tmp_path),
            "--project-name",
            "Custom Example",
            "--clients",
            "none",
            "--profile",
            "custom",
            "-y",
        ],
        tmp_path,
    )
    assert init_result.exit_code == 0, init_result.output

    verify_script = tmp_path / ".agents/scripts/verify-agent-dev.sh"
    hook_file = tmp_path / ".agents/project/verification-commands.sh"

    metadata = json.loads((tmp_path / ".agents/agent-feed.json").read_text(encoding="utf-8"))
    assert metadata["verification_profile"] == "custom"
    assert ".agents/project/verification-commands.sh" in verify_script.read_text(encoding="utf-8")
    assert hook_file.exists()
    hook_text = hook_file.read_text(encoding="utf-8")
    verify_text = verify_script.read_text(encoding="utf-8")
    assert "AF_RED" in verify_text
    assert 'path_text ".agents/agent-feed.json"' in verify_text
    assert 'command_text "agent-feed config set verification_profile' in verify_text
    assert "run_project_code_checks" in hook_text
    assert hook_text.startswith("#!/usr/bin/env sh\n")
    assert "\n# Project-owned custom code verification hook.\n" in hook_text
    assert (
        '# when .agents/agent-feed.json sets verification_profile to "custom".\n' in hook_text
    )
    assert "red=$(printf '\\033[31m')" in hook_text
    assert "Edit %s.agents/project/verification-commands.sh" in hook_text

    failing_code_gate = subprocess.run(
        ["sh", str(verify_script), "code"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert failing_code_gate.returncode == 1
    assert "Custom code verification is not configured yet" in failing_code_gate.stderr

    hook_file.write_text(
        "\n".join(
            [
                "#!/usr/bin/env sh",
                "run_project_code_checks() {",
                "  printf '%s\\n' custom-code-ok > custom-code-check.txt",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    passing_code_gate = subprocess.run(
        ["sh", str(verify_script), "code"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert passing_code_gate.returncode == 0, passing_code_gate.stderr
    assert (tmp_path / "custom-code-check.txt").read_text(encoding="utf-8").strip() == (
        "custom-code-ok"
    )


def test_session_state_check_validates_handoff_cards(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    state_dir = tmp_path / ".agents/session-state"
    session_file = state_dir / "codex-example.json"
    session_rel = ".agents/session-state/codex-example.json"
    session_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session": {
                    "id": "codex-example",
                    "label": "Example session",
                    "updated_at": "2026-05-01T02:10:33+0800",
                    "thread_id": "",
                    "title_history": ["Example session"],
                },
                "current_task": {
                    "goal": "Keep handoff state compact.",
                    "current_step": "Validate the new schema.",
                    "stop_condition": "Session check accepts a valid handoff card.",
                    "next_action": "Run docs checks.",
                },
                "carry_forwards": [
                    {
                        "id": "cli-boundary",
                        "type": "decision",
                        "content": "Do not merge public commands without a CLI contract decision.",
                        "why_keep": "Losing this would cause unsafe command cleanup.",
                        "expires_when": "Command boundary review is accepted or deferred.",
                        "updated_at": "2026-05-01T02:10:33+0800",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (state_dir / "current.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-05-01T02:10:33+0800",
                "active_session_file": session_rel,
                "sessions": [
                    {
                        "file": session_rel,
                        "label": "Example session",
                        "updated_at": "2026-05-01T02:10:33+0800",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    valid_result = invoke(["check", str(tmp_path), "--checks", "session"], tmp_path)
    assert valid_result.exit_code == 0, valid_result.output

    invalid_data = json.loads(session_file.read_text(encoding="utf-8"))
    invalid_data["carry_forwards"] = [
        {
            "id": f"item-{index}",
            "type": "decision",
            "content": "x",
            "why_keep": "x",
            "expires_when": "x",
            "updated_at": "2026-05-01T02:10:33+0800",
        }
        for index in range(8)
    ]
    invalid_data["carry_forwards"][0].pop("why_keep")
    session_file.write_text(json.dumps(invalid_data, indent=2), encoding="utf-8")

    invalid_result = invoke(
        ["check", str(tmp_path), "--checks", "session", "--json"],
        tmp_path,
    )
    assert invalid_result.exit_code == 1, invalid_result.output
    assert "carry_forwards must contain at most 7 items" in invalid_result.output
    assert "missing carry_forwards[0].why_keep" in invalid_result.output


def test_session_state_check_warns_on_expired_iso_topics(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    state_dir = tmp_path / ".agents/session-state"
    session_file = state_dir / "codex-expired.json"
    session_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session": {
                    "id": "codex-expired",
                    "label": "Expired session",
                    "updated_at": "2026-05-01T02:10:33+0800",
                },
                "current_task": {
                    "goal": "Keep handoff state compact.",
                    "current_step": "Detect expired carry-forward topics.",
                    "stop_condition": "Session check warns when an ISO expiry is already past.",
                    "next_action": "Clean stale carry-forwards before the next handoff.",
                },
                "carry_forwards": [
                    {
                        "id": "stale-topic",
                        "type": "handoff",
                        "content": "Old temporary topic that should have been cleaned already.",
                        "why_keep": "This should now be a warning, not hidden stale state.",
                        "expires_when": "2020-01-01",
                        "updated_at": "2026-05-01T02:10:33+0800",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = invoke(["check", str(tmp_path), "--checks", "session", "--json"], tmp_path)
    assert result.exit_code == 0, result.output
    assert '"ok": true' in result.output
    assert "appears expired by expires_when (2020-01-01)" in result.output

    text_result = invoke(["check", str(tmp_path), "--checks", "session"], tmp_path)
    assert text_result.exit_code == 0, text_result.output
    assert "Checks Passed With Warnings" in text_result.output
    assert "Review the warnings above before the final handoff" in text_result.output


def test_config_set_updates_session_schema_and_check_limit(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    preview = invoke(
        [
            "config",
            "set",
            "--path",
            str(tmp_path),
            "--dry-run",
            "settings.session_state.max_carry_forwards",
            "3",
        ],
        tmp_path,
    )
    assert preview.exit_code == 0, preview.output
    assert "settings.session_state.max_carry_forwards" not in preview.output
    assert '"max_carry_forwards": 3' in preview.output

    result = invoke(
        [
            "config",
            "set",
            "--path",
            str(tmp_path),
            "settings.session_state.max_carry_forwards",
            "3",
        ],
        tmp_path,
    )
    assert result.exit_code == 0, result.output
    schema = json.loads(
        (tmp_path / ".agents/session-state/schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["carry_forwards"]["maxItems"] == 3

    session_file = tmp_path / ".agents/session-state/codex-example.json"
    session_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session": {
                    "id": "codex-example",
                    "label": "Example session",
                    "updated_at": "2026-05-01T02:10:33+0800",
                },
                "current_task": {
                    "goal": "Keep handoff state compact.",
                    "current_step": "Validate custom max.",
                    "stop_condition": "Session check uses configured max.",
                    "next_action": "Run docs checks.",
                },
                "carry_forwards": [
                    {
                        "id": f"item-{index}",
                        "type": "decision",
                        "content": "x",
                        "why_keep": "x",
                        "expires_when": "x",
                        "updated_at": "2026-05-01T02:10:33+0800",
                    }
                    for index in range(4)
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    check = invoke(["check", str(tmp_path), "--checks", "session", "--json"], tmp_path)
    assert check.exit_code == 1, check.output
    assert "carry_forwards must contain at most 3 items" in check.output


def test_config_set_updates_skill_metadata_defaults(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--project-name", "Example", "--profile", "python"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    skill_dir = tmp_path / ".agents/skills/local-helper"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "\n".join(
            [
                "---",
                "name: local-helper",
                "description: Use when testing configured defaults.",
                "---",
                "",
                "# Local Helper",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = invoke(
        [
            "config",
            "set",
            "--path",
            str(tmp_path),
            "settings.skills",
            '{"default_import_source":"local","default_import_trust":"reviewed"}',
        ],
        tmp_path,
    )
    assert result.exit_code == 0, result.output
    skill_text = skill_file.read_text(encoding="utf-8")
    assert "source: local" in skill_text
    assert "trust: reviewed" in skill_text
    index_text = (tmp_path / ".agents/skills/README.md").read_text(encoding="utf-8")
    assert (
        "| `local-helper` | Use when testing configured defaults. | `local` | `reviewed` |"
        in index_text
    )


def test_config_set_updates_claude_required_snippets(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--clients", "claude", "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    (tmp_path / "AGENTS.md").write_text("# Local agent entry\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")

    check_before_set = invoke(["check", str(tmp_path), "--checks", "claude"], tmp_path)
    assert check_before_set.exit_code == 1, check_before_set.output
    assert "CLAUDE.md must contain .claude/skills" in check_before_set.output

    result = invoke(
        [
            "config",
            "set",
            "--path",
            str(tmp_path),
            "settings.claude.required_snippets",
            '["@AGENTS.md"]',
        ],
        tmp_path,
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# Local agent entry\n"
    check_after_set = invoke(["check", str(tmp_path), "--checks", "claude"], tmp_path)
    assert check_after_set.exit_code == 0, check_after_set.output


def test_init_backs_up_existing_ai_instruction_content(tmp_path: Path) -> None:
    existing_skill = tmp_path / ".agents/skills/old-skill/SKILL.md"
    existing_skill.parent.mkdir(parents=True)
    existing_skill.write_text("---\nname: old-skill\n---\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Old AI rules\n", encoding="utf-8")

    result = invoke(
        [
            "init",
            str(tmp_path),
            "--project-name",
            "Example",
            "--profile",
            "python",
            "--force-generated",
        ],
        tmp_path,
    )
    assert result.exit_code == 0, result.output
    assert "backup" in result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert "Example AI Development Instructions" in (tmp_path / "AGENTS.md").read_text(
        encoding="utf-8"
    )
    backup_dirs = list((tmp_path / ".feed-backup").iterdir())
    assert len(backup_dirs) == 1
    backup_dir = backup_dirs[0]
    assert (backup_dir / "AGENTS.md").read_text(encoding="utf-8") == "# Old AI rules\n"
    assert (backup_dir / ".agents/skills/old-skill/SKILL.md").exists()
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "legacy-ai-instruction-backup"
    assert manifest["project_domain_scaffolded"] is True
    guide = (backup_dir / "AI_MIGRATION_GUIDE.md").read_text(encoding="utf-8")
    assert "must follow these rules" in guide
    assert "Stop and ask the user" in guide


def test_init_dry_run_previews_legacy_adapter_backup_without_conflict(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# Old Claude rules\n", encoding="utf-8")
    cursor_rule = tmp_path / ".cursor/rules/custom.mdc"
    cursor_rule.parent.mkdir(parents=True)
    cursor_rule.write_text("# Old Cursor rules\n", encoding="utf-8")

    result = invoke(
        [
            "init",
            str(tmp_path),
            "--project-name",
            "Example",
            "--profile",
            "python",
            "--dry-run",
        ],
        tmp_path,
    )

    assert result.exit_code == 0, result.output
    assert "would backup" in result.output
    assert "CLAUDE.md is missing required Agent Feed references" not in result.output
    assert ".cursor/rules/agent-feed.mdc is not a managed Agent Feed adapter" not in result.output
    assert (tmp_path / "CLAUDE.md").exists()
    assert cursor_rule.exists()
    assert not (tmp_path / ".feed-backup").exists()


def test_init_refuses_already_installed_project(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--clients", "codex", "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    project_readme = tmp_path / ".agents/project/README.md"
    project_readme.write_text("# User maintained project rules\n", encoding="utf-8")

    second_result = invoke(["init", str(tmp_path), "--profile", "python", "-y"], tmp_path)
    assert second_result.exit_code == 3, second_result.output
    assert "already installed" in second_result.output
    assert not (tmp_path / ".feed-backup").exists()
    assert project_readme.read_text(encoding="utf-8") == "# User maintained project rules\n"


def test_sync_refuses_claude_md_without_required_agent_feed_references(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--clients", "codex", "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    (tmp_path / "CLAUDE.md").write_text("# user-owned claude instructions\n", encoding="utf-8")
    claude_result = invoke(
        ["sync", str(tmp_path), "--clients", "claude", "--force-generated", "--no-input"],
        tmp_path,
    )
    assert claude_result.exit_code == 3, claude_result.output
    assert "missing required Agent Feed references" in claude_result.output
    assert "# user-owned claude instructions" in (tmp_path / "CLAUDE.md").read_text(
        encoding="utf-8"
    )


def test_init_keeps_existing_claude_md_when_required_references_exist(tmp_path: Path) -> None:
    user_claude = "\n".join(
        [
            "# Existing Claude Instructions",
            "",
            "@AGENTS.md",
            "",
            "Use `.claude/skills/` and keep `.agents/` canonical.",
            "",
        ]
    )
    (tmp_path / "CLAUDE.md").write_text(user_claude, encoding="utf-8")

    init_result = invoke(["init", str(tmp_path), "--clients", "claude", "--profile", "python", "-y"], tmp_path)

    assert init_result.exit_code == 0, init_result.output
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == user_claude
    assert (tmp_path / ".claude/skills/project-development/SKILL.md").exists()


def test_sync_keeps_user_owned_claude_md_when_required_references_exist(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--clients", "codex", "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    user_claude = "\n".join(
        [
            "# Team Claude Notes",
            "",
            "@AGENTS.md",
            "",
            "Use `.claude/skills/` for Claude Code skill discovery.",
            "Rules stay in `.agents/`.",
            "",
        ]
    )
    (tmp_path / "CLAUDE.md").write_text(user_claude, encoding="utf-8")

    claude_result = invoke(
        ["sync", str(tmp_path), "--clients", "claude", "--force-generated", "--no-input"],
        tmp_path,
    )
    assert claude_result.exit_code == 0, claude_result.output
    assert "contains required Agent Feed" in claude_result.output
    assert "references" in claude_result.output
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == user_claude
    assert (tmp_path / ".claude/skills/project-review/SKILL.md").exists()


def test_check_accepts_user_owned_claude_md_with_required_references(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--clients", "claude", "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    (tmp_path / "CLAUDE.md").write_text(
        "\n".join(
            [
                "# Local Claude Instructions",
                "",
                "@AGENTS.md",
                "",
                "Read `.claude/skills/` and keep `.agents/` canonical.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = invoke(["check", str(tmp_path), "--checks", "claude"], tmp_path)
    assert result.exit_code == 0, result.output


def test_sync_refuses_unmanaged_cursor_adapter_even_with_force(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--clients", "codex", "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    cursor_file = tmp_path / ".cursor/rules/agent-feed.mdc"
    cursor_file.parent.mkdir(parents=True)
    cursor_file.write_text("user-owned cursor rule\n", encoding="utf-8")
    cursor_result = invoke(
        ["sync", str(tmp_path), "--clients", "cursor", "--force-generated", "--no-input"],
        tmp_path,
    )
    assert cursor_result.exit_code == 3, cursor_result.output
    assert "unmanaged" in cursor_result.output
    assert cursor_file.read_text(encoding="utf-8") == "user-owned cursor rule\n"


def test_check_requires_cursor_rule_to_import_agents_md(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    cursor_file = tmp_path / ".cursor/rules/agent-feed.mdc"
    cursor_file.write_text(
        cursor_file.read_text(encoding="utf-8").replace("@AGENTS.md\n\n", ""),
        encoding="utf-8",
    )

    result = invoke(["check", str(tmp_path), "--checks", "cursor"], tmp_path)
    assert result.exit_code == 1, result.output
    assert "Cursor adapter must import @AGENTS.md" in result.output


def test_uninstall_removes_only_managed_assets(tmp_path: Path) -> None:
    init_result = invoke(["init", str(tmp_path), "--profile", "python", "-y"], tmp_path)
    assert init_result.exit_code == 0, init_result.output
    user_file = tmp_path / ".claude/user-note.md"
    user_file.write_text("keep me\n", encoding="utf-8")

    dry_run = invoke(["uninstall", str(tmp_path), "--dry-run"], tmp_path)
    assert dry_run.exit_code == 0, dry_run.output
    assert "would delete" in dry_run.output
    assert (tmp_path / "AGENTS.md").exists()

    result = invoke(["uninstall", str(tmp_path), "-y"], tmp_path)
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / ".cursor/rules/agent-feed.mdc").exists()
    assert user_file.exists()


def test_uninstall_skips_unmanaged_assets(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# user owned\n", encoding="utf-8")
    result = invoke(["uninstall", str(tmp_path), "-y"], tmp_path)
    assert result.exit_code == 0, result.output
    assert "unmanaged" in result.output
    assert (tmp_path / "AGENTS.md").exists()
