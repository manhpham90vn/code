"""File reading tool."""

import os

from .base import Tool


class ReadFile(Tool):
    name = "read_file"
    description = (
        "Read a file from the local filesystem. "
        "Use this when you need to see the contents of a file."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "The path to the file to read"},
            "limit": {"type": "integer", "description": "Optional: Number of lines to read"},
            "offset": {
                "type": "integer",
                "description": "Optional: Line number to start reading from",
            },
        },
        "required": ["file_path"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        file_path = input_data["file_path"]
        limit = input_data.get("limit")
        offset = input_data.get("offset", 1)

        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if os.path.isdir(file_path):
            return f"Error: {file_path} is a directory"

        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        if offset > 1:
            lines = lines[offset - 1 :]

        if limit:
            lines = lines[:limit]

        return "".join(lines)


def get_tool_definition():
    return ReadFile.get_tool_definition()


def execute(input_data: dict) -> str:
    return ReadFile.execute(input_data)
