"""MCP (Model Context Protocol) client - stdio-based JSON-RPC communication."""

from __future__ import annotations

import json
import logging
import os
import select
import subprocess
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class MCPClient:
    """Client for communicating with MCP servers via stdio (JSON-RPC 2.0)."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._initialized = False
        self._stderr_output: list[str] = []
        self._stderr_thread: threading.Thread | None = None

    def _read_stderr(self) -> None:
        """Read stderr in a background thread to prevent blocking and capture errors."""
        assert self._process and self._process.stderr
        for line in self._process.stderr:
            line = line.strip()
            if line:
                self._stderr_output.append(line)
                logger.debug(f"MCP server {self.config.name} stderr: {line}")

    def _get_stderr_tail(self, max_lines: int = 10) -> str:
        """Get the last N lines of stderr output."""
        lines = self._stderr_output[-max_lines:]
        return "\n".join(lines) if lines else ""

    def _check_process_alive(self) -> None:
        """Check if the server process is still running, raise with details if not."""
        if not self._process:
            raise RuntimeError(f"MCP server '{self.config.name}' not started")
        returncode = self._process.poll()
        if returncode is not None:
            stderr_tail = self._get_stderr_tail()
            detail = f" stderr:\n{stderr_tail}" if stderr_tail else ""
            raise RuntimeError(
                f"MCP server '{self.config.name}' exited with code {returncode}.{detail}"
            )

    def start(self) -> None:
        """Start the MCP server process."""
        env = {**os.environ, **self.config.env}
        try:
            self._process = subprocess.Popen(
                [self.config.command, *self.config.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"MCP server '{self.config.name}': command '{self.config.command}' not found"
            )

        # Start background thread to drain stderr
        self._stderr_output.clear()
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_thread.start()

        logger.info(f"Started MCP server: {self.config.name}")

    def initialize(self) -> dict:
        """Send MCP initialize request and return server capabilities."""
        self._check_process_alive()

        request = self._build_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "code-cli",
                    "version": "0.1.0",
                },
            },
        )

        response = self._send_request(request)

        # Send initialized notification (required by MCP spec)
        self._send_notification("notifications/initialized", {})

        self._initialized = True
        logger.info(f"MCP server {self.config.name} initialized")
        return response.get("result", {})

    def list_tools(self) -> list[dict]:
        """Request list of available tools from MCP server."""
        self._check_process_alive()

        if not self._initialized:
            self.initialize()

        request = self._build_request("tools/list", {})
        response = self._send_request(request)

        # Handle error responses
        if "error" in response:
            raise RuntimeError(f"MCP server error listing tools: {response['error']}")

        tools = response.get("result", {}).get("tools", [])

        # Convert MCP tool format to Claude tool format
        return [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", {"type": "object"}),
            }
            for t in tools
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool and return the result."""
        self._check_process_alive()

        if not self._initialized:
            self.initialize()

        request = self._build_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )

        response = self._send_request(request)

        # Handle error responses
        if "error" in response:
            raise RuntimeError(f"MCP server error calling tool '{name}': {response['error']}")

        result = response.get("result", {})

        # Handle different result formats
        if "content" in result:
            return self._format_content(result["content"])
        return str(result)

    def stop(self) -> None:
        """Stop the MCP server process."""
        if self._stderr_thread:
            self._stderr_thread.join(timeout=2)
            self._stderr_thread = None
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None
            self._initialized = False
            logger.info(f"Stopped MCP server: {self.config.name}")

    def _build_request(self, method: str, params: dict) -> dict:
        self._request_id += 1
        return {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

    def _send_notification(self, method: str, params: dict) -> None:
        """Send a notification (one-way message) to the server."""
        if not self._process or not self._process.stdin:
            return  # Silently ignore if not running
        try:
            notification = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            self._process.stdin.write(json.dumps(notification) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            logger.warning(f"Failed to send notification to {self.config.name}: {e}")

    def _send_request(self, request: dict, timeout: float = 30.0) -> dict:
        """Send a request and wait for response with timeout."""
        self._check_process_alive()

        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError(f"MCP server '{self.config.name}' not started")

        try:
            # Write request
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
        except BrokenPipeError as e:
            self._check_process_alive()  # Will raise with details
            raise RuntimeError(f"Failed to write to MCP server '{self.config.name}': {e}") from e
        except OSError as e:
            self._check_process_alive()  # Will raise with details
            raise RuntimeError(f"OS error writing to MCP server '{self.config.name}': {e}") from e

        # Read response with timeout using select
        try:
            ready, _, _ = select.select([self._process.stdout], [], [], timeout)
            if not ready:
                raise TimeoutError(f"MCP server '{self.config.name}' timed out after {timeout}s")
            line = self._process.stdout.readline()
        except OSError as e:
            raise RuntimeError(f"Error reading from MCP server '{self.config.name}': {e}") from e
        except OSError as e:
            self._check_process_alive()
            raise RuntimeError(f"OS error reading from MCP server '{self.config.name}': {e}") from e

        if not line:
            self._check_process_alive()  # Will raise with details
            raise RuntimeError(f"MCP server '{self.config.name}' disconnected unexpectedly")

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON response from MCP server '{self.config.name}': {e}"
            ) from e

    def _format_content(self, content: list) -> str:
        """Format MCP content blocks to string."""
        parts = []
        for block in content:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "resource":
                parts.append(block.get("text", ""))
        return "\n".join(parts)


class MCPManager:
    """Manages multiple MCP server connections."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    def add_server(self, config: MCPServerConfig) -> None:
        """Add and start an MCP server."""
        client = MCPClient(config)
        client.start()
        # Eagerly initialize to catch startup failures early
        client.initialize()
        self._clients[config.name] = client

    def remove_server(self, name: str) -> None:
        """Stop and remove an MCP server."""
        if name in self._clients:
            self._clients[name].stop()
            del self._clients[name]

    def get_tools(self) -> list[dict]:
        """Get combined tool list from all MCP servers."""
        all_tools = []
        failed_servers = []
        for name, client in self._clients.items():
            try:
                server_tools = client.list_tools()
                # Prefix tool names with server name to avoid collisions
                for t in server_tools:
                    prefixed_name = f"mcp__{name}__{t['name']}"
                    t["name"] = prefixed_name
                all_tools.extend(server_tools)
            except Exception as e:
                failed_servers.append((name, str(e)))
                logger.warning(f"Failed to get tools from {name}: {e}")
        if failed_servers:
            for name, err in failed_servers:
                logger.error(f"MCP server '{name}' failed: {err}")
        return all_tools

    def call_tool(self, full_name: str, arguments: dict) -> str | None:
        """Call a tool, extracting server name from prefixed name."""
        if not full_name.startswith("mcp__"):
            return None

        # Parse name: mcp__{server}__{tool}
        parts = full_name.split("__", 2)
        if len(parts) < 3:
            return None

        _, server_name, tool_name = parts

        if server_name not in self._clients:
            return f"Unknown MCP server: {server_name}"

        try:
            return self._clients[server_name].call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"Error calling MCP tool {full_name}: {e}")
            return f"Error calling {full_name}: {str(e)}"

    def stop_all(self) -> None:
        """Stop all MCP servers."""
        for client in self._clients.values():
            client.stop()
        self._clients.clear()

    def get_server_names(self) -> list[str]:
        """Get list of active MCP server names."""
        return list(self._clients.keys())
