from __future__ import annotations

import httpx
from anthropic import Anthropic
from anthropic.lib.streaming import MessageStream
from anthropic.types import Message

USER_AGENT = "claude-cli/1.0 (github.com/anthropic/claude-cli)"


def _override_user_agent(request: httpx.Request):
    """Override the default SDK user-agent (some proxies block it)."""
    request.headers["user-agent"] = USER_AGENT


class ClaudeClient:
    """Claude API client."""

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        base_url: str | None = None,
        auth_token: str | None = None,
        api_key: str | None = None,
    ):
        # Explicit params override env vars; omitted ones fall back to SDK defaults
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        if auth_token:
            kwargs["auth_token"] = auth_token
        if api_key:
            kwargs["api_key"] = api_key

        http_client = httpx.Client(event_hooks={"request": [_override_user_agent]})
        self.client = Anthropic(http_client=http_client, **kwargs)
        self.model = model

    def send_message(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> Message:
        """Send a message and return the parsed response."""
        # Build cacheable system prompt block
        sys_blocks = None
        if system:
            sys_blocks = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        # Mark the last tool for prompt caching
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
    ) -> MessageStream:
        """Stream a response from Claude. Use as context manager.

        Usage:
            with client.stream_message(...) as stream:
                for event in stream:
                    if event.type == "text":
                        print(event.text, end="", flush=True)
                response = stream.get_final_message()
        """
        sys_blocks = None
        if system:
            sys_blocks = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        cached_tools = list(tools)
        if cached_tools:
            cached_tools[-1] = {
                **cached_tools[-1],
                "cache_control": {"type": "ephemeral"},
            }

        return self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=sys_blocks,
            messages=messages,
            tools=cached_tools,
        )
