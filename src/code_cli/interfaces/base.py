"""Interface protocol for I/O backends.

To add a new interface (e.g. Slack, Discord, Web):
  1. Subclass OutputInterface and/or InputInterface
  2. Register with OutputBus / wire into the input queue in _main()
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


class OutputInterface(ABC):
    """Where assistant output goes."""

    @abstractmethod
    async def send_response(self, text: str) -> None:
        """Assistant response (markdown)."""

    @abstractmethod
    async def send_tool_activity(self, icon: str, summary: str) -> None:
        """Tool execution info."""

    @abstractmethod
    async def send_tool_output(self, output: str, truncated: bool = False) -> None:
        """Tool stdout/stderr."""

    @abstractmethod
    async def send_error(self, error: str) -> None:
        """Error message."""

    @abstractmethod
    async def send_status(self, text: str) -> None:
        """Status / dim info."""

    @abstractmethod
    async def send_thinking(self, text: str) -> None:
        """Thinking / reasoning content."""


class InputInterface(ABC):
    """Where user input comes from."""

    @abstractmethod
    async def start(self, queue: asyncio.Queue[tuple[str, str]]) -> None:
        """Start pushing user messages into *queue* as (source, text) tuples."""

    @abstractmethod
    async def stop(self) -> None:
        """Cleanup."""

    async def display_input(self, source: str, text: str) -> None:
        """Display user input from another source.

        Called when input arrives from another interface so this interface
        can show what the user typed elsewhere.

        Args:
            source: Name of the source ('terminal', 'telegram', etc.)
            text: The input text that was received
        """
        pass
