from __future__ import annotations

import asyncio
import os
import sys
import traceback

import httpx
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
from .config import get_mcp_servers, load_config
from .context import Context
from .interfaces import (
    InputBus,
    OutputBus,
    TelegramInput,
    TerminalInput,
    TerminalOutput,
    create_telegram_interface,
)
from .mcp import MCPManager, MCPServerConfig
from .models import DEFAULT_MODEL, calc_cost, log_token_usage
from .permissions import PermissionManager, _format_tool_summary
from .plugin_system import discover_all, get_tool, register_mcp_server
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


def print_welcome() -> None:
    """Print the welcome banner."""
    console.print(
        Panel.fit(
            "[bold cyan]AI Coding Assistant CLI[/bold cyan]\n"
            "Powered by Claude API\n\n"
            "[dim]Type /help to see available commands[/dim]",
            border_style="cyan",
        )
    )


async def handle_tool_use(
    response,
    context: Context,
    mcp_manager: MCPManager | None,
    permissions: PermissionManager,
    output: OutputBus,
) -> list[dict]:
    """Execute tool calls from the response and collect results."""
    tool_results: list[dict] = []

    for block in response.content:
        if block.type != "tool_use":
            continue

        tool_name: str = block.name

        # Resolve tool class for built-in tools
        tool_class = None
        is_read_only = False
        icon = "🔧"
        if not tool_name.startswith("mcp__"):
            tool_class = get_tool(tool_name)
            if tool_class:
                is_read_only = getattr(tool_class, "read_only", False)
                icon = getattr(tool_class, "icon", "🔧")

        # Permission check
        if not permissions.check(tool_name, block.input, is_read_only, console, icon=icon):
            await output.send_status(f"{icon} {tool_name} - denied")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Tool execution denied by user.",
                }
            )
            continue

        # Execute tool
        if tool_name.startswith("mcp__"):
            await output.send_status(f"🔧 MCP: {tool_name}")
            if mcp_manager:
                result = await mcp_manager.call_tool(tool_name, block.input)
            else:
                result = "MCP tool called but no MCP manager available"
        else:
            # Built-in tool — show summary
            summary = _format_tool_summary(tool_name, block.input)
            await output.send_tool_activity(icon, summary or tool_name)

            try:
                result = await asyncio.to_thread(execute_tool, tool_name, block.input)
            except Exception as e:
                result = f"Error: {e}"

        # Show tool output
        output_str = str(result).strip()
        if output_str:
            await output.send_tool_output(output_str)

        # Store last output for $LAST_OUTPUT substitution
        if output_str:
            context.set_last_output(output_str)

        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            }
        )

    return tool_results


async def stream_response_async(
    client: ClaudeClient,
    context: Context,
    tools: list[dict],
    output: OutputBus,
    max_retries: int = 3,
) -> object:
    """Stream a response from Claude, displaying text and thinking in real-time."""
    loop = asyncio.get_running_loop()
    for attempt in range(1, max_retries + 1):
        try:
            return await asyncio.to_thread(
                _stream_response_sync, client, context, tools, output, loop
            )
        except (httpx.RemoteProtocolError, httpx.ReadError, ConnectionError):
            if attempt < max_retries:
                wait = 2**attempt
                await output.send_status(
                    f"⚠ Connection lost, retrying in {wait}s (attempt {attempt}/{max_retries})..."
                )
                await asyncio.sleep(wait)
            else:
                raise


def _stream_response_sync(
    client: ClaudeClient,
    context: Context,
    tools: list[dict],
    output: OutputBus,
    loop: asyncio.AbstractEventLoop,
) -> object:
    """Synchronous streaming helper."""
    collected_text = ""
    collected_thinking = ""
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
                collected_thinking += event.thinking
            elif event.type == "text":
                if in_thinking:
                    print()
                    in_thinking = False
                collected_text += event.text

        # Send collected thinking to non-terminal outputs (e.g. Telegram)
        if collected_thinking:
            asyncio.run_coroutine_threadsafe(output.send_thinking(collected_thinking), loop)

        if collected_text:
            # Send to output bus (both terminal and telegram)
            # Schedule on the event loop from the thread
            asyncio.run_coroutine_threadsafe(output.send_response(collected_text), loop)

        return stream.get_final_message()


async def chat_loop(
    client: ClaudeClient,
    context: Context,
    mcp_manager: MCPManager | None,
    input_queue: asyncio.Queue[tuple[str, str]],
    output: OutputBus,
    input_bus: InputBus,
) -> None:
    """Main chat loop - reads from input_queue, writes to output."""
    # Get built-in tools
    tools = get_all_tools()

    # Add MCP tools if available
    if mcp_manager:
        mcp_tools = await mcp_manager.get_tools()
        tools.extend(mcp_tools)

    # Permission manager
    permissions = PermissionManager()

    while True:
        try:
            # Read input from queue (could be from terminal or telegram)
            source, user_input = await input_queue.get()

            # Broadcast input to other interfaces
            await input_bus.broadcast_input(source, user_input)

            # Handle slash commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd_name = parts[0].lower()
                cmd_args = parts[1] if len(parts) > 1 else ""

                if cmd_name == "/clear":
                    session_cost = calc_cost(
                        context.total_input_tokens,
                        context.total_output_tokens,
                        context.total_cache_create_tokens,
                        context.total_cache_read_tokens,
                        client.model,
                    )
                    if session_cost > 0:
                        await output.send_status(f"💰 Session cost: ${session_cost:.4f}")
                    context.clear()
                    await output.send_status("Conversation cleared ✅")
                    continue
                elif cmd_name in ("/quit", "/exit"):
                    break

                # Dispatch to registered commands
                cmd = get_command(cmd_name.lstrip("/"))
                if cmd:
                    cmd.execute(
                        cmd_args,
                        client=client,
                        context=context,
                        console=console,
                        stream_fn=lambda c, ctx, t: _stream_response_sync(c, ctx, t, output),
                        log_usage_fn=lambda r: log_token_usage(r, client.model, context),
                    )
                    continue

                await output.send_error(f"Unknown command: {cmd_name}")
                continue

            if not user_input.strip():
                continue

            # Prepend last_output to user input if set
            if context.last_output:
                user_input = (
                    f"[Previous output]\n{context.last_output}\n\n[User request]\n{user_input}"
                )
                context.last_output = ""

            # Append user message to context
            context.add_user_message(user_input)

            # Call the API
            try:
                response = await stream_response_async(client, context, tools, output)
                msg = log_token_usage(response, client.model, context)
                await output.send_status(msg)

                # Process tool-use loop
                while response.stop_reason == "tool_use":
                    context.add_assistant_message([c.model_dump() for c in response.content])

                    tool_results = await handle_tool_use(
                        response, context, mcp_manager, permissions, output
                    )

                    context.add_tool_results(tool_results)

                    response = await stream_response_async(client, context, tools, output)
                    msg = log_token_usage(response, client.model, context)
                    await output.send_status(msg)

                # Save assistant response
                context.add_assistant_message([c.model_dump() for c in response.content])

            except Exception as e:
                await output.send_error(f"Error: {escape(str(e))}")
                await output.send_status(escape(traceback.format_exc()))

        except asyncio.CancelledError:
            break
        except Exception as e:
            await output.send_error(f"Error: {escape(str(e))}")

    # Show total cost on exit
    session_cost = calc_cost(
        context.total_input_tokens,
        context.total_output_tokens,
        context.total_cache_create_tokens,
        context.total_cache_read_tokens,
        client.model,
    )
    if session_cost > 0:
        await output.send_status(f"💰 Session total: ${session_cost:.4f}")
    await output.send_status("Bye!")


def main() -> None:
    """Entry point."""
    load_dotenv()
    print_welcome()
    asyncio.run(_main())


async def _main() -> None:
    """Async entry point."""
    # Initialize plugin system
    discover_all()

    # Initialize MCP servers
    mcp_manager: MCPManager | None = None
    config = load_config()
    mcp_configs = get_mcp_servers(config)
    if mcp_configs:
        mcp_manager = MCPManager()
        for name, server_config in mcp_configs.items():
            try:
                await mcp_manager.add_server(
                    MCPServerConfig(
                        name=name,
                        command=server_config.get("command", ""),
                        args=server_config.get("args", []),
                        env=server_config.get("env", {}),
                    )
                )
                register_mcp_server(name, server_config)
                console.print(f"[dim]Started MCP server: {name}[/dim]")
            except Exception as e:
                console.print(f"[warning]Failed to start MCP server {name}: {e}[/warning]")

    # Initialize Claude client
    try:
        client = ClaudeClient(
            model=config.get("model", DEFAULT_MODEL),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"),
        )
    except Exception as e:
        console.print(f"[error]Failed to initialize client: {escape(str(e))}[/error]")
        console.print(
            "[dim]Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL[/dim]"
        )
        sys.exit(1)

    # Setup interfaces
    output = OutputBus()
    input_bus = InputBus()
    input_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    # Terminal interface (always present)
    terminal_output = TerminalOutput(console)
    output.register(terminal_output)

    # Setup terminal input
    session: PromptSession = PromptSession(
        history=FileHistory(os.path.expanduser("~/.ai_cli/history")),
        auto_suggest=AutoSuggestFromHistory(),
        enable_open_in_editor=True,
    )
    terminal_input = TerminalInput(session, console)
    input_bus.register("terminal", terminal_input)

    # Telegram interface (if configured)
    tg_task: asyncio.Task | None = None
    tg_input: TelegramInput | None = None
    tg_data = await create_telegram_interface(input_queue)
    if tg_data:
        tg_output, tg_input, tg_task = tg_data
        output.register(tg_output)
        input_bus.register("telegram", tg_input)
        console.print("[dim]🤖 Telegram enabled[/dim]")

    # Start terminal input listener
    terminal_task = asyncio.create_task(terminal_input.start(input_queue))

    # Run chat loop
    context = Context()
    try:
        await chat_loop(client, context, mcp_manager, input_queue, output, input_bus)
    finally:
        terminal_input.stop()
        terminal_task.cancel()
        if tg_task:
            tg_task.cancel()
        if mcp_manager:
            await mcp_manager.stop_all()


if __name__ == "__main__":
    main()
