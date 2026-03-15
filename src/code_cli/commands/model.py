"""Model command - switch between Claude models."""

from __future__ import annotations

from rich.console import Console

from ..config import save_config
from .base import Command

AVAILABLE_MODELS = {
    "claude-opus-4-6": "Claude Opus 4.6 (most capable)",
    "claude-sonnet-4-6": "Claude Sonnet 4.6 (balanced)",
}


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
            for model_id, desc in AVAILABLE_MODELS.items():
                marker = " ✓" if model_id == client.model else ""
                console.print(f"  {model_id:20s} - {desc}{marker}")
            return True

        # Switch model
        model_id = args.strip().lower()
        if model_id not in AVAILABLE_MODELS:
            console.print(f"[error]Unknown model: {model_id}[/error]")
            console.print("Available models:")
            for mid in AVAILABLE_MODELS:
                console.print(f"  {mid}")
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
