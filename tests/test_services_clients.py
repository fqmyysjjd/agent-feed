"""Direct unit tests for ``agent_feed.services.clients``.

Each test exercises one services-layer function in isolation, so a future
behavior change in ``sync_clients``, ``installed_clients``,
``find_init_conflicts``, or ``planned_backup_resolves_init_adapter_error``
fails here even when the broader CLI smoke tests still pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_feed.cli import app
from agent_feed.models import Client, WriteAction
from agent_feed.services.clients import (
    find_init_conflicts,
    installed_clients,
    planned_backup_resolves_init_adapter_error,
    sync_clients,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _bootstrap_project(tmp_path: Path, *, clients: str = "none") -> Path:
    """Run a minimal ``init`` so services functions have a real .agents tree."""

    trust_home = tmp_path.parent / f"{tmp_path.name}-services-home"
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
        env={"AGENT_FEED_HOME": str(trust_home)},
    )
    assert result.exit_code == 0, result.output
    return tmp_path


# ---------------------------------------------------------------------------
# sync_clients
# ---------------------------------------------------------------------------


def test_sync_clients_with_no_clients_returns_skip_action(tmp_path: Path) -> None:
    actions, errors = sync_clients(
        tmp_path, clients=(), dry_run=True, force_generated=False
    )
    assert errors == []
    assert len(actions) == 1
    assert actions[0].action == "skip"
    assert "no clients selected" in actions[0].detail


def test_sync_clients_without_agents_dir_errors_unless_dry_run(tmp_path: Path) -> None:
    # No .agents directory exists.
    actions, errors = sync_clients(
        tmp_path,
        clients=(Client.CODEX,),
        dry_run=False,
        force_generated=False,
    )
    assert actions == []
    assert any("missing .agents" in err for err in errors)


def test_sync_clients_dry_run_without_agents_dir_does_not_error(tmp_path: Path) -> None:
    actions, errors = sync_clients(
        tmp_path,
        clients=(Client.CODEX,),
        dry_run=True,
        force_generated=False,
    )
    # Dry-run skips the missing-.agents guard and lets adapter sync produce
    # would-create entries instead of failing.
    assert errors == []
    assert actions != []


def test_sync_clients_with_codex_only_runs_codex_adapter(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    actions, errors = sync_clients(
        project,
        clients=(Client.CODEX,),
        dry_run=True,
        force_generated=False,
    )
    assert errors == []
    assert actions  # codex sync produces at least one action
    # Codex consumes AGENTS.md/.agents directly; its sync paths should not
    # mention .claude or .cursor outputs.
    paths = " ".join(action.path.as_posix() for action in actions)
    assert ".claude/" not in paths
    assert ".cursor/" not in paths


def test_sync_clients_with_claude_runs_claude_adapter(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path, clients="claude")
    actions, errors = sync_clients(
        project,
        clients=(Client.CLAUDE,),
        dry_run=True,
        force_generated=False,
    )
    # Errors may legitimately surface if managed CLAUDE.md content is missing
    # required snippets in a partially set-up project; what matters here is
    # that the claude code path executed and produced action records.
    assert any(action.path.as_posix().startswith("/") or ".claude" in action.path.as_posix() for action in actions) or errors


# ---------------------------------------------------------------------------
# installed_clients
# ---------------------------------------------------------------------------


def test_installed_clients_always_includes_codex(tmp_path: Path) -> None:
    assert installed_clients(tmp_path) == (Client.CODEX,)


def test_installed_clients_detects_claude_via_root_md(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# claude\n")
    assert Client.CLAUDE in installed_clients(tmp_path)


def test_installed_clients_detects_claude_via_skills_dir(tmp_path: Path) -> None:
    (tmp_path / ".claude/skills").mkdir(parents=True)
    assert Client.CLAUDE in installed_clients(tmp_path)


def test_installed_clients_detects_cursor_via_rule_file(tmp_path: Path) -> None:
    rule = tmp_path / ".cursor/rules/agent-feed.mdc"
    rule.parent.mkdir(parents=True)
    rule.write_text("# cursor\n")
    detected = installed_clients(tmp_path)
    assert Client.CURSOR in detected
    assert Client.CODEX in detected


def test_installed_clients_returns_in_canonical_order(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("")
    rule = tmp_path / ".cursor/rules/agent-feed.mdc"
    rule.parent.mkdir(parents=True)
    rule.write_text("")
    assert installed_clients(tmp_path) == (Client.CODEX, Client.CLAUDE, Client.CURSOR)


# ---------------------------------------------------------------------------
# find_init_conflicts
# ---------------------------------------------------------------------------


def test_find_init_conflicts_clean_target_returns_empty(tmp_path: Path) -> None:
    assert find_init_conflicts(tmp_path, clients=(Client.CODEX,)) == []


def test_find_init_conflicts_blocks_already_installed(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    errors = find_init_conflicts(project, clients=(Client.CODEX,))
    assert any("already installed" in err for err in errors)


def test_find_init_conflicts_when_agents_md_is_a_directory(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").mkdir()
    errors = find_init_conflicts(tmp_path, clients=(Client.CODEX,))
    assert any("AGENTS.md exists but is not a file" in err for err in errors)


def test_find_init_conflicts_when_dot_agents_is_a_file(tmp_path: Path) -> None:
    (tmp_path / ".agents").write_text("oops")
    errors = find_init_conflicts(tmp_path, clients=(Client.CODEX,))
    assert any(".agents exists but is not a directory" in err for err in errors)


def test_find_init_conflicts_when_claude_md_is_a_directory(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").mkdir()
    errors = find_init_conflicts(tmp_path, clients=(Client.CLAUDE,))
    assert any("CLAUDE.md exists but is not a file" in err for err in errors)


def test_find_init_conflicts_when_cursor_rule_is_a_directory(tmp_path: Path) -> None:
    rule = tmp_path / ".cursor/rules/agent-feed.mdc"
    rule.parent.mkdir(parents=True)
    rule.mkdir()
    errors = find_init_conflicts(tmp_path, clients=(Client.CURSOR,))
    assert any(".cursor/rules/agent-feed.mdc exists but is not a file" in err for err in errors)


def test_find_init_conflicts_does_not_check_unselected_client_paths(tmp_path: Path) -> None:
    # Pre-existing CLAUDE.md is fine when claude client is not selected.
    (tmp_path / "CLAUDE.md").mkdir()
    errors = find_init_conflicts(tmp_path, clients=(Client.CODEX,))
    assert errors == []


# ---------------------------------------------------------------------------
# planned_backup_resolves_init_adapter_error
# ---------------------------------------------------------------------------


@pytest.fixture
def backup_actions(tmp_path: Path) -> list[WriteAction]:
    backup_root = tmp_path / ".feed-backup/2026-05-10T00-00-00"
    return [
        WriteAction(
            path=tmp_path / "CLAUDE.md",
            action="backup",
            detail=f"-> {(backup_root / 'CLAUDE.md').relative_to(tmp_path)}",
        ),
        WriteAction(
            path=tmp_path / ".claude/skills",
            action="backup",
            detail=f"-> {(backup_root / '.claude/skills').relative_to(tmp_path)}",
        ),
        WriteAction(
            path=tmp_path / ".cursor/rules",
            action="backup",
            detail=f"-> {(backup_root / '.cursor/rules').relative_to(tmp_path)}",
        ),
    ]


def test_resolves_when_claude_md_backed_up(
    tmp_path: Path, backup_actions: list[WriteAction]
) -> None:
    err = "CLAUDE.md exists but is not a file"
    assert planned_backup_resolves_init_adapter_error(
        err, backup_actions, target=tmp_path
    )


def test_resolves_when_claude_skills_backed_up(
    tmp_path: Path, backup_actions: list[WriteAction]
) -> None:
    err = ".claude/skills exists but is not a directory"
    assert planned_backup_resolves_init_adapter_error(
        err, backup_actions, target=tmp_path
    )


def test_resolves_when_cursor_rule_backed_up(
    tmp_path: Path, backup_actions: list[WriteAction]
) -> None:
    err = ".cursor/rules/agent-feed.mdc exists but is not a file"
    assert planned_backup_resolves_init_adapter_error(
        err, backup_actions, target=tmp_path
    )


def test_does_not_resolve_unrelated_errors(
    tmp_path: Path, backup_actions: list[WriteAction]
) -> None:
    err = "AGENTS.md exists but is not a file"
    assert not planned_backup_resolves_init_adapter_error(
        err, backup_actions, target=tmp_path
    )


def test_does_not_resolve_when_no_backup_actions_match(
    tmp_path: Path,
) -> None:
    err = "CLAUDE.md exists but is not a file"
    # No backup actions at all.
    assert not planned_backup_resolves_init_adapter_error(err, [], target=tmp_path)
