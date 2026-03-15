"""MCP (Model Context Protocol) client - using official mcp SDK."""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class MCPManager:
    """Manages multiple MCP server connections using the official mcp SDK."""

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()

    async def add_server(self, config: MCPServerConfig) -> None:
        """Start and initialize an MCP server connection."""
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env={**os.environ, **config.env} if config.env else None,
        )

        read, write = await self._exit_stack.enter_async_context(stdio_client(params))
        session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._sessions[config.name] = session
        logger.info(f"MCP server '{config.name}' initialized")

    async def get_tools(self) -> list[dict]:
        """Get combined tool list from all MCP servers, prefixed with server name."""
        all_tools: list[dict] = []
        failed_servers: list[tuple[str, str]] = []
        for name, session in self._sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    all_tools.append(
                        {
                            "name": f"mcp__{name}__{tool.name}",
                            "description": tool.description or "",
                            "input_schema": tool.inputSchema,
                        }
                    )
            except Exception as e:
                failed_servers.append((name, str(e)))
                logger.warning(f"Failed to get tools from {name}: {e}")
        for name, err in failed_servers:
            logger.error(f"MCP server '{name}' failed: {err}")
        return all_tools

    async def call_tool(self, full_name: str, arguments: dict) -> str:
        """Call a tool, extracting server name from prefixed name."""
        if not full_name.startswith("mcp__"):
            return "Error: Not an MCP tool"

        parts = full_name.split("__", 2)
        if len(parts) < 3:
            return "Error: Invalid MCP tool name format"

        _, server_name, tool_name = parts

        if server_name not in self._sessions:
            return f"Error: Unknown MCP server: {server_name}"

        try:
            result = await self._sessions[server_name].call_tool(tool_name, arguments)
            # Format content blocks to string
            parts_out: list[str] = []
            for block in result.content:
                if block.type == "text":
                    parts_out.append(block.text)
            return "\n".join(parts_out) if parts_out else str(result.content)
        except Exception as e:
            logger.error(f"Error calling MCP tool {full_name}: {e}")
            return f"Error calling {full_name}: {e}"

    async def stop_all(self) -> None:
        """Stop all MCP servers by closing the exit stack."""
        await self._exit_stack.aclose()
        self._sessions.clear()

    def get_server_names(self) -> list[str]:
        """Get list of active MCP server names."""
        return list(self._sessions.keys())
