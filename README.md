# Nucleo ♎

Ultra-lightweight AI assistant in Python, inspired by [PicoClaw](https://github.com/sipeed/picoclaw)

## Features

- ✨ **Minimal Dependencies**: Core functionality with <5 packages
- 🪶 **Low Memory**: <100MB RAM usage (vs 1GB+ for full frameworks)
- ⚡ **Fast Startup**: <3 seconds boot time
- 🔧 **Modular Design**: Easy to extend with tools
- 💬 **Multi-Channel**: Telegram, Discord support
- 🛠️ **Tool System**: Bash execution, web search, file operations

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

Create `config.json`:

```json
{
  "agent": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "providers": {
    "anthropic": {
      "api_key": "sk-ant-..."
    }
  }
}
```

### 3. Run

```bash
# Interactive chat
python main.py chat

# Single query
python main.py query "What is 2+2?"

# Start gateway (for Telegram/Discord)
python main.py gateway
```

## Architecture

```
nucleo/
├── agent.py          # Core agent loop
├── config.py         # Configuration
├── llm.py            # LLM client
├── tools/            # Tool system
└── channels/         # Integrations
```

## Memory Optimization

- Lazy imports
- Streaming responses
- Minimal state management
- No heavy frameworks

## License

MIT License
