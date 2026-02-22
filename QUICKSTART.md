# Quick Start Guide

Get Nucleo running in 5 minutes! ♎

## Prerequisites

- Python 3.9 or higher
- pip package manager
- An Anthropic API key (get one at https://console.anthropic.com)

## Installation

### Step 1: Clone or Download

```bash
# Option A: Clone from git
git clone https://github.com/ReleaseOnMonday/nucleo.git
cd nucleo

# Option B: Download and extract
wget https://github.com/ReleaseOnMonday/nucleo/archive/main.zip
unzip main.zip
cd nucleo-main
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `httpx` - HTTP client
- `anthropic` - Claude API client

### Step 3: Create Configuration

```bash
python main.py init
```

This creates `config.json` from the example template.

### Step 4: Add Your API Key

Edit `config.json` and add your Anthropic API key:

```json
{
  "providers": {
    "anthropic": {
      "api_key": "sk-ant-YOUR_KEY_HERE"
    }
  }
}
```

**Where to get API keys:**
- Anthropic (Claude): https://console.anthropic.com
- Brave Search (optional): https://brave.com/search/api

## First Chat

Start an interactive conversation:

```bash
python main.py chat
```

Try these examples:

```
You: What is 2+2?
You: Write a Python function to calculate fibonacci numbers
You: Explain how async/await works in Python
```

Type `exit` or `quit` to end the session.

## Single Query Mode

For quick one-off questions:

```bash
python main.py query "What is the capital of France?"
```

## Enable Tools

### Bash Commands

Edit `config.json`:

```json
{
  "tools": {
    "bash": {
      "enabled": true,
      "allowed_commands": ["ls", "cat", "pwd", "echo", "date"]
    }
  }
}
```

Now try:

```
You: List files in the current directory
You: Show me the current date and time
```

### Web Search

1. Get a free Brave Search API key: https://brave.com/search/api
2. Edit `config.json`:

```json
{
  "tools": {
    "search": {
      "enabled": true,
      "api_key": "BSA_YOUR_KEY_HERE"
    }
  }
}
```

Now try:

```
You: What's the latest news about AI?
You: Search for Python best practices
```

### File Operations

Edit `config.json`:

```json
{
  "tools": {
    "files": {
      "enabled": true,
      "workspace": "./workspace"
    }
  }
}
```

Now try:

```
You: Create a file called hello.txt with the content "Hello World"
You: Read the file hello.txt
You: List all files in the workspace
```

## Configuration Tips

### Use a Smaller Model (Lower Cost)

```json
{
  "agent": {
    "model": "claude-3-haiku-20240307"
  }
}
```

### Reduce Memory Usage

```json
{
  "memory": {
    "max_history_messages": 20
  }
}
```

### Faster Responses

```json
{
  "agent": {
    "temperature": 0.3,
    "max_tokens": 2048
  }
}
```

## Troubleshooting

### "Config file not found"

```bash
python main.py init
```

### "API key not configured"

Make sure you've edited `config.json` and added your API key.

### "Command not allowed"

Add the command to the `allowed_commands` list in `config.json`.

### Import Error

```bash
pip install -r requirements.txt
```

## Next Steps

- Read [USAGE.md](USAGE.md) for detailed usage instructions
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the design
- Enable Telegram/Discord channels (coming soon)
- Customize the system prompt
- Add your own tools

## Getting Help

- Check the documentation in the repo
- Open an issue on GitHub
- Read the code - it's intentionally simple and well-commented!

## Memory Usage

Expected memory usage:
- Idle: ~30MB
- During chat: ~50MB
- With all tools: ~80MB
- Peak: ~100MB

Much lower than alternatives! 🎉

## Performance

Typical response times:
- Configuration load: <10ms
- LLM response: 500-5000ms (depends on provider)
- Tool execution: 10-1000ms (depends on tool)

## What's Different from Go Version?

| Feature | Go | Python | Winner |
|---------|----|----|--------|
| Memory | <10MB | ~50MB | Go |
| Startup | <1s | ~2s | Go |
| Development | Medium | Fast | Python |
| Ecosystem | Good | Excellent | Python |

Python version is 5x more memory but much easier to develop with!

## Contributing

Want to help? Great! Check out:
- [ ] Add Telegram channel
- [ ] Add Discord channel
- [ ] Implement conversation persistence
- [ ] Add more tools
- [ ] Improve documentation

Happy hacking! ♎
