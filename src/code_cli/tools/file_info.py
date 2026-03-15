"""File info/metadata tool."""

import os
import stat
from datetime import datetime, timezone

from .base import Tool


class GetFileInfo(Tool):
    name = "get_file_info"
    read_only = True
    description = (
        "Get detailed metadata about a file or directory: "
        "size, timestamps, type, and permissions."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file or directory",
            },
        },
        "required": ["path"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        path = input_data["path"]

        if not os.path.exists(path):
            return f"Error: Path not found: {path}"

        try:
            st = os.stat(path)
        except PermissionError:
            return f"Error: Permission denied: {path}"

        file_type = "directory" if stat.S_ISDIR(st.st_mode) else "file"
        if stat.S_ISLNK(st.st_mode):
            file_type = "symlink"

        perms = stat.filemode(st.st_mode)
        size = st.st_size
        modified = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        created = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat()
        accessed = datetime.fromtimestamp(st.st_atime, tz=timezone.utc).isoformat()

        # Human-readable size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.1f} MB"

        return (
            f"Path: {path}\n"
            f"Type: {file_type}\n"
            f"Size: {size_str} ({size} bytes)\n"
            f"Permissions: {perms}\n"
            f"Modified: {modified}\n"
            f"Created: {created}\n"
            f"Accessed: {accessed}"
        )


def get_tool_definition():
    return GetFileInfo.get_tool_definition()


def execute(input_data: dict) -> str:
    return GetFileInfo.execute(input_data)
