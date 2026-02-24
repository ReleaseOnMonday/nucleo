# Nucleo ♎

[![GitHub Stars](https://img.shields.io/github/stars/your-org/nucleo?style=flat-square)](https://github.com/your-org/nucleo)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Visitor Badge](https://visitor-badge.laobi.icu/badge?page_id=your-org.nucleo)](https://github.com/your-org/nucleo)

Ultra-lightweight AI assistant in Python with multi-channel support for Telegram, Discord, and more. Inspired by modern distributed AI architectures.

## ✨ Features

### Core
- 🪶 **Ultra-Lightweight**: <100MB memory footprint, no heavy frameworks
- ⚡ **Fast**: <3 seconds startup time
- 🔧 **Modular**: Extensible tool and channel architecture
- 💬 **Multi-Channel**: Deploy to Telegram, Discord, and more
- 🎯 **Smart**: Claude AI with tool orchestration

### Capabilities
- 📝 **Conversation Memory**: Persistent multi-turn chat history
- 🧠 **Tool Orchestration**: Execute tools (bash, files, search) with AI decision-making
- 🌐 **Web Search**: Real-time information retrieval
- 📁 **File Operations**: Read, write, and analyze files safely
- 🛡️ **Sandboxed Bash**: Execute shell commands with allowlist
- 🔄 **Streaming**: Real-time response streaming
- 👥 **Multi-User**: Handle concurrent users across channels
- 🎛️ **Fine-Grained Configuration**: Control every aspect via JSON config

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Create `config.json` from the example:

```bash
cp config.example.json config.json
```

Edit `config.json` and add your API keys:

```json
{
  "agent": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "temperature": 0.7,
    "system_prompt": "You are a helpful AI assistant. Be concise and practical."
  },
  "providers": {
    "anthropic": {
      "api_key": "sk-ant-..."
    }
  },
  "tools": {
    "bash": {
      "enabled": true,
      "allowed_commands": ["ls", "cat", "grep", "find", "echo"]
    },
    "search": {
      "enabled": false,
      "api_key": ""
    },
    "files": {
      "enabled": true,
      "workspace": "./workspace"
    }
  }
}
```

### 3. Run

**Interactive Chat**
```bash
python main.py chat
```

**Single Query**
```bash
python main.py query "What is 2+2?"
```

**Start Gateway** (Telegram/Discord)
```bash
python main.py gateway
```

See [GATEWAY.md](GATEWAY.md) for detailed channel setup and configuration.

---

## 🚀 Gateway - Multi-Channel AI Assistant

Deploy Nucleo across messaging platforms with a unified interface.

### Supported Channels

| Platform | Status | Access | Setup Time |
|----------|--------|--------|------------|
| **Telegram** | ✅ Ready | Long Polling | 5 min |
| **Discord** | ✅ Ready | WebSocket | 10 min |
| **Slack** | 🔄 Coming Soon | Socket Mode | - |
| **WhatsApp** | 🔄 Planned | Cloud API | - |

### Quick Gateway Setup

#### Telegram

1. Open Telegram → Search `@BotFather`
2. Send `/newbot` and follow prompts
3. Copy bot token to `config.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowed_users": []
    }
  }
}
```

4. Start: `python main.py gateway`

#### Discord

1. Go to https://discord.com/developers/applications
2. Create "New Application" → Go to "Bot" → "Add Bot"
3. Copy token to `config.json`:

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowed_users": []
    }
  }
}
```

4. Invite bot to server via OAuth2 URL Generator
5. Start: `python main.py gateway`

### Gateway Features

- 🔀 **Unified Interface**: Same Agent across all channels
- 👥 **Multi-User**: Handle concurrent users
- 🛡️ **Access Control**: Allowlist users by ID
- 📁 **File Support**: Upload/download files per channel
- 🎯 **Smart Routing**: Messages automatically route to correct channel
- 🔄 **Conversation History**: Per-user chat memory
- ⚡ **Streaming**: Real-time response delivery

### Advanced Gateway Usage

See [GATEWAY.md](GATEWAY.md) for:
- Detailed channel configuration
- Creating custom channels
- Production deployment tips
- Troubleshooting guide
- Performance optimization

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Telegram   │  │   Discord    │  │ (More Soon)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Message Bus (Pub/Sub)                           │
│  Decouples channels from agent, enables horizontal scaling  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Agent Core                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Chat Loop    │  │ Tool System  │  │ History Mgmt │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Tools & Services                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Bash Tool    │  │ Search Tool  │  │ Files Tool   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    LLM Layer                                 │
│  Anthropic Claude 3.5 Sonnet with Tool Use                  │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
nucleo/
├── agent.py                 # Core agent with tool orchestration
├── config.py               # Configuration management
├── llm.py                  # LLM client (Anthropic)
├── tools/
│   ├── base.py            # Tool interface
│   ├── bash.py            # Shell execution
│   ├── files.py           # File operations
│   └── search.py          # Web search
└── channels/
    ├── base.py            # Channel interface
    ├── manager.py         # Channel orchestration
    ├── bus.py             # Message bus
    ├── telegram.py        # Telegram integration
    ├── discord.py         # Discord integration
    └── message.py         # Message types
```

### Message Flow

```
User Message
    ↓
Channel listens & normalizes
    ↓
MessageBus.publish_inbound()
    ↓
Agent.chat() processes with tools
    ↓
LLM generates response (calling tools as needed)
    ↓
MessageBus.publish_outbound()
    ↓
ChannelManager routes to source channel
    ↓
Channel sends response to user
```

---

## 📦 Dependencies

**Core (required)**
- `anthropic` - LLM provider
- `httpx` - Async HTTP client

**Channels (optional)**
- `python-telegram-bot` - Telegram support
- `discord.py` - Discord support

**Tools (optional)**
- `brave-search` - Web search

**Development**
- `pytest` - Testing
- `ruff` - Linting

---

## 🔧 Extending Nucleo

### Creating Custom Tools

Extend `BaseTool`:

```python
from nucleo.tools import Tool

class MyTool(Tool):
    async def execute(self, **kwargs):
        # Your implementation
        return {"result": "data"}
    
    def to_anthropic_tool(self):
        return {
            "name": "my_tool",
            "description": "What it does",
            "input_schema": {...}
        }
```

### Creating Custom Channels

Extend `BaseChannel`:

```python
from nucleo.channels import BaseChannel

class MyChannel(BaseChannel):
    @property
    def name(self) -> str:
        return 'mychannel'
    
    async def start(self) -> None:
        self._running = True
        # Start listening
    
    async def stop(self) -> None:
        self._running = False
    
    async def send(self, message) -> None:
        # Send via your platform
        pass
```

See [GATEWAY.md](GATEWAY.md#advanced-usage) for detailed examples.

---

## ⚙️ Configuration

Nucleo uses JSON configuration. Key sections:

### Agent Settings
```json
{
  "agent": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "temperature": 0.7,
    "max_tool_iterations": 10,
    "system_prompt": "Your custom system prompt"
  }
}
```

### Tool Configuration
```json
{
  "tools": {
    "bash": {
      "enabled": true,
      "allowed_commands": ["ls", "grep", "find"],
      "max_output_length": 10000
    },
    "search": {
      "enabled": true,
      "api_key": "your-brave-search-key",
      "max_results": 5
    },
    "files": {
      "enabled": true,
      "workspace": "./workspace",
      "max_file_size_mb": 10
    }
  }
}
```

### Channel Configuration
```json
{
  "channels": {
    "telegram": {
      "enabled": false,
      "token": "",
      "allowed_users": []
    },
    "discord": {
      "enabled": false,
      "token": "",
      "allowed_users": []
    }
  }
}
```

See `config.example.json` for all available options.

---

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

## 📊 Performance Benchmarks

Nucleo is optimized for minimal resource usage:

| Metric | Value | Notes |
|--------|-------|-------|
| Memory (Idle) | ~50MB | Python base + imports |
| Memory (Active) | ~100MB | With one channel + agent |
| Startup Time | ~2-3s | Module loading only |
| Response Latency | ~1-5s | LLM generation + tool exec |
| Concurrent Users | Unlimited* | Rate-limited by LLM API |
| File Operations | Safe | Sandboxed to workspace dir |
| Tool Execution | Controlled | Allowlist-based command safety |

*Practically limited by Anthropic API rate limits (~25k tokens/min)

---

## 🖥️ System Requirements

- **Python**: 3.10+
- **Memory**: 256MB+ (512MB recommended for gateway mode)
- **Disk**: 200MB (mostly for dependencies)
- **Network**: Required
- **OS**: Linux, macOS, Windows (via WSL)

---

## 🚀 Deployment

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "gateway"]
```

### Docker Compose

```yaml
services:
  nucleo:
    build: .
    environment:
      - NUCLEO_CONFIG=/etc/nucleo/config.json
    volumes:
      - ./config.json:/etc/nucleo/config.json
      - ./workspace:/app/workspace
    restart: unless-stopped
```

### Command Line

```bash
# Set config path
export NUCLEO_CONFIG=/etc/nucleo/config.json

# Start gateway
python main.py gateway

# Enable debug logging
export DEBUG=1 python main.py gateway
```

---

## 📚 Examples

### Simple Chat Loop

```python
from nucleo import Agent, Config

config = Config().load()
agent = Agent(config)

while True:
    user_input = input("You: ")
    response = ""
    async for chunk in agent.chat(user_input, stream=True):
        response += chunk
    print("Agent:", response)
```

### Using Tools

```python
# Agent automatically uses tools when appropriate
async for chunk in agent.chat(
    "List files in /tmp and search for 'nucleo'",
    stream=True
):
    print(chunk, end="", flush=True)
```

### Gateway with Multiple Channels

```python
from nucleo.channels import ChannelManager, TelegramChannel, DiscordChannel

manager = ChannelManager(config)
manager.register_channel(TelegramChannel(config, bus))
manager.register_channel(DiscordChannel(config, bus))
await manager.start()
```

See [GATEWAY.md](GATEWAY.md) for more advanced examples.

---

## 🛠️ Development

### Setup Dev Environment

```bash
# Install with dev dependencies
pip install -r requirements.txt pytest ruff

# Format code
ruff format nucleo/

# Lint
ruff check nucleo/

# Run tests
pytest test_nucleo.py -v
```

### Contributing

We welcome contributions! Areas to enhance:

- **New Channels**: Slack, WhatsApp, Matrix, IRC
- **New Tools**: Calculator, SQL, APIs
- **Features**: Voice support, rich formatting, reactions
- **Performance**: Response caching, optimizations
- **Docs**: Examples, tutorials, API docs

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines (coming soon).

---
