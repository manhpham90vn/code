"""List directory contents tool."""

import os
from typing import ClassVar

from .base import Tool


class ListDirectory(Tool):
    name: ClassVar[str] = "list_directory"
    read_only: ClassVar[bool] = True
    icon: ClassVar[str] = "📂"
    description: ClassVar[str] = (
        "List the contents of a directory. Returns entries prefixed with [FILE] or [DIR]."
    )
    input_schema: ClassVar[dict] = {
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
        path = input_data.get("path", "")

        if not path or not isinstance(path, str):
            return "Error: path must be a non-empty string"

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

        lines: list[str] = []
        for entry in entries:
            full_path = os.path.join(path, entry)
            prefix = "[DIR]" if os.path.isdir(full_path) else "[FILE]"
            lines.append(f"{prefix} {entry}")

        return "\n".join(lines)
