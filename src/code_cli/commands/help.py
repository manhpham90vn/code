"""Help command."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from ..registry import registry
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
        # Build commands list
        commands = registry.get_all_commands()
        cmd_lines = "\n".join(
            f"  {', '.join(c.names):16s} {c.description}" for c in commands
        )

        # Built-in commands
        builtin_cmds = "  /clear            Clear conversation history\n  /quit, /exit       Exit"

        # Build tools list
        tools = get_all_tools()
        tool_lines = "\n".join(f"  {t['name']:16s} {t.get('description', '')[:60]}" for t in tools)

        # Build MCP info
        mcp_servers = registry.get_all_mcp_servers()
        mcp_lines = ""
        if mcp_servers:
            mcp_lines = "\n\n[bold]MCP Servers:[/bold]\n"
            mcp_lines += "\n".join(f"  {name}" for name in mcp_servers)

        console.print(
            Panel.fit(
                f"[bold]Commands:[/bold]\n{cmd_lines}\n{builtin_cmds}\n\n"
                f"[bold]Tools:[/bold]\n{tool_lines}{mcp_lines}",
                border_style="green",
            )
        )
        return True
