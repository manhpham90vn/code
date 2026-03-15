"""Base class for slash commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from code_cli.client import ClaudeClient
    from code_cli.context import Context


class ConsoleProtocol(Protocol):
    """Protocol for console operations."""

    def print(self, *args, **kwargs) -> None: ...
    def input(self, *args, **kwargs) -> str: ...


class StreamFnProtocol(Protocol):
    """Protocol for streaming function."""

    def __call__(self, client: ClaudeClient, context: Context, tools: list[dict]) -> object: ...


class LogUsageFnProtocol(Protocol):
    """Protocol for logging token usage."""

    def __call__(self, response: object) -> None: ...


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
        console: ConsoleProtocol,
        stream_fn: StreamFnProtocol | None = None,
        log_usage_fn: LogUsageFnProtocol | None = None,
    ) -> bool:
        """Run the command.

        Args:
            args: Command arguments (after the command name)
            client: The Claude API client
            context: Conversation context
            console: Console for output/input
            stream_fn: Function to stream LLM response
            log_usage_fn: Function to log token usage

        Returns:
            True to continue the main loop, False to break.
        """
        ...
