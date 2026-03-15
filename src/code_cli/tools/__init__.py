"""Tool registry and dispatcher.

Tools are auto-discovered by plugin_system.discover_all() at startup.
"""

from ..plugin_system import execute_tool as _execute_tool
from ..plugin_system import get_all_tool_definitions


def get_all_tools() -> list[dict]:
    """Get all tool definitions for Claude API."""
    return get_all_tool_definitions()


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool by name."""
    return _execute_tool(name, input_data)
