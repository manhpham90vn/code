"""Command registry and dispatcher.

Commands are auto-discovered by registry.discover_all() at startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..registry import registry

if TYPE_CHECKING:
    from .base import Command


def get_command(name: str) -> Command | None:
    """Lookup a command by its slash name (without /)."""
    return registry.get_command(name)


def get_all_commands() -> list[Command]:
    """Return unique command instances."""
    return registry.get_all_commands()
