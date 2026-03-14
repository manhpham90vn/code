# Code CLI

AI Coding Assistant CLI powered by Claude API.

## Features

- Interact with Claude API via CLI
- Use tools to read, write, and edit files
- Run shell commands directly
- Web search and URL content fetching
- Conversation history saved automatically
- Proxy support with custom base_url + auth_token
- Automatic token cost calculation

## Installation

```bash
# Clone repo and install
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```bash
# Option 1: Direct API Key
ANTHROPIC_API_KEY=sk-ant-...

# Option 2: Proxy (base_url + auth_token)
ANTHROPIC_BASE_URL=https://your-proxy.com
ANTHROPIC_AUTH_TOKEN=your-token
```

## Usage

```bash
# Run CLI
code

# Or run directly with Python
python -m code_cli.main
```

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear conversation history |
| `/quit` | Exit |

## Tools

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

## Token Usage

The CLI displays token information after each response:
- Input/output token count
- Cache tokens (if any)
- Estimated cost (USD)
- HTTP status code

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

# Lint and auto-fix
ruff check --fix .
```

## License

MIT License
