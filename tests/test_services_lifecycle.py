"""Direct unit tests for ``agent_feed.services.lifecycle``.

These tests cover the project lifecycle orchestrators (``init_project``,
``preview_project``, ``preview_actions``, ``upgrade_project``,
``downgrade_preflight_errors``, ``init_backup_dir``, ``_downgrade_warning``)
without going through the Typer command runner.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import agent_feed.services.lifecycle as lifecycle
from agent_feed.cli import app
from agent_feed.models import Client, VerificationProfile, WriteAction
from agent_feed.services.lifecycle import (
    _downgrade_warning,
    downgrade_preflight_errors,
    init_backup_dir,
    init_project,
    preview_actions,
    preview_project,
    upgrade_project,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _trust_home(tmp_path: Path) -> Path:
    return tmp_path.parent / f"{tmp_path.name}-services-home"


def _bootstrap(tmp_path: Path, *, clients: str = "none") -> Path:
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--project-name",
            "Example",
            "--clients",
            clients,
            "--profile",
            "python",
        ],
        env={"AGENT_FEED_HOME": str(_trust_home(tmp_path))},
    )
    assert result.exit_code == 0, result.output
    return tmp_path


# ---------------------------------------------------------------------------
# init_project
# ---------------------------------------------------------------------------


def test_init_project_dry_run_creates_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_FEED_HOME", str(_trust_home(tmp_path)))
    actions, errors = init_project(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
        dry_run=True,
        force_generated=False,
    )
    assert errors == []
    assert actions  # plan is non-empty
    # No on-disk effect.
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".agents").exists()


def test_init_project_writes_canonical_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_FEED_HOME", str(_trust_home(tmp_path)))
    actions, errors = init_project(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
        dry_run=False,
        force_generated=False,
    )
    assert errors == []
    assert actions
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".agents/agent-feed.json").is_file()


def test_init_project_blocks_when_already_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(tmp_path)
    monkeypatch.setenv("AGENT_FEED_HOME", str(_trust_home(tmp_path)))
    actions, errors = init_project(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
        dry_run=True,
        force_generated=False,
    )
    assert actions == []
    assert any("already installed" in err for err in errors)


# ---------------------------------------------------------------------------
# preview_project
# ---------------------------------------------------------------------------


def test_preview_project_returns_would_create_actions_for_fresh_target(tmp_path: Path) -> None:
    actions = preview_project(
        tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
    )
    assert actions
    # All canonical-template entries should be "would create" since the
    # target was empty.
    template_creates = [
        a
        for a in actions
        if a.path == tmp_path / "AGENTS.md"
        or (a.path.is_relative_to(tmp_path / ".agents") and a.action != "ok")
    ]
    assert template_creates
    assert all(a.action == "would create" for a in template_creates)


def test_preview_project_marks_existing_paths_as_would_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(tmp_path)
    actions = preview_project(
        tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
    )
    update_actions = [a for a in actions if a.action == "would update"]
    create_actions = [a for a in actions if a.action == "would create"]
    assert update_actions  # at least one canonical asset already exists
    # Bootstrapped project should have all canonical assets present, so most
    # actions should be updates rather than creates.
    assert len(update_actions) >= len(create_actions)


# ---------------------------------------------------------------------------
# preview_actions (router between init-preview and upgrade-preview)
# ---------------------------------------------------------------------------


def test_preview_actions_routes_uninstalled_target_to_init_preview(tmp_path: Path) -> None:
    actions, errors = preview_actions(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
    )
    assert errors == []
    assert actions
    # An uninstalled target's canonical assets must come back as "would create".
    template_creates = [
        a for a in actions if a.path == tmp_path / "AGENTS.md"
    ]
    assert template_creates
    assert all(a.action == "would create" for a in template_creates)


def test_preview_actions_routes_installed_target_to_upgrade_preview(
    tmp_path: Path,
) -> None:
    _bootstrap(tmp_path)
    actions, errors = preview_actions(
        target=tmp_path,
        project_name=None,
        clients=None,
        verification_profile=None,
    )
    assert errors == []
    assert actions  # at least the trust preview row is appended


def test_preview_actions_uses_default_verification_profile_when_unspecified(
    tmp_path: Path,
) -> None:
    actions, errors = preview_actions(
        target=tmp_path,
        project_name=None,
        clients=None,
        verification_profile=None,
    )
    assert errors == []
    assert actions


# ---------------------------------------------------------------------------
# upgrade_project
# ---------------------------------------------------------------------------


def test_upgrade_project_dry_run_does_not_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(tmp_path)
    before = (tmp_path / "AGENTS.md").read_text()

    monkeypatch.setenv("AGENT_FEED_HOME", str(_trust_home(tmp_path)))
    actions, errors = upgrade_project(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
        dry_run=True,
    )
    assert errors == []
    assert actions
    assert (tmp_path / "AGENTS.md").read_text() == before


def test_upgrade_project_is_idempotent_after_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(tmp_path)
    monkeypatch.setenv("AGENT_FEED_HOME", str(_trust_home(tmp_path)))
    first_actions, first_errors = upgrade_project(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
        dry_run=False,
    )
    assert first_errors == []
    second_actions, second_errors = upgrade_project(
        target=tmp_path,
        project_name="Example",
        clients=(Client.CODEX,),
        verification_profile=VerificationProfile.PYTHON,
        dry_run=False,
    )
    assert second_errors == []
    # On the second pass everything should be a no-op or skip.
    write_actions = [a for a in second_actions if a.action in {"create", "update"}]
    assert not write_actions


# ---------------------------------------------------------------------------
# init_backup_dir
# ---------------------------------------------------------------------------


def test_init_backup_dir_returns_first_timestamped_directory(tmp_path: Path) -> None:
    timestamp = "2026-05-10T00-00-00"
    actions = [
        WriteAction(
            path=tmp_path / "CLAUDE.md",
            action="backup",
            detail=f"-> .feed-backup/{timestamp}/CLAUDE.md",
        ),
        WriteAction(
            path=tmp_path / ".claude/skills",
            action="backup",
            detail=f"-> .feed-backup/{timestamp}/claude/skills",
        ),
    ]
    backup_dir = init_backup_dir(actions, target=tmp_path)
    assert backup_dir == tmp_path / ".feed-backup" / timestamp


def test_init_backup_dir_returns_none_when_no_backup_actions(tmp_path: Path) -> None:
    actions = [WriteAction(path=tmp_path / "AGENTS.md", action="create")]
    assert init_backup_dir(actions, target=tmp_path) is None


def test_init_backup_dir_ignores_actions_outside_feed_backup(tmp_path: Path) -> None:
    actions = [
        WriteAction(
            path=tmp_path / "elsewhere",
            action="backup",
            detail="-> some/other/place",
        )
    ]
    assert init_backup_dir(actions, target=tmp_path) is None


# ---------------------------------------------------------------------------
# _downgrade_warning
# ---------------------------------------------------------------------------


def test_downgrade_warning_returns_none_when_versions_align(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bootstrap(tmp_path)
    monkeypatch.setattr(lifecycle, "downgrade_warnings", lambda _target: [])
    assert _downgrade_warning(tmp_path) is None


def test_downgrade_warning_returns_review_action_when_warnings_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        lifecycle, "downgrade_warnings", lambda _target: ["older CLI; risk"]
    )
    action = _downgrade_warning(tmp_path)
    assert action is not None
    assert action.action == "review"
    assert action.path == tmp_path / ".agents/agent-feed.json"
    assert "older CLI" in action.detail


# ---------------------------------------------------------------------------
# downgrade_preflight_errors
# ---------------------------------------------------------------------------


def test_downgrade_preflight_errors_returns_empty_when_versions_aligned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle, "installed_version", lambda _target: None)
    assert (
        downgrade_preflight_errors(target=tmp_path, interactive=False) == []
    )


def test_downgrade_preflight_errors_returns_two_lines_when_older_cli_non_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle, "installed_version", lambda _target: "999.999.999")
    monkeypatch.setattr(lifecycle, "is_older_version", lambda cli, project: True)

    errors = downgrade_preflight_errors(target=tmp_path, interactive=False)

    assert len(errors) == 2
    assert "managed by Agent Feed 999.999.999" in errors[0]
    assert "--allow-downgrade" in errors[1]


def test_downgrade_preflight_errors_clears_when_user_confirms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle, "installed_version", lambda _target: "999.999.999")
    monkeypatch.setattr(lifecycle, "is_older_version", lambda cli, project: True)
    monkeypatch.setattr(lifecycle, "prompt_confirm", lambda _msg, default=False: True)

    assert downgrade_preflight_errors(target=tmp_path, interactive=True) == []


def test_downgrade_preflight_errors_blocks_when_user_declines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle, "installed_version", lambda _target: "999.999.999")
    monkeypatch.setattr(lifecycle, "is_older_version", lambda cli, project: True)
    monkeypatch.setattr(lifecycle, "prompt_confirm", lambda _msg, default=False: False)

    errors = downgrade_preflight_errors(target=tmp_path, interactive=True)
    assert len(errors) == 2
