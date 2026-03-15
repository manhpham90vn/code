"""File editing tool."""

import os

from .base import Tool, ToolName


class EditFile(Tool):
    name = ToolName.EDIT_FILE
    icon = "✏️"
    description = (
        "Make exact string replacements in a file. Use this to modify specific parts of a file."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "The path to the file to edit"},
            "old_string": {"type": "string", "description": "The exact string to find and replace"},
            "new_string": {"type": "string", "description": "The string to replace it with"},
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
        file_path = input_data["file_path"]
        old_string = input_data["old_string"]
        new_string = input_data["new_string"]
        replace_all = input_data.get("replace_all", False)

        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Verify old_string exists in the file
        if old_string not in content:
            return f"Error: String not found in file:\n{old_string[:100]}..."

        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        action = "Replaced all" if replace_all else "Replaced"
        return f"{action} in {file_path}"


def get_tool_definition():
    return EditFile.get_tool_definition()


def execute(input_data: dict) -> str:
    return EditFile.execute(input_data)
