# Usage Guide

## Installation

```bash
# Basic installation
pip install -r requirements.txt

# With optional features
pip install -r requirements.txt
pip install python-telegram-bot  # For Telegram
pip install discord.py           # For Discord
```

## Configuration

### 1. Create config.json

```bash
python main.py init
```

This creates `config.json` from the example template.

### 2. Add API Keys

Edit `config.json` and add your API keys:

```json
{
  "providers": {
    "anthropic": {
      "api_key": "sk-ant-YOUR_KEY_HERE"
    }
  }
}
```

### 3. Enable Tools (Optional)

```json
{
  "tools": {
    "bash": {
      "enabled": true,
      "allowed_commands": ["ls", "cat", "grep", "echo"]
    },
    "search": {
      "enabled": true,
      "api_key": "YOUR_BRAVE_API_KEY"
    },
    "files": {
      "enabled": true,
      "workspace": "./workspace"
    }
  }
}
```

## Usage Modes

### Interactive Chat

Start an interactive conversation:

```bash
python main.py chat
```

Commands:
- Type your messages normally
- `reset` - Clear conversation history
- `exit` or `quit` - End session

### Single Query

Run a single query and exit:

```bash
python main.py query "What is the capital of France?"
python main.py query "List files in current directory"
```

### Gateway Mode (Coming Soon)

Start the gateway for Telegram/Discord:

```bash
python main.py gateway
```

## Tool Usage

### Bash Commands

The agent can execute bash commands when enabled:

```
You: List files in the current directory
Assistant: [Uses bash tool to run 'ls']
```

**Safety**: Configure `allowed_commands` to restrict what can be executed.

### Web Search

Search the web for current information:

```
You: What's the latest news about AI?
Assistant: [Uses search tool to find recent articles]
```

**Requirements**: Brave Search API key (free tier available)

### File Operations

Read, write, and manage files:

```
You: Create a file called hello.txt with "Hello World"
Assistant: [Uses files tool to create the file]

You: Read the contents of hello.txt
Assistant: [Uses files tool to read the file]
```

**Safety**: All operations are sandboxed to the workspace directory.

## Memory Management

The agent uses several strategies to minimize memory usage:

### 1. Conversation History Limits

```json
{
  "memory": {
    "max_history_messages": 50
  }
}
```

Keeps only the most recent 50 messages in memory.

### 2. Lazy Loading

Modules are imported only when needed, reducing startup memory.

### 3. Streaming Responses

LLM responses are streamed chunk-by-chunk instead of loading the entire response.

## Advanced Configuration

### Custom System Prompt

```json
{
  "agent": {
    "system_prompt": "You are a Python expert assistant. Focus on code quality and best practices."
  }
}
```

### Model Selection

```json
{
  "agent": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "temperature": 0.7
  }
}
```

### Tool Iterations

```json
{
  "agent": {
    "max_tool_iterations": 10
  }
}
```

Limits how many times the agent can call tools in a single conversation turn.

## Environment Variables

- `NUCLEO_CONFIG` - Path to config file (default: `./config.json`)

Example:
```bash
export NUCLEO_CONFIG=~/.nucleo/config.json
python main.py chat
```

## Troubleshooting

### "Config file not found"

```bash
python main.py init
```

### "API key not configured"

Edit `config.json` and add your API key under `providers.<provider>.api_key`

### "Tool not found"

Enable the tool in `config.json`:

```json
{
  "tools": {
    "bash": {"enabled": true}
  }
}
```

### High Memory Usage

1. Reduce `max_history_messages`
2. Disable unused tools
3. Use a smaller model

## Performance Tips

### Minimize Memory

```json
{
  "memory": {
    "max_history_messages": 20
  },
  "agent": {
    "max_tool_iterations": 5
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

### Cost Optimization

Use smaller models or OpenRouter for best pricing:

```json
{
  "agent": {
    "model": "claude-3-haiku-20240307"
  },
  "providers": {
    "openrouter": {
      "api_key": "sk-or-...",
      "api_base": "https://openrouter.ai/api/v1"
    }
  }
}
```

## Next Steps

- [ ] Add Telegram channel support
- [ ] Add Discord channel support
- [ ] Implement conversation persistence
- [ ] Add voice transcription
- [ ] Create web UI
