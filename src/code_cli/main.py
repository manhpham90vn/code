from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.theme import Theme

from .client import ClaudeClient
from .context import Context
from .tools import execute_tool, get_all_tools

# Terminal theme
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "red bold",
        "success": "green",
        "dim": "dim",
    }
)

console = Console(theme=custom_theme)


def print_welcome():
    """Print the welcome banner."""
    console.print(
        Panel.fit(
            "[bold cyan]AI Coding Assistant CLI[/bold cyan]\n"
            "Powered by Claude API\n\n"
            "[dim]Type /help to see available commands[/dim]",
            border_style="cyan",
        )
    )


def print_help():
    """Print the help panel."""
    console.print(
        Panel.fit(
            "[bold]Commands:[/bold]\n"
            "/help   - Show help\n"
            "/clear  - Clear conversation history\n"
            "/quit   - Exit\n\n"
            "[bold]Tools:[/bold]\n"
            "- read - Read files\n"
            "- write - Write files\n"
            "- edit - Edit files\n"
            "- bash - Run shell commands\n"
            "- grep - Search file contents\n"
            "- glob - Find files by pattern\n"
            "- web_search - Search the web\n"
            "- web_fetch - Fetch URL content",
            border_style="green",
        )
    )


def handle_thinking(response):
    """Display thinking blocks from the response, if any."""
    for block in response.content:
        if block.type == "thinking":
            console.print(f"[dim italic]🤔 {block.thinking}[/dim italic]")


def handle_tool_use(response) -> list[dict]:
    """Execute tool calls from the response and collect results."""
    tool_results = []

    for block in response.content:
        if block.type == "tool_use":
            # Log tool input details
            if block.name == "run_bash":
                cmd = block.input.get("command", "")
                console.print(f"[dim]$ {cmd}[/dim]")
            elif block.name == "read_file":
                path = block.input.get("file_path", "")
                console.print(f"[dim]📄 Reading {path}[/dim]")
            elif block.name == "write_file":
                path = block.input.get("file_path", "")
                console.print(f"[dim]✏️  Writing {path}[/dim]")
            elif block.name == "edit_file":
                path = block.input.get("file_path", "")
                console.print(f"[dim]✏️  Editing {path}[/dim]")
            else:
                console.print(f"[dim]🔧 {block.name}({block.input})[/dim]")

            try:
                result = execute_tool(block.name, block.input)
            except Exception as e:
                result = f"Error: {str(e)}"

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                }
            )

    return tool_results


def handle_text_response(response):
    """Render text blocks from the response as markdown."""
    for block in response.content:
        if block.type == "text":
            console.print(Markdown(block.text))


def log_token_usage(response, status_code: int | None = None):
    """Log token usage, estimated cost, and HTTP status code."""
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    # Claude Opus 4.6 pricing (USD per 1M tokens)
    # Input: $5, Output: $25, Cache write: $6.25, Cache read: $0.50
    input_cost = (input_tokens / 1_000_000) * 5.00
    output_cost = (output_tokens / 1_000_000) * 25.00
    cache_write_cost = (cache_create / 1_000_000) * 6.25
    cache_read_cost = (cache_read / 1_000_000) * 0.50
    total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

    parts = [
        f"{input_tokens} in / {output_tokens} out",
    ]
    if cache_create or cache_read:
        parts.append(f"cache: {cache_create} write / {cache_read} read")
    parts.append(f"${total_cost:.4f}")
    if status_code:
        parts.append(f"HTTP {status_code}")

    console.print(f"[dim]📊 {' | '.join(parts)}[/dim]")


def chat_loop(client: ClaudeClient, context: Context):
    """Main chat loop."""
    tools = get_all_tools()

    # Set up prompt session with history and IME support
    session = PromptSession(
        history=FileHistory(os.path.expanduser("~/.ai_cli/history")),
        auto_suggest=AutoSuggestFromHistory(),
        enable_open_in_editor=True,
    )

    while True:
        try:
            user_input = session.prompt("❯ ")

            # Handle slash commands
            if user_input.startswith("/"):
                cmd = user_input.split()[0].lower()
                if cmd == "/help":
                    print_help()
                    continue
                elif cmd == "/clear":
                    context.clear()
                    console.print("[success]Conversation history cleared[/success]")
                    continue
                elif cmd in ["/quit", "/exit"]:
                    break
                else:
                    console.print(f"[error]Unknown command: {cmd}[/error]")
                    continue

            if not user_input.strip():
                continue

            # Append user message to context
            context.add_user_message(user_input)

            # Call the API
            try:
                api_response = client.send_message(
                    messages=context.messages,
                    tools=tools,
                    system=context.system_prompt,
                )
                response = api_response.data
                log_token_usage(response, api_response.status_code)

                # Process tool-use loop
                while response.stop_reason == "tool_use":
                    # Display thinking before running tools
                    handle_thinking(response)

                    # Append assistant message (contains tool_use blocks)
                    context.add_assistant_message([c.model_dump() for c in response.content])

                    # Execute requested tools
                    tool_results = handle_tool_use(response)

                    # Append tool results to context
                    context.add_tool_results(tool_results)

                    # Send tool results back to the API
                    api_response = client.send_message(
                        messages=context.messages,
                        tools=tools,
                        system=context.system_prompt,
                    )
                    response = api_response.data
                    log_token_usage(response, api_response.status_code)

                # Display final thinking
                handle_thinking(response)

                # Render text response
                handle_text_response(response)

                # Save assistant response to context
                context.add_assistant_message([c.model_dump() for c in response.content])

            except Exception as e:
                import traceback

                console.print(f"[error]Error: {str(e)}[/error]")
                console.print(f"[dim]{traceback.format_exc()}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[dim]Ctrl+C — Type /quit to exit[/dim]")
            continue
        except EOFError:
            break

    console.print("\n[success]Bye![/success]")


def main():
    """Entry point."""
    load_dotenv()
    print_welcome()

    # SDK reads env vars: ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY
    try:
        client = ClaudeClient(
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"),
        )
    except Exception as e:
        console.print(f"[error]Failed to initialize client: {e}[/error]")
        console.print(
            "[dim]Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL[/dim]"
        )
        sys.exit(1)

    context = Context()
    chat_loop(client, context)


if __name__ == "__main__":
    main()
