"""File move/rename tool."""

import os
import shutil

from .base import Tool


class MoveFile(Tool):
    name = "move_file"
    icon = "📦"
    description = "Move or rename a file or directory."
    input_schema = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "The source path",
            },
            "destination": {
                "type": "string",
                "description": "The destination path",
            },
        },
        "required": ["source", "destination"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        source = input_data["source"]
        destination = input_data["destination"]

        if not os.path.exists(source):
            return f"Error: Source not found: {source}"

        if os.path.exists(destination):
            return f"Error: Destination already exists: {destination}"

        # Create parent directories if needed
        dest_dir = os.path.dirname(destination)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        try:
            shutil.move(source, destination)
            return f"Moved {source} -> {destination}"
        except Exception as e:
            return f"Error: {str(e)}"


def get_tool_definition():
    return MoveFile.get_tool_definition()


def execute(input_data: dict) -> str:
    return MoveFile.execute(input_data)
