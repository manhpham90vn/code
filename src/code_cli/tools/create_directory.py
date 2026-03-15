"""Directory creation tool."""

import os
from typing import ClassVar

from .base import Tool


class CreateDirectory(Tool):
    name: ClassVar[str] = "create_directory"
    icon: ClassVar[str] = "📁"
    description: ClassVar[str] = (
        "Create a new directory. Creates parent directories if they don't exist."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The directory path to create",
            },
        },
        "required": ["path"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        path = input_data.get("path", "")

        if not path or not isinstance(path, str):
            return "Error: path must be a non-empty string"

        # Prevent directory traversal attack
        if ".." in path:
            return "Error: '..' not allowed in path"

        if os.path.exists(path):
            if os.path.isdir(path):
                return f"Directory already exists: {path}"
            return f"Error: Path exists and is not a directory: {path}"

        try:
            os.makedirs(path, exist_ok=True)
            return f"Created directory: {path}"
        except PermissionError:
            return "Error: Permission denied"
        except Exception as e:
            return f"Error: {str(e)}"
