"""Tool registry and dispatcher.

Tools are auto-discovered by registry.discover_all() at startup.
"""

from ..registry import registry


def get_all_tools() -> list[dict]:
    """Get all tool definitions for Claude API."""
    return registry.get_all_tool_definitions()


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool by name."""
    return registry.execute_tool(name, input_data)
