"""Commit command — stage all changes and generate a commit message via AI."""

from __future__ import annotations

import subprocess

from rich.console import Console
from rich.markup import escape

from code_cli.config import get_pre_commit_commands

from .base import Command


def run_pre_commit_checks(console: Console) -> tuple[bool, str]:
    """Run pre-commit commands (lint, format, etc.).

    Return (passed, output) — output contains error details on failure.
    """
    commands = get_pre_commit_commands()
    if not commands:
        return True, ""

    for cmd in commands:
        console.print(f"[dim]▶ {cmd}[/dim]")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[error]✗ Failed: {cmd}[/error]")
            output_parts = [f"Command failed: {cmd}"]
            if result.stdout.strip():
                console.print(f"[dim]{escape(result.stdout.strip())}[/dim]")
                output_parts.append(result.stdout.strip())
            if result.stderr.strip():
                console.print(f"[error]{escape(result.stderr.strip())}[/error]")
                output_parts.append(result.stderr.strip())
            return False, "\n".join(output_parts)
        console.print(f"[success]✓ {cmd}[/success]")

    return True, ""


def get_staged_diff() -> str:
    """Stage all changes and return the diff for AI to review."""
    try:
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to stage changes: {e.stderr}") from e
    except FileNotFoundError as exc:
        raise RuntimeError("git is not installed or not in PATH") from exc

    status = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        check=True,
        capture_output=True,
        text=True,
    )
    if not status.stdout.strip():
        return ""

    stat = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        check=True,
        capture_output=True,
        text=True,
    )
    diff = subprocess.run(
        ["git", "diff", "--cached"],
        check=True,
        capture_output=True,
        text=True,
    )

    diff_text = diff.stdout
    max_len = 8000
    if len(diff_text) > max_len:
        diff_text = diff_text[:max_len] + "\n... (truncated)"

    return f"Staged files:\n{status.stdout}\nStats:\n{stat.stdout}\nDiff:\n{diff_text}"


class CommitCommand(Command):
    names = ["/commit"]
    description = "AI-generated commit message"

    def execute(
        self,
        args: str,
        *,
        client,
        context,
        console: Console,
        stream_fn=None,
        log_usage_fn=None,
    ) -> bool:
        try:
            # Run lint/format checks first
            passed, error_output = run_pre_commit_checks(console)
            if not passed:
                console.print("[error]Pre-commit checks failed. Commit aborted.[/error]")
                # Store error output in context for "fix đi" to reference
                context.last_output = error_output
                return True

            diff = get_staged_diff()
            if not diff:
                console.print("[warning]No changes to commit.[/warning]")
                return True

            console.print(f"[dim]{diff.split(chr(10))[0]}[/dim]")

            # Ask AI to generate commit message (no tools)
            user_input = (
                "Here is the git diff of staged changes:\n\n"
                f"{diff}\n\n"
                "Generate a single-line commit message in "
                "Conventional Commits format "
                "(e.g. feat(scope): ..., fix: ..., refactor: ...). "
                "Reply with ONLY the commit message, nothing else."
            )
            context.add_user_message(user_input)
            response = stream_fn(client, context, [])
            if log_usage_fn:
                log_usage_fn(response)

            # Extract commit message
            commit_msg = ""
            for block in response.content:
                if hasattr(block, "text"):
                    commit_msg = block.text.strip()
                    break

            if not commit_msg:
                console.print("[error]Failed to generate commit message.[/error]")
                return True

            context.add_assistant_message([c.model_dump() for c in response.content])

            # Execute git commit
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                short_hash = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                console.print(f"[success]✅ {short_hash} {commit_msg}[/success]")
            else:
                console.print(f"[error]{escape(result.stderr)}[/error]")

        except Exception as e:
            console.print(f"[error]Commit failed: {escape(str(e))}[/error]")

        return True
