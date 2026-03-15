"""Central plugin registry with auto-discovery."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .commands.base import Command

logger = logging.getLogger(__name__)


class Registry:
    """Central registry for all plugin types (commands, tools, MCP)."""

    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._tools: dict[str, Any] = {}  # Tool classes
        self._mcp_servers: dict[str, dict] = {}

    # === Commands ===

    def register_command(self, cmd: Command) -> None:
        """Register a command by all its names."""
        for name in cmd.names:
            key = name.lstrip("/")
            self._commands[key] = cmd

    def get_command(self, name: str) -> Command | None:
        return self._commands.get(name)

    def get_all_commands(self) -> list[Command]:
        """Return unique command instances."""
        seen: set[int] = set()
        result = []
        for cmd in self._commands.values():
            if id(cmd) not in seen:
                seen.add(id(cmd))
                result.append(cmd)
        return result

    # === Tools ===

    def register_tool(self, tool_class: type) -> None:
        """Register a tool class."""
        name = getattr(tool_class, "name", None)
        if name:
            self._tools[name] = tool_class

    def get_tool(self, name: str) -> type | None:
        return self._tools.get(name)

    def get_all_tool_definitions(self) -> list[dict]:
        """Get tool definitions for Claude API."""
        return [tool.get_tool_definition() for tool in self._tools.values()]

    def execute_tool(self, name: str, input_data: dict) -> str:
        """Execute a tool by name."""
        tool_class = self._tools.get(name)
        if not tool_class:
            return f"Unknown tool: {name}"
        try:
            return tool_class.execute(input_data)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    # === MCP ===

    def register_mcp_server(self, name: str, config: dict) -> None:
        """Register an MCP server config."""
        self._mcp_servers[name] = config

    def get_mcp_server(self, name: str) -> dict | None:
        return self._mcp_servers.get(name)

    def get_all_mcp_servers(self) -> dict[str, dict]:
        return dict(self._mcp_servers)


# Global registry instance
registry = Registry()


def discover_commands() -> None:
    """Auto-discover commands by scanning the commands package."""
    from .commands.base import Command

    pkg_path = Path(__file__).parent / "commands"
    for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
        if module_name.startswith("_") or module_name == "base":
            continue
        try:
            mod = importlib.import_module(f".commands.{module_name}", package="code_cli")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Command)
                    and attr is not Command
                ):
                    cmd_instance = attr()
                    registry.register_command(cmd_instance)
                    logger.debug(f"Registered command: {cmd_instance.names}")
        except Exception as e:
            logger.warning(f"Failed to load command module {module_name}: {e}")


def discover_tools() -> None:
    """Auto-discover tools by scanning the tools package."""
    from .tools.base import Tool

    pkg_path = Path(__file__).parent / "tools"
    for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
        if module_name.startswith("_") or module_name == "base":
            continue
        try:
            mod = importlib.import_module(f".tools.{module_name}", package="code_cli")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Tool)
                    and attr is not Tool
                ):
                    registry.register_tool(attr)
                    logger.debug(f"Registered tool: {attr.name}")
        except Exception as e:
            logger.warning(f"Failed to load tool module {module_name}: {e}")


def discover_all() -> None:
    """Discover all plugins."""
    discover_commands()
    discover_tools()
