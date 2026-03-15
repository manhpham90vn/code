"""File content search tool."""

import re
import subprocess
from typing import ClassVar

from .base import Tool


class Grep(Tool):
    name: ClassVar[str] = "grep"
    read_only: ClassVar[bool] = True
    icon: ClassVar[str] = "🔎"
    description: ClassVar[str] = (
        "Search for a pattern in files. Returns matching lines with file paths and line numbers."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The regex pattern to search for",
            },
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
        pattern = input_data.get("pattern", "")
        path = input_data.get("path", ".")
        include = input_data.get("include")
        case_insensitive = input_data.get("case_insensitive", False)

        # Validate pattern
        if not pattern or not isinstance(pattern, str):
            return "Error: pattern must be a non-empty string"

        # Validate regex
        try:
            re.compile(pattern)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        # Prevent directory traversal
        path_val = path if isinstance(path, str) and ".." not in path else "."

        cmd = ["grep", "-rn"]
        if case_insensitive:
            cmd.append("-i")
        if include:
            cmd.extend(["--include", include])
        cmd.extend([pattern, path_val])

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
        except FileNotFoundError:
            return "Error: grep command not found"
        except Exception as e:
            return f"Error: {str(e)}"
