"""Simple plugin system - direct module-level functions replacing Registry class."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .commands.base import Command

logger = logging.getLogger(__name__)

# Module-level storage
_commands: dict[str, Command] = {}
_tools: dict[str, Any] = {}
_mcp_servers: dict[str, dict] = {}


# === Commands ===


def register_command(cmd: Command) -> None:
    for name in cmd.names:
        _commands[name.lstrip("/")] = cmd


def get_command(name: str) -> Command | None:
    return _commands.get(name)


def get_all_commands() -> list[Command]:
    seen: set[int] = set()
    result = []
    for cmd in _commands.values():
        if id(cmd) not in seen:
            seen.add(id(cmd))
            result.append(cmd)
    return result


# === Tools ===


def register_tool(tool_class: type) -> None:
    name = getattr(tool_class, "name", None)
    if name:
        _tools[name] = tool_class


def get_tool(name: str) -> type | None:
    return _tools.get(name)


def get_all_tool_definitions() -> list[dict]:
    return [tool.get_tool_definition() for tool in _tools.values()]


def execute_tool(name: str, input_data: dict) -> str:
    tool_class = _tools.get(name)
    if not tool_class:
        return f"Unknown tool: {name}"
    try:
        return tool_class.execute(input_data)
    except Exception as e:
        return f"Error executing {name}: {str(e)}"


# === MCP ===


def register_mcp_server(name: str, config: dict) -> None:
    _mcp_servers[name] = config


def get_mcp_server(name: str) -> dict | None:
    return _mcp_servers.get(name)


def get_all_mcp_servers() -> dict[str, dict]:
    return dict(_mcp_servers)


# === Discovery ===


def discover_commands() -> None:
    from .commands.base import Command

    pkg_path = Path(__file__).parent / "commands"
    for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
        if module_name.startswith("_") or module_name == "base":
            continue
        try:
            mod = importlib.import_module(f".commands.{module_name}", package="code_cli")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Command) and attr is not Command:
                    register_command(attr())
                    logger.debug(f"Registered command: {attr().names}")
        except Exception as e:
            logger.warning(f"Failed to load command module {module_name}: {e}")


def discover_tools() -> None:
    from .tools.base import Tool

    pkg_path = Path(__file__).parent / "tools"
    for _, module_name, _ in pkgutil.iter_modules([str(pkg_path)]):
        if module_name.startswith("_") or module_name == "base":
            continue
        try:
            mod = importlib.import_module(f".tools.{module_name}", package="code_cli")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Tool) and attr is not Tool:
                    register_tool(attr)
                    logger.debug(f"Registered tool: {attr.name}")
        except Exception as e:
            logger.warning(f"Failed to load tool module {module_name}: {e}")


def discover_all() -> None:
    discover_commands()
    discover_tools()
