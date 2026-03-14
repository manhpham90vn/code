from collections.abc import Generator

import httpx
from anthropic import Anthropic
from anthropic.types import Message

# Monkey-patch để override user-agent (proxy chặn SDK user-agent mặc định)
_original_send = httpx.Client.send


def _patched_send(self, request, **kwargs):
    request.headers["user-agent"] = "claude-cli/1.0 (github.com/anthropic/claude-cli)"
    return _original_send(self, request, **kwargs)


httpx.Client.send = _patched_send


class ClaudeClient:
    """Client tương tác với Claude API."""

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        base_url: str | None = None,
        auth_token: str | None = None,
        api_key: str | None = None,
    ):
        # Truyền param sẽ ghi đè env vars, không truyền thì SDK tự đọc env
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        if auth_token:
            kwargs["auth_token"] = auth_token
        if api_key:
            kwargs["api_key"] = api_key

        self.client = Anthropic(**kwargs)
        self.model = model

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> Message:
        """Gửi message và nhận response."""
        # Cache system prompt
        sys_blocks = None
        if system:
            sys_blocks = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        # Cache tools (đánh dấu tool cuối)
        cached_tools = list(tools)
        if cached_tools:
            cached_tools[-1] = {
                **cached_tools[-1],
                "cache_control": {"type": "ephemeral"},
            }

        return self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=sys_blocks,
            messages=messages,
            tools=cached_tools,
        )

    def stream_message(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Stream response từ Claude."""
        stream = self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        )
        yield from stream.text_stream
