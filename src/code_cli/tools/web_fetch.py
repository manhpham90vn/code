"""URL content fetching tool."""

import urllib.request

from .base import Tool, ToolName


class WebFetch(Tool):
    name = ToolName.WEB_FETCH
    read_only = True
    icon = "🌐"
    description = "Fetch content from a URL. Returns the page content as text."
    input_schema = {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "The URL to fetch"}},
        "required": ["url"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        url = input_data["url"]

        # Validate URL
        if not url.startswith(("http://", "https://")):
            return "Error: URL must start with http:// or https://"

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; AI-CLI/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8", errors="ignore")

            # Truncate large responses
            if len(content) > 50000:
                return content[:50000] + "\n... (truncated)"

            return content
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"


def get_tool_definition():
    return WebFetch.get_tool_definition()


def execute(input_data: dict) -> str:
    return WebFetch.execute(input_data)
