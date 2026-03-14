"""File writing tool."""

import os

from .base import Tool


class WriteFile(Tool):
    name = "write_file"
    description = (
        "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "The path to the file to write"},
            "content": {"type": "string", "description": "The content to write to the file"},
        },
        "required": ["file_path", "content"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        file_path = input_data["file_path"]
        content = input_data["content"]

        # Create parent directories if needed
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote to {file_path}"


def get_tool_definition():
    return WriteFile.get_tool_definition()


def execute(input_data: dict) -> str:
    return WriteFile.execute(input_data)
