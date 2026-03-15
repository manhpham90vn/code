# Code CLI

> AI Coding Assistant CLI powered by Claude API

Code CLI is a powerful command-line tool that lets you interact directly with Claude (Anthropic) to assist with coding. With built-in tools, you can read/write files, run shell commands, search the web, and more — all from your terminal.

## Features

- 🤖 **Claude API Interaction** — Chat with Claude directly in your terminal
- 📁 **File Operations** — Read, write, and edit files effortlessly
- 🔧 **Shell Commands** — Execute commands directly
- 🔍 **Web Search & Fetch** — Search the web and fetch URL content
- 💾 **Conversation History** — Automatically saved, resume anytime
- 🔐 **Permission System** — Confirm before running dangerous commands
- 🌐 **Proxy Support** — Custom base_url and auth_token support
- 💰 **Token Cost Tracking** — Real-time cost display
- 🔌 **MCP Server** — Extend functionality with Model Context Protocol

## Installation

```bash
# Clone repository
git clone <repo-url>
cd code-cli

# Install package
pip install -e .
```

## Configuration

Copy the example config file and fill in your credentials:

```bash
cp .env.example .env
```

Edit the `.env` file:

```bash
# Option 1: Direct API Key
ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Proxy
ANTHROPIC_BASE_URL=https://your-proxy.com
ANTHROPIC_AUTH_TOKEN=your-token
```

### Advanced Configuration (Optional)

Create `.code_cli/config.json` for additional settings:

```json
{
    "model": "claude-sonnet-4-6",
    "mcp_servers": {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {}
        }
    }
}
```

## Usage

```bash
# Run CLI
code

# Or run directly with Python
python -m code_cli.main
```

### Available Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear conversation history |
| `/quit` / `/exit` | Exit the program |

### Built-in Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write content to file |
| `edit_file` | Edit file contents |
| `bash` | Run shell commands |
| `grep` | Search file contents |
| `glob` | Find files by pattern |
| `web_search` | Search the web |
| `web_fetch` | Fetch URL content |

### Usage Examples

```
❯ Read the main.py file in the current directory

❯ Find all .py files in the project

❯ Create a new README.md file

❯ Run pip list to see installed packages

❯ Search how to use Git on the web
```

## Token & Cost

The CLI displays token information after each response:

- **Input/Output tokens** — Token count for input/output
- **Cache tokens** — Cache tokens (if any)
- **Estimated cost** — Estimated cost in USD
- **Session total** — Total cost for the session

### Reference Pricing (USD/1M tokens)

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| Claude Opus 4-6 | $5.00 | $25.00 | $6.25 | $0.50 |
| Claude Sonnet 4-6 | $3.00 | $15.00 | $3.75 | $0.30 |

## Development

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

Format and lint with [Ruff](https://docs.astral.sh/ruff/):

```bash
# Format code
ruff format .

# Lint
ruff check .

# Auto-fix
ruff check --fix .
```

## Project Structure

```
code_cli/
├── src/code_cli/
│   ├── client.py      # Claude API client
│   ├── commands/     # CLI commands
│   ├── config.py     # Configuration management
│   ├── context.py    # Context/conversation management
│   ├── main.py       # Entry point
│   ├── mcp/          # MCP server integration
│   ├── permissions.py # Permission system
│   ├── registry.py   # Tool registry
│   └── tools/        # Built-in tools
├── .env.example      # Example config file
└── pyproject.toml   # Project configuration
```

## License

MIT License
