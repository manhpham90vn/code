from __future__ import annotations

import os
import sys
import time
import traceback

import httpx
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.theme import Theme

from .client import ClaudeClient
from .commands import get_command
from .config import get_mcp_servers, load_config
from .context import Context
from .mcp import MCPManager, MCPServerConfig
from .permissions import PermissionManager
from .registry import discover_all, registry
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


def handle_tool_use(
    response,
    context: Context,
    mcp_manager: MCPManager | None = None,
    permission_manager: PermissionManager | None = None,
) -> list[dict]:
    """Execute tool calls from the response and collect results."""
    tool_results = []

    for block in response.content:
        if block.type == "tool_use":
            tool_name = block.name

            # Determine if tool is read-only
            is_read_only = False
            if not tool_name.startswith("mcp__"):
                tool_class = registry.get_tool(tool_name)
                if tool_class:
                    is_read_only = getattr(tool_class, "read_only", False)

            # Permission check
            if permission_manager and not permission_manager.check(
                tool_name, block.input, is_read_only, console
            ):
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Tool execution denied by user.",
                    }
                )
                continue

            # Check if it's an MCP tool
            if mcp_manager and tool_name.startswith("mcp__"):
                console.print(f"[dim]🔧 MCP: {tool_name}({block.input})[/dim]")
                result = mcp_manager.call_tool(tool_name, block.input)
            else:
                # Built-in tool
                # Log tool input details
                if tool_name == "run_bash":
                    cmd = block.input.get("command", "")
                    console.print(f"[dim]$ {cmd}[/dim]")
                elif tool_name == "read_file":
                    path = block.input.get("file_path", "")
                    console.print(f"[dim]📄 Reading {path}[/dim]")
                elif tool_name == "write_file":
                    path = block.input.get("file_path", "")
                    console.print(f"[dim]✏️  Writing {path}[/dim]")
                elif tool_name == "edit_file":
                    path = block.input.get("file_path", "")
                    console.print(f"[dim]✏️  Editing {path}[/dim]")
                else:
                    console.print(f"[dim]🔧 {tool_name}({block.input})[/dim]")

                try:
                    result = execute_tool(tool_name, block.input)
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

            # Store last output for $LAST_OUTPUT substitution
            if output:
                context.set_last_output(output)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                }
            )

    return tool_results


# Model pricing (USD per 1M tokens)
# Format: {model_id: (input, output, cache_write, cache_read)}
MODEL_PRICING = {
    "claude-opus-4-6": (5.00, 25.00, 6.25, 0.50),
    "claude-sonnet-4-6": (3.00, 15.00, 3.75, 0.30),
}


def _get_model_pricing(model: str) -> tuple[float, float, float, float]:
    """Get pricing for a model. Returns default pricing if model not found."""
    # Exact match first
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    # Default to Opus pricing
    return (5.00, 25.00, 6.25, 0.50)


def calc_cost(
    input_tokens: int,
    output_tokens: int,
    cache_create: int,
    cache_read: int,
    model: str,
) -> float:
    """Calculate cost in USD for given token counts."""
    input_price, output_price, cache_write_price, cache_read_price = _get_model_pricing(model)
    return (
        (input_tokens / 1_000_000) * input_price
        + (output_tokens / 1_000_000) * output_price
        + (cache_create / 1_000_000) * cache_write_price
        + (cache_read / 1_000_000) * cache_read_price
    )


def log_token_usage(response, model: str | None = None, context: Context | None = None):
    """Log token usage, estimated cost, and accumulate totals in context."""
    if model is None:
        model = "claude-opus-4-6"

    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    # Accumulate in context
    if context:
        context.add_usage(input_tokens, output_tokens, cache_create, cache_read)

    req_cost = calc_cost(input_tokens, output_tokens, cache_create, cache_read, model)

    parts = [
        f"{input_tokens} in / {output_tokens} out",
    ]
    if cache_create or cache_read:
        parts.append(f"cache: {cache_create} write / {cache_read} read")
    parts.append(f"${req_cost:.4f}")

    # Show running total
    if context:
        session_cost = calc_cost(
            context.total_input_tokens,
            context.total_output_tokens,
            context.total_cache_create_tokens,
            context.total_cache_read_tokens,
            model,
        )
        parts.append(f"total: ${session_cost:.4f}")

    console.print(f"[dim]📊 {' | '.join(parts)}[/dim]")


def stream_response(client, context, tools, max_retries: int = 3) -> object:
    """Stream a response from Claude, displaying text and thinking in real-time.

    Retries on transient connection errors (e.g. peer closed connection).
    Returns the final Message object for further processing (tool_use, etc.).
    """
    for attempt in range(1, max_retries + 1):
        try:
            collected_text = ""
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
                        collected_text += event.text

                if in_thinking:
                    pass  # No closing tag needed
                if collected_text:
                    console.print(Markdown(collected_text))

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


def chat_loop(client: ClaudeClient, context: Context, mcp_manager: MCPManager | None = None):
    """Main chat loop."""
    # Get built-in tools
    tools = get_all_tools()

    # Add MCP tools if available
    if mcp_manager:
        mcp_tools = mcp_manager.get_tools()
        tools.extend(mcp_tools)

    # Permission manager for tool confirmation
    permissions = PermissionManager()

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
                    # Show total cost before clearing
                    session_cost = calc_cost(
                        context.total_input_tokens,
                        context.total_output_tokens,
                        context.total_cache_create_tokens,
                        context.total_cache_read_tokens,
                        client.model,
                    )
                    if session_cost > 0:
                        console.print(f"[dim]💰 Session cost: ${session_cost:.4f}[/dim]")
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
                        log_usage_fn=lambda r: log_token_usage(r, client.model, context),
                    )
                    continue

                console.print(f"[error]Unknown command: {cmd_name}[/error]")
                continue

            if not user_input.strip():
                continue

            # Prepend last_output to user input if it's set (e.g., after failed /commit)
            if context.last_output:
                user_input = (
                    f"[Previous output]\n{context.last_output}\n\n[User request]\n{user_input}"
                )
                # Clear after using so it doesn't persist to next message
                context.last_output = ""

            # Append user message to context
            context.add_user_message(user_input)

            # Call the API
            try:
                response = stream_response(client, context, tools)
                log_token_usage(response, client.model, context)

                # Process tool-use loop
                while response.stop_reason == "tool_use":
                    # Append assistant message (contains tool_use blocks)
                    context.add_assistant_message([c.model_dump() for c in response.content])

                    # Execute requested tools
                    tool_results = handle_tool_use(response, context, mcp_manager, permissions)

                    # Append tool results to context
                    context.add_tool_results(tool_results)

                    # Send tool results back to the API
                    response = stream_response(client, context, tools)
                    log_token_usage(response, client.model, context)

                # Save assistant response to context
                context.add_assistant_message([c.model_dump() for c in response.content])

            except Exception as e:
                console.print(f"[error]Error: {escape(str(e))}[/error]")
                console.print(f"[dim]{escape(traceback.format_exc())}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[dim]Ctrl+C — Type /quit to exit[/dim]")
            continue
        except EOFError:
            break

    # Show total cost on exit
    session_cost = calc_cost(
        context.total_input_tokens,
        context.total_output_tokens,
        context.total_cache_create_tokens,
        context.total_cache_read_tokens,
        client.model,
    )
    if session_cost > 0:
        console.print(f"[dim]💰 Session total: ${session_cost:.4f}[/dim]")
    console.print("\n[success]Bye![/success]")


def main():
    """Entry point."""
    load_dotenv()
    print_welcome()

    # Initialize plugin system (auto-discovery)
    discover_all()

    # Initialize MCP servers from config
    mcp_manager = None
    config = load_config()
    mcp_configs = get_mcp_servers(config)
    if mcp_configs:
        mcp_manager = MCPManager()
        for name, server_config in mcp_configs.items():
            try:
                mcp_manager.add_server(
                    MCPServerConfig(
                        name=name,
                        command=server_config.get("command", ""),
                        args=server_config.get("args", []),
                        env=server_config.get("env", {}),
                    )
                )
                # Register in registry for help display
                registry.register_mcp_server(name, server_config)
                console.print(f"[dim]Started MCP server: {name}[/dim]")
            except Exception as e:
                console.print(f"[warning]Failed to start MCP server {name}: {e}[/warning]")

    # SDK reads env vars: ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY
    try:
        client = ClaudeClient(
            model=config.get("model", "claude-opus-4-6"),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"),
        )
    except Exception as e:
        console.print(f"[error]Failed to initialize client: {escape(str(e))}[/error]")
        console.print(
            "[dim]Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL[/dim]"
        )
        sys.exit(1)

    try:
        context = Context()
        chat_loop(client, context, mcp_manager)
    finally:
        if mcp_manager:
            mcp_manager.stop_all()


if __name__ == "__main__":
    main()
