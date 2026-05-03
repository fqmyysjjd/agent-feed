"""Rich console output for Agent Feed."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_feed import __version__
from agent_feed.config import ConfigCheckReport
from agent_feed.models import CheckReport, ProjectStatus, WriteAction


console = Console()


def print_welcome() -> None:
    logo = Text()
    logo.append("AGENT\n", style="bold cyan")
    logo.append("FEED", style="bold green")

    body = Table.grid(padding=(0, 2))
    body.add_column(no_wrap=True)
    body.add_column(ratio=1)
    body.add_row(
        logo,
        "[bold white]Agent Feed[/bold white]\n"
        "[dim]A source-controlled workflow pipeline for AI coding agents.[/dim]\n\n"
        "[bold]Start[/bold]    agent-feed init\n"
        "[bold]Verify[/bold]   agent-feed check\n"
        "[bold]Inspect[/bold]  agent-feed status\n"
        "[bold]Preview[/bold]  agent-feed preview",
    )
    console.print(
        Panel.fit(
            body,
            title=f"agent-feed {__version__}",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def print_error_panel(title: str, errors: list[str]) -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(width=2, no_wrap=True)
    table.add_column(ratio=1)
    for error in errors:
        table.add_row("[bold red]![/bold red]", error)
    console.print(Panel(table, title=title, border_style="red", expand=False))


def render_diff(diff: str) -> Text:
    rendered = Text()
    lines = diff.splitlines(keepends=True)
    if not lines and diff:
        lines = [diff]
    for line in lines:
        rendered.append(line, style=diff_line_style(line))
    return rendered


def diff_line_style(line: str) -> str | None:
    if line.startswith("@@"):
        return "bold cyan"
    if line.startswith("--- "):
        return "bold red"
    if line.startswith("+++ "):
        return "bold green"
    if line.startswith("-"):
        return "red"
    if line.startswith("+"):
        return "green"
    if line.startswith("diff ") or line.startswith("index "):
        return "bold"
    if line.startswith("\\"):
        return "dim"
    return None


def print_write_plan(actions: list[WriteAction], *, show_diffs: bool = False) -> None:
    print_write_plan_with_title(actions, title=write_plan_title(actions), show_diffs=show_diffs)


def print_write_plan_with_title(
    actions: list[WriteAction],
    *,
    title: str,
    show_diffs: bool = False,
) -> None:
    table = Table(
        title=title,
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold",
    )
    table.add_column("", width=2, no_wrap=True)
    table.add_column("Action", style="bold")
    table.add_column("Path", overflow="fold")
    table.add_column("Detail", style="dim", overflow="fold")
    for action in actions:
        table.add_row(
            action_icon(action),
            styled_action(action),
            display_path(action.path),
            action.detail,
        )
    console.print(table)
    if show_diffs:
        print_diff_details(actions)


def has_diff_details(actions: list[WriteAction]) -> bool:
    return any(action.diff for action in actions)


def print_diff_details(actions: list[WriteAction]) -> None:
    for action in actions:
        if action.diff:
            console.print(
                Panel(
                    render_diff(action.diff),
                    title=f"Diff: {display_path(action.path)}",
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

    if report.ok and not report.warnings:
        console.print(
            Panel.fit(
                f"[bold green]Checks passed[/bold green]\n"
                f"[dim]Target[/dim] {report.target}\n"
                f"[dim]Scope[/dim]  {', '.join(check.value for check in report.checks)}",
                title="Agent Feed",
                border_style="green",
            )
        )
    elif report.ok:
        table = Table(title="Checks Passed With Warnings", box=box.SIMPLE_HEAVY)
        table.add_column("", width=2)
        table.add_column("Type")
        table.add_column("Message", overflow="fold")
        for warning in report.warnings:
            table.add_row("?", "[yellow]warning[/yellow]", warning)
        console.print(table)
        print_next_step("Review the warnings above before the final handoff.")
    else:
        table = Table(title="Checks blocked", box=box.SIMPLE_HEAVY, header_style="bold red")
        table.add_column("", width=2)
        table.add_column("Type")
        table.add_column("Message", overflow="fold")
        for error in report.errors:
            table.add_row("!", "[red]error[/red]", error)
        for warning in report.warnings:
            table.add_row("?", "[yellow]warning[/yellow]", warning)
        console.print(table)
        print_next_step("Fix the diagnostics above, then rerun `agent-feed check`.")


def print_config_check_report(report: ConfigCheckReport, *, as_json: bool) -> None:
    if as_json:
        payload = {
            "target": str(report.target),
            "project_config": str(report.project_config),
            "user_config": str(report.user_config) if report.user_config else None,
            "ok": report.ok,
            "errors": list(report.errors),
            "warnings": list(report.warnings),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if report.ok and not report.warnings:
        console.print(
            Panel.fit(
                "[bold green]Config checks passed[/bold green]\n"
                f"[dim]Project[/dim] {report.project_config}\n"
                f"[dim]User[/dim]    {report.user_config or 'not configured'}",
                title="Agent Feed",
                border_style="green",
            )
        )
        return

    table = Table(title="Config Diagnostics", box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("", width=2)
    table.add_column("Type")
    table.add_column("Message", overflow="fold")
    for error in report.errors:
        table.add_row("!", "[red]error[/red]", error)
    for warning in report.warnings:
        table.add_row("?", "[yellow]warning[/yellow]", warning)
    console.print(table)
    if report.errors:
        print_next_step("Fix the config diagnostics above, then rerun `agent-feed config check`.")
    else:
        print_next_step("Review stale entries or rerun `agent-feed config set` to clean them.")


def print_status(status: ProjectStatus, *, as_json: bool) -> None:
    if as_json:
        payload = asdict(status)
        payload["target"] = str(status.target)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    table = Table(
        title=f"Agent Feed Status: {status.target}",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
    )
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
        report = Table(title="Diagnostics", box=box.SIMPLE_HEAVY)
        report.add_column("", width=2)
        report.add_column("Type")
        report.add_column("Message", overflow="fold")
        for error in status.errors:
            report.add_row("!", "[red]error[/red]", error)
        for warning in status.warnings:
            report.add_row("?", "[yellow]warning[/yellow]", warning)
        console.print(report)

    print_next_step(status_next_step(status))


def _state(ok: bool) -> str:
    return "[green]ready[/green]" if ok else "[red]blocked[/red]"


def write_plan_title(actions: list[WriteAction]) -> str:
    if not actions:
        return "No Changes"
    if any(action.severity == "warning" for action in actions):
        return "Review Required"
    if any(action.severity == "preview" for action in actions):
        return "Preview"
    return "Changes"


def action_icon(action: WriteAction) -> str:
    return {
        "warning": "!",
        "preview": "~",
        "neutral": "-",
        "success": "+",
    }[action.severity]


def styled_action(action: WriteAction) -> Text:
    styles = {
        "warning": "bold yellow",
        "preview": "cyan",
        "neutral": "dim",
        "success": "green",
    }
    return Text(action.action, style=styles[action.severity])


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def print_next_step(message: str) -> None:
    console.print(f"[bold cyan]Next:[/bold cyan] [bold white]{message}[/bold white]")


def print_action_result(
    *,
    title: str,
    message: str,
    kind: str = "info",
    detail: str | None = None,
) -> None:
    styles = {
        "success": ("green", "bold green"),
        "warning": ("yellow", "bold yellow"),
        "error": ("red", "bold red"),
        "info": ("cyan", "bold cyan"),
    }
    border_style, heading_style = styles.get(kind, styles["info"])
    body = f"[{heading_style}]{message}[/{heading_style}]"
    if detail:
        body += f"\n[dim]{detail}[/dim]"
    console.print(Panel.fit(body, title=title, border_style=border_style))


def print_recommended_command(message: str, command: str, *, path: str | None = None) -> None:
    text = Text()
    text.append(message, style="bold cyan")
    if path:
        text.append(" Edit ")
        text.append(path, style="blue italic")
        text.append(", then run ")
    else:
        text.append(" Run ")
    text.append(command, style="bold green")
    text.append(".")
    console.print(text)


def print_markdown_panel(title: str, body: str, *, border_style: str = "blue") -> None:
    console.print(Panel(Markdown(body), title=title, border_style=border_style, expand=False))


def print_stale_project_cleanup(config_file: Path, project_roots: tuple[Path, ...]) -> None:
    metadata = Table(
        box=None,
        show_header=False,
        expand=True,
        padding=(0, 1),
    )
    metadata.add_column("Field", style="dim", no_wrap=True)
    metadata.add_column("Value", overflow="fold", ratio=1)
    metadata.add_row("Config", str(config_file))

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Missing project root", overflow="fold", ratio=1)
    for index, project_root in enumerate(project_roots, start=1):
        table.add_row(str(index), str(project_root))

    body = Table.grid(expand=True, padding=(0, 1))
    body.add_column(ratio=1)
    body.add_row(
        "Agent Feed found project records in the user-level config whose directories no "
        "longer exist. Removing them only cleans stale trust metadata; it does not touch "
        "project files."
    )
    body.add_row(metadata)
    body.add_row(table)
    console.print(
        Panel(
            body,
            title="Stale Project Entries",
            border_style="yellow",
            expand=False,
        )
    )


def status_next_step(status: ProjectStatus) -> str:
    if not status.canonical_installed:
        return "Run `agent-feed init` in this project."
    if status.errors:
        return "Run `agent-feed check --checks all` for the full failure list."
    if status.warnings:
        return "Review the warnings above, then run `agent-feed preview` before updating."
    return "Run `agent-feed preview` to inspect managed drift before updating."


def print_diff_hint(
    *,
    command: str,
    interactive: bool,
) -> None:
    if interactive:
        message = (
            f"[bold cyan]Diff details:[/bold cyan] press [bold green]v[/bold green] "
            f"to show all diffs, or press any other key to exit. "
            f"Script mode: [bold green]{command}[/bold green]."
        )
    else:
        message = (
            f"[bold cyan]Diff details:[/bold cyan] rerun [bold green]{command}[/bold green]."
        )
    console.print(message)
