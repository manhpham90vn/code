"""Shell command execution tool."""

import subprocess

from .base import Tool


class RunBash(Tool):
    name = "run_bash"
    description = (
        "Execute a shell command and return its output. "
        "Use for system commands, git, package managers, etc."
    )
    input_schema = {
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

        try:
            result = subprocess.run(
                command,
                shell=True,
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
        except Exception as e:
            return f"Error: {str(e)}"


def get_tool_definition():
    return RunBash.get_tool_definition()


def execute(input_data: dict) -> str:
    return RunBash.execute(input_data)
