"""Terminal (stdout) interface."""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape

from .base import InputInterface, OutputInterface


class TerminalOutput(OutputInterface):
    """Rich console output."""

    def __init__(self, console: Console) -> None:
        self._console = console

    async def send_response(self, text: str) -> None:
        self._console.print(Markdown(text))

    async def send_tool_activity(self, icon: str, summary: str) -> None:
        self._console.print(f"[dim]{icon} {summary}[/dim]")

    async def send_tool_output(self, output: str, truncated: bool = False) -> None:
        max_lines = 30
        lines = output.split("\n")
        if len(lines) > max_lines:
            shown = "\n".join(lines[:max_lines])
            self._console.print(
                f"[dim]{escape(shown)}\n... ({len(lines) - max_lines} more lines)[/dim]"
            )
        else:
            self._console.print(f"[dim]{escape(output)}[/dim]")

    async def send_error(self, error: str) -> None:
        self._console.print(f"[error]{escape(error)}[/error]")

    async def send_status(self, text: str) -> None:
        self._console.print(f"[dim]{text}[/dim]")

    async def send_thinking(self, text: str) -> None:
        # Terminal already streams thinking via print() in _stream_response_sync
        pass


class TerminalInput(InputInterface):
    """Readline / prompt_toolkit input."""

    def __init__(self, prompt_session, console: Console | None = None) -> None:
        self._session = prompt_session
        self._console = console
        self._running = False

    async def start(self, queue: asyncio.Queue[tuple[str, str]]) -> None:
        self._running = True
        while self._running:
            try:
                user_input = await self._session.prompt_async("❯ ")
                if user_input:
                    await queue.put(("terminal", user_input))
            except asyncio.CancelledError:
                break
            except EOFError:
                break
            except Exception:
                # Continue on prompt errors
                await asyncio.sleep(0.1)

    async def stop(self) -> None:
        self._running = False

    async def display_input(self, source: str, text: str) -> None:
        if self._console:
            self._console.print(f"[dim][{source}] {escape(text)}[/dim]")
