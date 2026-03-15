"""Command registry and dispatcher."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .commit import CommitCommand
from .help import HelpCommand

if TYPE_CHECKING:
    from .base import Command

# Register all commands here
_COMMANDS: dict[str, Command] = {}


def _register(cmd: Command):
    for name in cmd.names:
        # Store without leading slash for clean lookup
        key = name.lstrip("/")
        _COMMANDS[key] = cmd


def _init():
    _register(HelpCommand())
    _register(CommitCommand())


_init()


def get_command(name: str) -> Command | None:
    """Lookup a command by its slash name (without /)."""
    return _COMMANDS.get(name)


def get_all_commands() -> list[Command]:
    """Return unique command instances."""
    seen: set[int] = set()
    result = []
    for cmd in _COMMANDS.values():
        if id(cmd) not in seen:
            seen.add(id(cmd))
            result.append(cmd)
    return result
