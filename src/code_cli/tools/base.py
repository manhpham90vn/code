"""Base class for tools."""

from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all available tools."""

    name: str
    description: str
    input_schema: dict
    read_only: bool = False  # Set to True for read-only tools that don't require confirmation
    icon: str = "🔧"  # Default icon for tools

    @classmethod
    def get_tool_definition(cls) -> dict:
        return {
            "name": cls.name,
            "description": cls.description,
            "input_schema": cls.input_schema,
        }

    @classmethod
    @abstractmethod
    def execute(cls, input_data: dict) -> str:
        raise NotImplementedError
