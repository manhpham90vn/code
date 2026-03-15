"""File editing tool."""

import os
from typing import ClassVar

from .base import Tool


class EditFile(Tool):
    name: ClassVar[str] = "edit_file"
    icon: ClassVar[str] = "✏️"
    description: ClassVar[str] = (
        "Make exact string replacements in a file. Use this to modify specific parts of a file."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to find and replace",
            },
            "new_string": {
                "type": "string",
                "description": "The string to replace it with",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (default: false, only first occurrence)",
                "default": False,
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        file_path = input_data.get("file_path", "")
        old_string = input_data.get("old_string", "")
        new_string = input_data.get("new_string", "")
        replace_all = input_data.get("replace_all", False)

        if not file_path or not isinstance(file_path, str):
            return "Error: file_path must be a non-empty string"

        if not old_string:
            return "Error: old_string must be a non-empty string"

        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {file_path}"

        # Verify old_string exists in the file
        if old_string not in content:
            # Show a helpful snippet for debugging
            preview = old_string[:100] + "..." if len(old_string) > 100 else old_string
            return f"Error: String not found in file:\n{preview}"

        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except PermissionError:
            return f"Error: Permission denied writing to: {file_path}"

        action = "Replaced all" if replace_all else "Replaced"
        return f"{action} in {file_path}"
