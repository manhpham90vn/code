"""Help command."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from ..tools import get_all_tools
from .base import Command


class HelpCommand(Command):
    names = ["/help", "/h"]
    description = "Show available commands and tools"

    def execute(
        self,
        args: str,
        *,
        client,
        context,
        console: Console,
        stream_fn=None,
        log_usage_fn=None,
    ) -> bool:
        # Build tools list
        tools = get_all_tools()
        tool_names = "\n".join(f"- {t['name']} - {t.get('description', '')}" for t in tools)

        console.print(
            Panel.fit(
                "[bold]Commands:[/bold]\n"
                "/help   - Show help\n"
                "/clear  - Clear conversation history\n"
                "/commit - AI-generated commit message\n"
                "/quit   - Exit\n\n"
                f"[bold]Tools:[/bold]\n{tool_names}",
                border_style="green",
            )
        )
        return True
