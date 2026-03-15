"""File content search tool."""

import subprocess

from .base import Tool, ToolName


class Grep(Tool):
    name = ToolName.GREP
    read_only = True
    icon = "🔎"
    description = (
        "Search for a pattern in files. Returns matching lines with file paths and line numbers."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "The regex pattern to search for"},
            "path": {
                "type": "string",
                "description": "Directory or file to search in (default: current directory)",
                "default": ".",
            },
            "include": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g. '*.py', '*.js')",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Case insensitive search",
                "default": False,
            },
        },
        "required": ["pattern"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        pattern = input_data["pattern"]
        path = input_data.get("path", ".")
        include = input_data.get("include")
        case_insensitive = input_data.get("case_insensitive", False)

        cmd = ["grep", "-rn"]
        if case_insensitive:
            cmd.append("-i")
        if include:
            cmd.extend(["--include", include])
        cmd.extend([pattern, path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout
            if not output:
                return "No matches found."
            # Truncate large output
            lines = output.split("\n")
            if len(lines) > 50:
                return "\n".join(lines[:50]) + f"\n... ({len(lines) - 50} more matches)"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Search timed out"
        except Exception as e:
            return f"Error: {str(e)}"


def get_tool_definition():
    return Grep.get_tool_definition()


def execute(input_data: dict) -> str:
    return Grep.execute(input_data)
