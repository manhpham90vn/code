from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.theme import Theme

from .client import ClaudeClient
from .commands import get_command
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

            # Show tool output to user
            output = str(result).strip()
            if output:
                max_lines = 30
                lines = output.split("\n")
                if len(lines) > max_lines:
                    shown = "\n".join(lines[:max_lines])
                    console.print(
                        f"[dim]{escape(shown)}\n... ({len(lines) - max_lines} more lines)[/dim]"
                    )
                else:
                    console.print(f"[dim]{escape(output)}[/dim]")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                }
            )

    return tool_results


def log_token_usage(response):
    """Log token usage and estimated cost."""
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

    console.print(f"[dim]📊 {' | '.join(parts)}[/dim]")


def stream_response(client, context, tools, max_retries: int = 3) -> object:
    """Stream a response from Claude, displaying text and thinking in real-time.

    Retries on transient connection errors (e.g. peer closed connection).
    Returns the final Message object for further processing (tool_use, etc.).
    """
    import httpx

    for attempt in range(1, max_retries + 1):
        try:
            has_text = False
            in_thinking = False
            with client.stream_message(
                messages=context.messages,
                tools=tools,
                system=context.system_prompt,
            ) as stream:
                for event in stream:
                    if event.type == "thinking":
                        if not in_thinking:
                            print("🤔 ", end="", flush=True)
                            in_thinking = True
                        print(event.thinking, end="", flush=True)
                    elif event.type == "text":
                        if in_thinking:
                            print()  # newline after thinking
                            in_thinking = False
                        print(event.text, end="", flush=True)
                        has_text = True

                if in_thinking:
                    pass  # No closing tag needed
                if has_text:
                    print()  # newline after streamed text

                return stream.get_final_message()

        except (httpx.RemoteProtocolError, httpx.ReadError, ConnectionError):
            if attempt < max_retries:
                wait = 2**attempt
                console.print(
                    f"\n[warning]⚠ Connection lost, retrying in {wait}s "
                    f"(attempt {attempt}/{max_retries})...[/warning]"
                )
                time.sleep(wait)
            else:
                raise


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
                parts = user_input.split(maxsplit=1)
                cmd_name = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""

                # Handle special /clear and /quit inline
                if cmd_name == "/clear":
                    context.clear()
                    console.print("[success]Conversation history cleared[/success]")
                    continue
                elif cmd_name in ["/quit", "/exit"]:
                    break

                # Dispatch to registered commands
                cmd = get_command(cmd_name.lstrip("/"))
                if cmd:
                    cmd.execute(
                        cmd_args,
                        client=client,
                        context=context,
                        console=console,
                        stream_fn=stream_response,
                        log_usage_fn=log_token_usage,
                    )
                    continue

                console.print(f"[error]Unknown command: {cmd_name}[/error]")
                continue

            if not user_input.strip():
                continue

            # Append user message to context
            context.add_user_message(user_input)

            # Call the API
            try:
                response = stream_response(client, context, tools)
                log_token_usage(response)

                # Process tool-use loop
                while response.stop_reason == "tool_use":
                    # Append assistant message (contains tool_use blocks)
                    context.add_assistant_message([c.model_dump() for c in response.content])

                    # Execute requested tools
                    tool_results = handle_tool_use(response)

                    # Append tool results to context
                    context.add_tool_results(tool_results)

                    # Send tool results back to the API
                    response = stream_response(client, context, tools)
                    log_token_usage(response)

                # Save assistant response to context
                context.add_assistant_message([c.model_dump() for c in response.content])

            except Exception as e:
                import traceback

                console.print(f"[error]Error: {escape(str(e))}[/error]")
                console.print(f"[dim]{escape(traceback.format_exc())}[/dim]")

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
        console.print(f"[error]Failed to initialize client: {escape(str(e))}[/error]")
        console.print(
            "[dim]Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL[/dim]"
        )
        sys.exit(1)

    context = Context()
    chat_loop(client, context)


if __name__ == "__main__":
    main()
