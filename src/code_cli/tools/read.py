"""File reading tool."""

import os
from typing import ClassVar

from .base import Tool


class ReadFile(Tool):
    name: ClassVar[str] = "read_file"
    read_only: ClassVar[bool] = True
    icon: ClassVar[str] = "📄"
    description: ClassVar[str] = (
        "Read a file from the local filesystem. "
        "Use this when you need to see the contents of a file."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to read",
            },
            "limit": {
                "type": "integer",
                "description": "Optional: Number of lines to read",
            },
            "offset": {
                "type": "integer",
                "description": "Optional: Line number to start reading from",
            },
        },
        "required": ["file_path"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        file_path = input_data.get("file_path", "")
        limit = input_data.get("limit")
        offset = input_data.get("offset", 1)

        if not file_path or not isinstance(file_path, str):
            return "Error: file_path must be a non-empty string"

        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if os.path.isdir(file_path):
            return f"Error: {file_path} is a directory"

        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {file_path}"

        if offset and offset > 1:
            lines = lines[offset - 1 :]

        if limit and limit > 0:
            lines = lines[:limit]

        return "".join(lines)
