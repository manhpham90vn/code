"""Base class for tools."""

from enum import Enum


class ToolName(str, Enum):
    """Enum of all built-in tool names."""

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    RUN_BASH = "run_bash"
    MOVE_FILE = "move_file"
    CREATE_DIRECTORY = "create_directory"
    GLOB_FILES = "glob_files"
    GREP = "grep"
    GET_FILE_INFO = "get_file_info"
    DIRECTORY_TREE = "directory_tree"
    LIST_DIRECTORY = "list_directory"
    WEB_FETCH = "web_fetch"
    WEB_SEARCH = "web_search"


class Tool:
    """Base class for all available tools."""

    name: str
    description: str
    input_schema: dict
    read_only: bool = False  # Set to True for read-only tools that don't require confirmation
    icon: str = "🔧"  # Default icon for tools

    @classmethod
    def get_tool_definition(cls) -> dict:
        return {
            "name": cls.name.value,  # Convert ToolName enum to plain string
            "description": cls.description,
            "input_schema": cls.input_schema,
        }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        raise NotImplementedError
