"""URL content fetching tool."""

import urllib.request
from typing import ClassVar

from .base import Tool


class WebFetch(Tool):
    name: ClassVar[str] = "web_fetch"
    read_only: ClassVar[bool] = True
    icon: ClassVar[str] = "🌐"
    description: ClassVar[str] = "Fetch content from a URL. Returns the page content as text."
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch"},
        },
        "required": ["url"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        url = input_data.get("url", "")

        if not url or not isinstance(url, str):
            return "Error: url must be a non-empty string"

        # Validate URL scheme
        if not url.startswith(("http://", "https://")):
            return "Error: URL must start with http:// or https://"

        # Basic URL validation
        if len(url) > 2048:
            return "Error: URL too long (max 2048 characters)"

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AI-CLI/1.0)"},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                content = response.read().decode("utf-8", errors="ignore")

            # Truncate large responses
            if len(content) > 50000:
                return content[:50000] + "\n... (truncated)"

            return content
        except urllib.error.URLError as e:
            return f"Error fetching {url}: {e}"
        except Exception as e:
            return f"Error: {str(e)}"
