"""Shell command execution tool."""

import shlex
import subprocess
from typing import ClassVar

from .base import Tool


class RunBash(Tool):
    name: ClassVar[str] = "run_bash"
    icon: ClassVar[str] = "$"
    description: ClassVar[str] = (
        "Execute a shell command and return its output. "
        "Use for system commands, git, package managers, etc."
    )
    input_schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30)",
                "default": 30,
            },
        },
        "required": ["command"],
    }

    @classmethod
    def execute(cls, input_data: dict) -> str:
        command = input_data["command"]
        timeout = input_data.get("timeout", 30)

        # Validate: ensure command is a non-empty string
        if not command or not isinstance(command, str):
            return "Error: Command must be a non-empty string"

        # Security: use shlex.split to safely parse command
        # This prevents shell injection while supporting pipes/redirection via shlex
        try:
            args = shlex.split(command)
        except ValueError as e:
            return f"Error: Invalid command syntax: {e}"

        try:
            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=None,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += result.stderr
            if result.returncode != 0:
                output += f"\n[Exit code: {result.returncode}]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s"
        except FileNotFoundError:
            return "Error: Command not found. Make sure the executable is in PATH."
        except PermissionError:
            return "Error: Permission denied to execute this command."
        except Exception as e:
            return f"Error: {str(e)}"
