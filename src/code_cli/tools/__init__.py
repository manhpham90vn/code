"""Tool registry and dispatcher."""

from . import bash as bash_module
from . import edit as edit_module
from . import glob as glob_module
from . import grep as grep_module
from . import read as read_module
from . import web_fetch as web_fetch_module
from . import web_search as web_search_module
from . import write as write_module


# All tool definitions following the Anthropic tool-use schema
def get_all_tools() -> list[dict]:
    return [
        read_module.get_tool_definition(),
        write_module.get_tool_definition(),
        edit_module.get_tool_definition(),
        bash_module.get_tool_definition(),
        grep_module.get_tool_definition(),
        glob_module.get_tool_definition(),
        web_search_module.get_tool_definition(),
        web_fetch_module.get_tool_definition(),
    ]


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool by name."""
    tool_map = {
        "read_file": read_module.execute,
        "write_file": write_module.execute,
        "edit_file": edit_module.execute,
        "run_bash": bash_module.execute,
        "grep": grep_module.execute,
        "glob_files": glob_module.execute,
        "web_search": web_search_module.execute,
        "web_fetch": web_fetch_module.execute,
    }

    if name not in tool_map:
        return f"Unknown tool: {name}"

    try:
        return tool_map[name](input_data)
    except Exception as e:
        return f"Error executing {name}: {str(e)}"
