"""Conversation context management."""

from dataclasses import dataclass, field


@dataclass
class Context:
    """Manages conversation history and project context."""

    messages: list[dict] = field(default_factory=list)
    system_prompt: str = (
        "You are an AI coding assistant running inside a CLI tool. "
        "You have access to tools for reading, writing, editing files and running shell commands. "
        "Use tools when needed to help the user. Be concise and helpful. "
        "Respond in the same language the user uses."
    )

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: list) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict]) -> None:
        self.messages.append({"role": "user", "content": results})

    def clear(self) -> None:
        self.messages.clear()
