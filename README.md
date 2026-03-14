# AI CLI

AI Coding Assistant CLI powered by Claude API.

## Cài đặt

```bash
pip install -e .
```

## Cấu hình

```bash
# Cách 1: Sử dụng API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Cách 2: Sử dụng base_url + auth_token (proxy)
export ANTHROPIC_BASE_URL="https://your-proxy.com"
export ANTHROPIC_AUTH_TOKEN="your-token"
```

## Chạy

```bash
ai-cli
# hoặc
python -m ai_cli.main
```

## Commands

- `/help` - Hiển thị help
- `/clear` - Xóa conversation history
- `/quit` - Thoát
