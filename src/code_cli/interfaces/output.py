"""Broadcast output to all registered interfaces."""

from __future__ import annotations

import asyncio
import logging

from .base import InputInterface, OutputInterface

logger = logging.getLogger(__name__)


class OutputBus(OutputInterface):
    """Fans out every call to all registered backends."""

    def __init__(self) -> None:
        self._backends: list[OutputInterface] = []

    def register(self, backend: OutputInterface) -> None:
        self._backends.append(backend)

    async def _broadcast(self, method: str, *args, **kwargs) -> None:
        tasks = [getattr(b, method)(*args, **kwargs) for b in self._backends]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.warning("Output error in %s: %s", type(self._backends[i]).__name__, r)

    async def send_response(self, text: str) -> None:
        await self._broadcast("send_response", text)

    async def send_tool_activity(self, icon: str, summary: str) -> None:
        await self._broadcast("send_tool_activity", icon, summary)

    async def send_tool_output(self, output: str, truncated: bool = False) -> None:
        await self._broadcast("send_tool_output", output, truncated=truncated)

    async def send_error(self, error: str) -> None:
        await self._broadcast("send_error", error)

    async def send_status(self, text: str) -> None:
        await self._broadcast("send_status", text)

    async def send_thinking(self, text: str) -> None:
        await self._broadcast("send_thinking", text)


class InputBus:
    """Broadcasts input from one source to all other registered input interfaces."""

    def __init__(self) -> None:
        self._backends: dict[str, InputInterface] = {}

    def register(self, name: str, backend: InputInterface) -> None:
        self._backends[name] = backend

    async def broadcast_input(self, source: str, text: str) -> None:
        """Notify all interfaces except the source about new input."""
        tasks = [
            backend.display_input(source, text)
            for name, backend in self._backends.items()
            if name != source
        ]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning("InputBus error: %s", r)
