"""File writing tool."""

import os
from typing import ClassVar

from .base import Tool


class WriteFile(Tool):
    name: ClassVar[str] = "write_file"
    icon: ClassVar[str] = "✏️"
    description: ClassVar[str] = (
        "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        "required": ["file_path", "content"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        file_path = input_data.get("file_path", "")
        content = input_data.get("content", "")

        if not file_path or not isinstance(file_path, str):
            return "Error: file_path must be a non-empty string"

        if not isinstance(content, str):
            return "Error: content must be a string"

        # Create parent directories if needed
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except IsADirectoryError:
            return f"Error: {file_path} is a directory"

        return f"Successfully wrote to {file_path}"
