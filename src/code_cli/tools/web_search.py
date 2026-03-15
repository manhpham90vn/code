"""Web search tool."""

from typing import ClassVar

from .base import Tool


class WebSearch(Tool):
    name: ClassVar[str] = "web_search"
    read_only: ClassVar[bool] = True
    icon: ClassVar[str] = "🔍"
    description: ClassVar[str] = (
        "Search the web for information. Returns search results with titles and URLs."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
        },
        "required": ["query"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        query = input_data.get("query", "")
        if not query or not isinstance(query, str):
            return "Error: query must be a non-empty string"

        return (
            f"Web search for '{query}' is not yet implemented. "
            "To enable, integrate a search API "
            "(e.g., Google Custom Search, Bing Search API, or SerpAPI)."
        )
