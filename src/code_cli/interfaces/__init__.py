"""I/O interfaces - supports multiple backends (terminal, Telegram, etc.)."""

from .base import InputInterface, OutputInterface
from .output import InputBus, OutputBus
from .telegram import TelegramInput, TelegramOutput, create_telegram_interface, is_telegram_enabled
from .terminal import TerminalInput, TerminalOutput

__all__ = [
    "InputBus",
    "InputInterface",
    "OutputBus",
    "OutputInterface",
    "TerminalInput",
    "TerminalOutput",
    "TelegramInput",
    "TelegramOutput",
    "create_telegram_interface",
    "is_telegram_enabled",
]
