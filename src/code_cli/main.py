from __future__ import annotations

import os
import sys

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

# Custom theme cho terminal
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
    """In welcome message."""
    console.print(
        Panel.fit(
            "[bold cyan]AI Coding Assistant CLI[/bold cyan]\n"
            "Powered by Claude API\n\n"
            "[dim]Gõ /help để xem các lệnh có sẵn[/dim]",
            border_style="cyan",
        )
    )


def print_help():
    """In help message."""
    console.print(
        Panel.fit(
            "[bold]Các lệnh:[/bold]\n"
            "/help   - Hiển thị help\n"
            "/clear  - Xóa conversation history\n"
            "/quit   - Thoát\n\n"
            "[bold]Các tools:[/bold]\n"
            "• read - Đọc file\n"
            "• write - Ghi file\n"
            "• edit - Chỉnh sửa file\n"
            "• bash - Chạy lệnh shell\n"
            "• grep - Tìm kiếm trong file\n"
            "• glob - Tìm file theo pattern\n"
            "• web_search - Tìm kiếm web\n"
            "• web_fetch - Lấy nội dung từ URL",
            border_style="green",
        )
    )


def handle_thinking(response):
    """In thinking blocks từ response (nếu có)."""
    for block in response.content:
        if block.type == "thinking":
            console.print(f"[dim italic]🤔 {block.thinking}[/dim italic]")


def handle_tool_use(response) -> list[dict]:
    """Xử lý tool use từ Claude response."""
    tool_results = []

    for block in response.content:
        if block.type == "tool_use":
            # Hiển thị chi tiết input của tool
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
                console.print(
                    f"[dim]🔧 {block.name}({block.input})[/dim]"
                )

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
    """Xử lý text response từ Claude."""
    for block in response.content:
        if block.type == "text":
            console.print(Markdown(block.text))


def log_token_usage(response):
    """Log token usage và cost."""
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    # Giá Claude Opus 4.6 (USD per 1M tokens)
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


def chat_loop(client: ClaudeClient, context: Context):
    """Main chat loop."""
    tools = get_all_tools()

    # Setup prompt session với IME support
    session = PromptSession(
        history=FileHistory(os.path.expanduser("~/.ai_cli/history")),
        auto_suggest=AutoSuggestFromHistory(),
        enable_open_in_editor=True,
    )

    while True:
        try:
            user_input = session.prompt("❯ ")

            # Xử lý commands
            if user_input.startswith("/"):
                cmd = user_input.split()[0].lower()
                if cmd == "/help":
                    print_help()
                    continue
                elif cmd == "/clear":
                    context.clear()
                    console.print("[success]Đã xóa conversation history[/success]")
                    continue
                elif cmd in ["/quit", "/exit"]:
                    break
                else:
                    console.print(f"[error]Lệnh không hợp lệ: {cmd}[/error]")
                    continue

            if not user_input.strip():
                continue

            # Thêm user message vào context
            context.add_user_message(user_input)

            # Gọi API
            try:
                response = client.send_message(
                    messages=context.messages,
                    tools=tools,
                    system=context.system_prompt,
                )
                log_token_usage(response)

                # Xử lý response
                while response.stop_reason == "tool_use":
                    # Hiển thị thinking trước khi chạy tool
                    handle_thinking(response)

                    # Thêm assistant message (chứa tool_use)
                    context.add_assistant_message([c.model_dump() for c in response.content])

                    # Execute tools
                    tool_results = handle_tool_use(response)

                    # Thêm tool results
                    context.add_tool_results(tool_results)

                    # Gọi lại API với kết quả
                    response = client.send_message(
                        messages=context.messages,
                        tools=tools,
                        system=context.system_prompt,
                    )
                    log_token_usage(response)

                # Hiển thị thinking cuối cùng
                handle_thinking(response)

                # In text response
                handle_text_response(response)

                # Lưu assistant response vào context
                context.add_assistant_message([c.model_dump() for c in response.content])

            except Exception as e:
                import traceback

                console.print(f"[error]Error: {str(e)}[/error]")
                console.print(f"[dim]{traceback.format_exc()}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[dim]Ctrl+C - Gõ /quit để thoát[/dim]")
            continue
        except EOFError:
            break

    console.print("\n[success]Bye![/success]")


def main():
    """Entry point."""
    print_welcome()

    # SDK tự đọc env vars: ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY
    try:
        client = ClaudeClient(
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"),
        )
    except Exception as e:
        console.print(f"[error]Không thể khởi tạo client: {e}[/error]")
        console.print(
            "[dim]Đặt ANTHROPIC_API_KEY hoặc ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL[/dim]"
        )
        sys.exit(1)

    context = Context()
    chat_loop(client, context)


if __name__ == "__main__":
    main()
