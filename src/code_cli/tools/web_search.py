"""Web search tool."""

from .base import Tool


class WebSearch(Tool):
    name = "web_search"
    read_only = True
    icon = "🔍"
    description = "Search the web for information. Returns search results with titles and URLs."
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query"}},
        "required": ["query"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        # Placeholder — requires a search API integration (Google, Bing, SerpAPI, etc.)
        query = input_data["query"]
        return (
            f"Web search for '{query}' is not yet implemented. "
            "To enable, integrate a search API "
            "(e.g., Google Custom Search, Bing Search API, or SerpAPI)."
        )


def get_tool_definition():
    return WebSearch.get_tool_definition()


def execute(input_data: dict) -> str:
    return WebSearch.execute(input_data)
