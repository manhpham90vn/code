"""Directory tree tool."""

import os
from typing import ClassVar

from .base import Tool

DEFAULT_EXCLUDE: set[str] = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox"}


class DirectoryTree(Tool):
    name: ClassVar[str] = "directory_tree"
    read_only: ClassVar[bool] = True
    icon: ClassVar[str] = "🌲"
    description: ClassVar[str] = (
        "Get a recursive tree view of a directory structure. "
        "Useful for understanding project layout."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The root directory path",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth to recurse (default: 4)",
                "default": 4,
            },
            "exclude_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Directories to exclude (default: .git, __pycache__, node_modules)",
            },
        },
        "required": ["path"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        path = input_data.get("path", "")
        max_depth = input_data.get("max_depth", 4)
        exclude = set(input_data.get("exclude_patterns", [])) or DEFAULT_EXCLUDE

        if not path or not isinstance(path, str):
            return "Error: path must be a non-empty string"

        if not os.path.exists(path):
            return f"Error: Path not found: {path}"

        if not os.path.isdir(path):
            return f"Error: Not a directory: {path}"

        lines: list[str] = [os.path.basename(path) + "/"]
        cls._build_tree(path, "", lines, max_depth, 0, exclude)

        if len(lines) > 500:
            lines = lines[:500]
            lines.append("... (truncated, tree too large)")

        return "\n".join(lines)

    @classmethod
    def _build_tree(
        cls,
        path: str,
        prefix: str,
        lines: list[str],
        max_depth: int,
        depth: int,
        exclude: set[str],
    ) -> None:
        if depth >= max_depth:
            return

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            lines.append(f"{prefix}[permission denied]")
            return

        # Filter excluded directories
        filtered_entries = [e for e in entries if e not in exclude]

        for i, entry in enumerate(filtered_entries):
            is_last = i == len(filtered_entries) - 1
            connector = "└── " if is_last else "├── "
            full_path = os.path.join(path, entry)

            if os.path.isdir(full_path):
                lines.append(f"{prefix}{connector}{entry}/")
                extension = "    " if is_last else "│   "
                cls._build_tree(full_path, prefix + extension, lines, max_depth, depth + 1, exclude)
            else:
                lines.append(f"{prefix}{connector}{entry}")
