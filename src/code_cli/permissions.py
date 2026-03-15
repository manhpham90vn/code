"""Tool permission manager — Claude CLI style confirmation prompts."""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape


# Icons for tool display
TOOL_ICONS = {
    "run_bash": "$",
    "write_file": "✏️ ",
    "edit_file": "✏️ ",
    "move_file": "📦",
    "create_directory": "📁",
}


def _format_tool_summary(tool_name: str, tool_input: dict) -> str:
    """Format a one-line summary of what the tool will do."""
    if tool_name == "run_bash":
        return tool_input.get("command", "")
    if tool_name == "write_file":
        return tool_input.get("file_path", "")
    if tool_name == "edit_file":
        return tool_input.get("file_path", "")
    if tool_name == "move_file":
        src = tool_input.get("source", "")
        dst = tool_input.get("destination", "")
        return f"{src} -> {dst}"
    if tool_name == "create_directory":
        return tool_input.get("path", "")
    # MCP or unknown tools
    return str(tool_input) if tool_input else ""


class PermissionManager:
    """Session-level tool permission manager."""

    def __init__(self):
        self._always_allowed: set[str] = set()

    def check(
        self,
        tool_name: str,
        tool_input: dict,
        is_read_only: bool,
        console: Console,
    ) -> bool:
        """Check if a tool is allowed to run. Prompts user if needed.

        Returns True if allowed, False if denied.
        """
        if is_read_only:
            return True

        if tool_name in self._always_allowed:
            return True

        # Display tool info
        icon = TOOL_ICONS.get(tool_name, "🔧")
        summary = _format_tool_summary(tool_name, tool_input)
        console.print(f"  [bold yellow]{icon} {tool_name}[/bold yellow]")
        if summary:
            console.print(f"    [dim]{escape(summary)}[/dim]")

        # Prompt
        while True:
            try:
                answer = input("  Allow? (y)es / (n)o / (a)lways: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                console.print()
                return False

            if answer in ("y", "yes", ""):
                return True
            if answer in ("a", "always"):
                self._always_allowed.add(tool_name)
                return True
            if answer in ("n", "no"):
                return False
            # Invalid input — ask again
