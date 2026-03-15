"""Conversation context management."""

from __future__ import annotations

from dataclasses import dataclass, field

# Max conversation turns to keep (1 turn = user + assistant pair)
DEFAULT_MAX_TURNS = 50


@dataclass
class Context:
    """Manages conversation history and project context."""

    messages: list[dict] = field(default_factory=list)
    last_output: str = ""
    max_turns: int = DEFAULT_MAX_TURNS
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
        self._trim()

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

    def _trim(self) -> None:
        """Trim oldest messages when exceeding max_turns.

        Keeps the conversation within bounds to avoid exceeding API context
        limits and controlling cost.  A "turn" is roughly a user+assistant
        pair, but tool_result messages in between are counted individually.
        We trim from the front, always keeping at least the latest message.
        """
        max_messages = self.max_turns * 2  # rough: 2 messages per turn
        if len(self.messages) <= max_messages:
            return

        overflow = len(self.messages) - max_messages
        self.messages = self.messages[overflow:]

    def clear(self) -> None:
        self.messages.clear()
        self.last_output = ""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_create_tokens = 0
        self.total_cache_read_tokens = 0
