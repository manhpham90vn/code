"""Command registry and dispatcher.

Commands are auto-discovered by plugin_system.discover_all() at startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..plugin_system import get_all_commands as _get_all_commands
from ..plugin_system import get_command as _get_command

if TYPE_CHECKING:
    from .base import Command


def get_command(name: str) -> Command | None:
    """Lookup a command by its slash name (without /)."""
    return _get_command(name)


def get_all_commands() -> list[Command]:
    """Return unique command instances."""
    return _get_all_commands()
