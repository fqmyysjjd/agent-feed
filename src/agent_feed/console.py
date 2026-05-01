"""Rich console output for Agent Feed."""

from __future__ import annotations

import json
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_feed import __version__
from agent_feed.models import CheckReport, ProjectStatus, WriteAction


console = Console()


def print_welcome() -> None:
    console.print(
        Panel.fit(
            "[bold]Agent Feed[/bold]\n"
            "Install and maintain a reusable AI engineering protocol.\n\n"
            "[dim]Typical flow[/dim]\n"
            "  agent-feed init\n"
            "  agent-feed update\n"
            "  agent-feed check\n"
            "  agent-feed sync",
            title=f"agent-feed {__version__}",
            border_style="cyan",
        )
    )


def print_write_plan(actions: list[WriteAction]) -> None:
    table = Table(title="Write Plan")
    table.add_column("Action", style="cyan")
    table.add_column("Path")
    table.add_column("Detail", style="dim")
    for action in actions:
        table.add_row(action.action, str(action.path), action.detail)
    console.print(table)

    for action in actions:
        if action.diff:
            console.print(
                Panel(
                    action.diff,
                    title=f"Diff: {action.path}",
                    border_style="yellow",
                    expand=False,
                )
            )


def print_check_report(report: CheckReport, *, as_json: bool) -> None:
    if as_json:
        payload = {
            "target": str(report.target),
            "checks": [check.value for check in report.checks],
            "ok": report.ok,
            "errors": report.errors,
            "warnings": report.warnings,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if report.ok:
        console.print(
            Panel.fit(
                f"[green]Checks passed[/green]\n"
                f"Target: {report.target}\n"
                f"Scope: {', '.join(check.value for check in report.checks)}",
                border_style="green",
            )
        )
    else:
        table = Table(title="Check Failures")
        table.add_column("Type", style="red")
        table.add_column("Message")
        for error in report.errors:
            table.add_row("error", error)
        for warning in report.warnings:
            table.add_row("warning", warning)
        console.print(table)


def print_status(status: ProjectStatus, *, as_json: bool) -> None:
    if as_json:
        payload = asdict(status)
        payload["target"] = str(status.target)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"Agent Feed Status: {status.target}")
    table.add_column("Area")
    table.add_column("Source")
    table.add_column("State")
    table.add_row("Canonical", "AGENTS.md + .agents/", _state(status.canonical_installed))
    table.add_row(
        "Codex",
        "AGENTS.md + .agents/skills (direct)",
        _state(status.codex_ready),
    )
    table.add_row(
        "Claude",
        "CLAUDE.md + .claude/skills (generated)",
        _state(status.claude_ready),
    )
    table.add_row(
        "Cursor",
        ".cursor/rules/agent-feed.mdc (generated)",
        _state(status.cursor_ready),
    )
    console.print(table)

    if status.errors or status.warnings:
        report = Table(title="Diagnostics")
        report.add_column("Type")
        report.add_column("Message")
        for error in status.errors:
            report.add_row("error", error)
        for warning in status.warnings:
            report.add_row("warning", warning)
        console.print(report)


def _state(ok: bool) -> str:
    return "[green]ready[/green]" if ok else "[red]missing/stale[/red]"
