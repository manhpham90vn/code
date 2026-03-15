"""File glob/pattern matching tool."""

import glob as glob_module
import os

from .base import Tool, ToolName


class GlobFiles(Tool):
    name = ToolName.GLOB_FILES
    read_only = True
    icon = "🔍"
    description = "Find files matching a glob pattern. Use this to discover files in the project."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')",
            },
            "path": {
                "type": "string",
                "description": "Base directory to search from (default: current directory)",
                "default": ".",
            },
        },
        "required": ["pattern"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        pattern = input_data["pattern"]
        path = input_data.get("path", ".")

        full_pattern = os.path.join(path, pattern)
        matches = sorted(glob_module.glob(full_pattern, recursive=True))

        if not matches:
            return "No files found."

        if len(matches) > 100:
            return "\n".join(matches[:100]) + f"\n... ({len(matches) - 100} more files)"

        return "\n".join(matches)


def get_tool_definition():
    return GlobFiles.get_tool_definition()


def execute(input_data: dict) -> str:
    return GlobFiles.execute(input_data)
