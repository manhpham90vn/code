"""List directory contents tool."""

import os

from .base import Tool, ToolName


class ListDirectory(Tool):
    name = ToolName.LIST_DIRECTORY
    read_only = True
    icon = "📂"
    description = "List the contents of a directory. Returns entries prefixed with [FILE] or [DIR]."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The directory path to list",
            },
        },
        "required": ["path"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        path = input_data["path"]

        if not os.path.exists(path):
            return f"Error: Path not found: {path}"

        if not os.path.isdir(path):
            return f"Error: Not a directory: {path}"

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return f"Error: Permission denied: {path}"

        if not entries:
            return "(empty directory)"

        lines = []
        for entry in entries:
            full_path = os.path.join(path, entry)
            prefix = "[DIR]" if os.path.isdir(full_path) else "[FILE]"
            lines.append(f"{prefix} {entry}")

        return "\n".join(lines)


def get_tool_definition():
    return ListDirectory.get_tool_definition()


def execute(input_data: dict) -> str:
    return ListDirectory.execute(input_data)
