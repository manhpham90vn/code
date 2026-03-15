"""Model command - switch between Claude models."""

from __future__ import annotations

from rich.console import Console

from ..config import save_config
from ..models import Model
from .base import Command


class ModelCommand(Command):
    names = ["/model", "/m"]
    description = "Show or switch Claude model"

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
        if not args:
            # Show current model
            console.print(f"[bold]Current model:[/bold] {client.model}")
            console.print("\n[bold]Available models:[/bold]")
            for m in Model:
                marker = " ✓" if m.value == client.model else ""
                console.print(f"  {m.value:20s} - {m.description}{marker}")
            return True

        # Switch model
        model_id = args.strip().lower()
        try:
            Model(model_id)
        except ValueError:
            console.print(f"[error]Unknown model: {model_id}[/error]")
            console.print("Available models:")
            for m in Model:
                console.print(f"  {m.value}")
            return True

        client.model = model_id
        console.print(f"[success]Switched to {model_id}[/success]")

        # Ask if user wants to persist this choice
        try:
            answer = console.input("  Save as default? (y)es / (a)lways / (n)o: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return True

        if answer in ("y", "yes", "a", "always"):
            save_config({"model": model_id})
            console.print("  [dim]Saved to .code_cli/config.json[/dim]")

        return True
