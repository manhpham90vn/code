"""Directory creation tool."""

import os

from .base import Tool


class CreateDirectory(Tool):
    name = "create_directory"
    description = "Create a new directory. Creates parent directories if they don't exist."
    input_schema = {
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
        path = input_data["path"]

        if os.path.exists(path):
            if os.path.isdir(path):
                return f"Directory already exists: {path}"
            return f"Error: Path exists and is not a directory: {path}"

        try:
            os.makedirs(path, exist_ok=True)
            return f"Created directory: {path}"
        except Exception as e:
            return f"Error: {str(e)}"


def get_tool_definition():
    return CreateDirectory.get_tool_definition()


def execute(input_data: dict) -> str:
    return CreateDirectory.execute(input_data)
