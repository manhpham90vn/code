"""Telegram interface (input + output).

Mirrors terminal I/O to Telegram. Messages from Telegram go into the
shared input queue; all output is broadcast to every active Telegram chat.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .base import InputInterface, OutputInterface

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _get_config() -> dict[str, Any]:
    return {
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "allowed_users": _parse_ids(os.getenv("TELEGRAM_ALLOWED_USERS")),
    }


def _parse_ids(value: str | None) -> set[int]:
    if not value:
        return set()
    try:
        return {int(u.strip()) for u in value.split(",") if u.strip()}
    except ValueError:
        return set()


def is_telegram_enabled() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN"))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class TelegramOutput(OutputInterface):
    """Broadcast output to all active Telegram chats."""

    def __init__(self, app: Application) -> None:
        self._app = app
        # chat_ids that have interacted with the bot
        self._chat_ids: set[int] = set()

    def add_chat(self, chat_id: int) -> None:
        self._chat_ids.add(chat_id)

    def add_allowed_users(self, user_ids: set[int]) -> None:
        """Add allowed users to receive broadcasts even before they start the bot."""
        self._chat_ids.update(user_ids)

    async def send_response(self, text: str) -> None:
        await self._broadcast(text, parse_mode="Markdown")

    async def send_tool_activity(self, icon: str, summary: str) -> None:
        await self._broadcast(f"{icon} _{summary}_", parse_mode="Markdown")

    async def send_tool_output(self, output: str, truncated: bool = False) -> None:
        max_len = 3900
        if len(output) > max_len:
            output = output[:max_len] + "\n...truncated"
        await self._broadcast(f"```\n{output}\n```", parse_mode="Markdown")

    async def send_error(self, error: str) -> None:
        await self._broadcast(f"❌ {error}")

    async def send_status(self, text: str) -> None:
        await self._broadcast(f"_{text}_", parse_mode="Markdown")

    async def send_thinking(self, text: str) -> None:
        # For Telegram, use code block to show thinking nicely
        await self._broadcast(f"```\n{text}\n```", parse_mode="Markdown")

    async def _broadcast(self, text: str, **kwargs) -> None:
        bot = self._app.bot
        for chat_id in list(self._chat_ids):
            try:
                await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            except Exception:
                # Fallback: try without parse_mode
                try:
                    await bot.send_message(chat_id=chat_id, text=text)
                except Exception as e:
                    logger.warning("Failed to send to %s: %s", chat_id, e)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class TelegramInput(InputInterface):
    """Receive messages from Telegram, push to shared input queue."""

    def __init__(self, app: Application, tg_output: TelegramOutput) -> None:
        self._app = app
        self._output = tg_output
        self._config = _get_config()

    async def start(self, queue: asyncio.Queue[tuple[str, str]]) -> None:
        """Wire up handlers and start polling."""
        allowed = self._config["allowed_users"]
        output = self._output

        async def _check_auth(update: Update) -> bool:
            user = update.effective_user
            if not user:
                return False
            if allowed and user.id not in allowed:
                await update.message.reply_text("⛔ Not authorized.")
                return False
            # Register chat for output broadcast
            output.add_chat(update.effective_chat.id)
            return True

        async def _on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            if not await _check_auth(update):
                return
            await update.message.reply_text(
                "👋 Connected to Claude CLI.\nSend messages here or in the terminal.",
            )

        async def _on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
            if not await _check_auth(update):
                return
            text = update.message.text
            if text:
                await update.message.chat.send_action("typing")
                await queue.put(("telegram", text))

        self._app.add_handler(CommandHandler("start", _on_start))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_message))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def stop(self) -> None:
        pass  # Handled by CancelledError in start()

    async def display_input(self, source: str, text: str) -> None:
        """Display input from another source (e.g., terminal)."""
        await self._output._broadcast(f"📝 Input from {source}: {text}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


async def create_telegram_interface(
    input_queue: asyncio.Queue[tuple[str, str]],
) -> tuple[TelegramOutput, TelegramInput, asyncio.Task] | None:
    """Create and start Telegram interfaces.

    Returns (output_interface, input_interface, background_task) or None if not configured.
    """
    if not is_telegram_enabled():
        return None

    config = _get_config()
    app = Application.builder().token(config["bot_token"]).build()

    tg_output = TelegramOutput(app)
    # Pre-populate with allowed users so they receive broadcasts from terminal
    tg_output.add_allowed_users(config["allowed_users"])
    tg_input = TelegramInput(app, tg_output)

    task = asyncio.create_task(tg_input.start(input_queue))
    return tg_output, tg_input, task
