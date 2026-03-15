"""Conversation context management."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Context:
    """Manages conversation history and project context."""

    messages: list[dict] = field(default_factory=list)
    last_output: str = ""
    system_prompt: str = (
        "You are an AI coding assistant running inside a CLI tool. "
        "You have access to tools for reading, writing, editing files and running shell commands. "
        "Use tools when needed to help the user. Be concise and helpful. "
        "Respond in the same language the user uses."
    )

    # Token usage tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_create_tokens: int = 0
    total_cache_read_tokens: int = 0

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: list) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict]) -> None:
        self.messages.append({"role": "user", "content": results})

    def set_last_output(self, output: str) -> None:
        """Store the output from the last tool execution."""
        self.last_output = output

    def add_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_create: int = 0,
        cache_read: int = 0,
    ) -> None:
        """Add token usage to the running total."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cache_create_tokens += cache_create
        self.total_cache_read_tokens += cache_read

    def get_total_tokens(self) -> int:
        """Get total tokens used."""
        return (
            self.total_input_tokens
            + self.total_output_tokens
            + self.total_cache_create_tokens
            + self.total_cache_read_tokens
        )

    def clear(self) -> None:
        self.messages.clear()
        self.last_output = ""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_create_tokens = 0
        self.total_cache_read_tokens = 0
