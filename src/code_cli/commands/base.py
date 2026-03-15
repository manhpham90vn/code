"""Base class for slash commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from code_cli.client import ClaudeClient
    from code_cli.context import Context


class Command(ABC):
    """Base class all slash commands must implement."""

    # Command names (first is primary, rest are aliases)
    names: list[str]
    # Short description shown in /help
    description: str

    @abstractmethod
    def execute(
        self,
        args: str,
        *,
        client: ClaudeClient,
        context: Context,
        console: object,
        stream_fn: object | None = None,
        log_usage_fn: object | None = None,
    ) -> bool:
        """Run the command. Return True to continue the loop, False to break."""
        ...
