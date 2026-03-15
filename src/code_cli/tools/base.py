"""Base class for tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class Tool(ABC):
    """Base class for all available tools.

    Subclasses must define:
    - name: unique tool identifier
    - description: what the tool does
    - input_schema: JSON Schema for the tool's input
    - execute(): the tool's implementation
    """

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict]
    read_only: ClassVar[bool] = False
    icon: ClassVar[str] = "🔧"

    @classmethod
    def get_tool_definition(cls) -> dict:
        """Return the tool definition for the Claude API."""
        return {
            "name": cls.name,
            "description": cls.description,
            "input_schema": cls.input_schema,
        }

    @classmethod
    @abstractmethod
    def execute(cls, input_data: dict) -> str:
        """Execute the tool with the given input. Returns result as string."""
        raise NotImplementedError
