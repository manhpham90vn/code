"""Tool permission manager — Claude CLI style confirmation prompts."""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape

from .config import load_config, save_config
from .tools.base import ToolName


def _format_tool_summary(tool_name: str, tool_input: dict) -> str:
    """Format a one-line summary of what the tool will do."""
    match tool_name:
        case ToolName.RUN_BASH:
            return tool_input.get("command", "")
        case ToolName.WRITE_FILE | ToolName.EDIT_FILE:
            return tool_input.get("file_path", "")
        case ToolName.MOVE_FILE:
            src = tool_input.get("source", "")
            dst = tool_input.get("destination", "")
            return f"{src} -> {dst}"
        case ToolName.CREATE_DIRECTORY:
            return tool_input.get("path", "")
        case _:
            return str(tool_input) if tool_input else ""


class PermissionManager:
    """Session-level tool permission manager."""

    def __init__(self):
        config = load_config()
        self._always_allowed: set[str] = set(config.get("allowed_tools", []))

    def check(
        self,
        tool_name: str,
        tool_input: dict,
        is_read_only: bool,
        console: Console,
        icon: str = "🔧",
    ) -> bool:
        """Check if a tool is allowed to run. Prompts user if needed.

        Returns True if allowed, False if denied.
        """
        if is_read_only:
            return True

        if tool_name in self._always_allowed:
            return True

        # Display tool info
        summary = _format_tool_summary(tool_name, tool_input)
        console.print(f"  [bold yellow]{icon} {tool_name}[/bold yellow]")
        if summary:
            console.print(f"    [dim]{escape(summary)}[/dim]")

        # Prompt
        while True:
            try:
                answer = console.input("  Allow? (y)es / (n)o / (a)lways: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                console.print()
                return False

            if answer in ("y", "yes", ""):
                return True
            if answer in ("a", "always"):
                self._always_allowed.add(tool_name)
                # Save to config
                config = load_config()
                config.setdefault("allowed_tools", [])
                if tool_name not in config["allowed_tools"]:
                    config["allowed_tools"].append(tool_name)
                    save_config({"allowed_tools": config["allowed_tools"]})
                    console.print("  [dim]Saved to .code_cli/config.json[/dim]")
                return True
            if answer in ("n", "no"):
                return False
            # Invalid input — ask again
