"""Configuration loader for CLI settings."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = ".code_cli"
CONFIG_FILE = "config.json"


def get_config_path() -> Path:
    """Get config path in project root (current working directory)."""
    return Path(os.getcwd()) / CONFIG_DIR / CONFIG_FILE


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from JSON file in project root.

    Default location: ./.code_cli/config.json (relative to where CLI is run)

    Example config:
    {
        "mcp_servers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
            }
        }
    }
    """
    path = config_path or get_config_path()

    if not path.exists():
        logger.debug(f"Config not found at {path}, using defaults")
        return {}

    try:
        with open(path) as f:
            config = json.load(f)
            logger.info(f"Loaded config from {path}")
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config {path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load config {path}: {e}")
        return {}


def get_mcp_servers(config: dict[str, Any] | None = None) -> dict[str, dict]:
    """Get MCP server configurations from config."""
    if config is None:
        config = load_config()
    return config.get("mcp_servers", {})


def get_pre_commit_commands(config: dict[str, Any] | None = None) -> list[str]:
    """Get pre-commit commands (lint, format, etc.) from config."""
    if config is None:
        config = load_config()
    return config.get("pre_commit", [])


def ensure_config_dir() -> Path:
    """Ensure the config directory exists in project root."""
    config_dir = Path(os.getcwd()) / CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def save_config(updates: dict[str, Any], config_path: Path | None = None) -> None:
    """Merge updates into the config file and save."""
    path = config_path or get_config_path()
    ensure_config_dir()
    config = load_config(path)
    config.update(updates)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved config to {path}")
