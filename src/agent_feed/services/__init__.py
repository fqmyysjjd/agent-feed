"""High-level orchestration services used by the CLI command layer.

Functions in this package are deliberately UI-aware (they may print Rich
progress bars or call ``prompt_confirm``) but framework-agnostic — they do
not import Typer and do not parse command-line arguments. The CLI layer
in ``agent_feed.cli`` re-exports these for backward compatibility.
"""

from agent_feed.services.clients import (
    find_init_conflicts,
    installed_clients,
    planned_backup_resolves_init_adapter_error,
    sync_clients,
)
from agent_feed.services.lifecycle import (
    downgrade_preflight_errors,
    init_backup_dir,
    init_project,
    preview_actions,
    preview_project,
    upgrade_project,
)

__all__ = [
    "downgrade_preflight_errors",
    "find_init_conflicts",
    "init_backup_dir",
    "init_project",
    "installed_clients",
    "planned_backup_resolves_init_adapter_error",
    "preview_actions",
    "preview_project",
    "sync_clients",
    "upgrade_project",
]
