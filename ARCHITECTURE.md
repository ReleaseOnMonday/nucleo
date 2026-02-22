# Architecture Overview

## Design Goals

1. **Minimal Memory Footprint**: <100MB RAM usage
2. **Fast Startup**: <3 seconds boot time
3. **Lightweight Dependencies**: Core functionality with minimal packages
4. **Modular Design**: Easy to extend and customize
5. **Production Ready**: Robust error handling and logging

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Layer                          │
│  - Interactive chat                                     │
│  - Single query mode                                    │
│  - Gateway mode (Telegram/Discord)                      │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                    Agent Core                           │
│  - Conversation management                              │
│  - Tool orchestration                                   │
│  - History trimming                                     │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼────┐   ┌───▼────┐   ┌───▼────┐
│  LLM   │   │ Tools  │   │Channels│
│ Client │   │ System │   │        │
└────────┘   └────────┘   └────────┘
    │             │             │
    │         ┌───┴───┐     ┌───┴───┐
    │         │ Bash  │     │Telegram│
    │         ├───────┤     ├───────┤
    │         │Search │     │Discord│
    │         ├───────┤     └───────┘
    │         │ Files │
    │         └───────┘
    │
┌───▼────────────────────────┐
│   Anthropic/OpenAI/etc     │
│      (API Endpoints)       │
└────────────────────────────┘
```

## Core Components

### 1. Config System (`config.py`)

**Purpose**: Centralized configuration management

**Features**:
- Singleton pattern for memory efficiency
- Lazy loading of configuration
- Dot notation access (`config.get('agent.model')`)
- Environment variable support

**Memory Impact**: ~1KB

```python
config = Config().load()
model = config.get('agent.model', 'claude-3-5-sonnet')
```

### 2. LLM Client (`llm.py`)

**Purpose**: Unified interface to multiple LLM providers

**Features**:
- Streaming response support
- Lazy client initialization
- Provider auto-detection
- Tool use support

**Memory Impact**: ~5MB (loaded on first use)

**Optimization**: Client objects are created only when needed:

```python
# Lazy import - only loads when actually used
_anthropic_client = None

def get_anthropic_client(api_key: str):
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client
```

### 3. Tool System (`tools/`)

**Purpose**: Extensible tool framework for agent capabilities

**Components**:
- `base.py` - Abstract tool interface
- `bash.py` - Command execution
- `search.py` - Web search
- `files.py` - File operations

**Memory Impact**: ~2MB per tool (loaded on demand)

**Design Pattern**: Each tool inherits from `Tool` base class:

```python
class Tool(ABC):
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        # Convert to Anthropic tool format
        pass
```

### 4. Agent Core (`agent.py`)

**Purpose**: Main agent loop with tool orchestration

**Features**:
- Conversation history management
- Tool execution and result handling
- Multi-turn tool use support
- Memory-efficient history trimming

**Memory Impact**: ~10MB + conversation history

**Key Algorithms**:

1. **Tool Execution Loop**:
```python
for iteration in range(max_iterations):
    # 1. LLM generates response with potential tool calls
    # 2. Execute all tool calls in parallel
    # 3. Feed results back to LLM
    # 4. Repeat until no more tool calls
```

2. **History Management**:
```python
def _trim_history(self):
    max_messages = 50  # Configurable
    if len(self.history) > max_messages:
        self.history = self.history[-max_messages:]
```

### 5. CLI Interface (`main.py`)

**Purpose**: Command-line entry point

**Modes**:
- `chat` - Interactive conversation
- `query` - Single query
- `gateway` - Multi-channel server
- `init` - Setup configuration

**Memory Impact**: Minimal (~2MB)

## Memory Optimization Strategies

### 1. Lazy Loading

Modules are imported only when needed:

```python
# Bad: Always loads
from anthropic import Anthropic
client = Anthropic()

# Good: Load on first use
_client = None
def get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic()
    return _client
```

**Savings**: ~50-100MB for unused modules

### 2. Streaming Responses

Process LLM output incrementally:

```python
async for chunk in llm.chat_stream(messages):
    yield chunk  # Process immediately, don't accumulate
```

**Savings**: ~10-50MB depending on response size

### 3. History Trimming

Limit conversation history:

```python
max_history = 50  # Keep only recent messages
self.history = self.history[-max_history:]
```

**Savings**: ~1KB per message trimmed

### 4. Tool Result Streaming

Stream tool output instead of buffering:

```python
process = await asyncio.create_subprocess_shell(
    command,
    stdout=asyncio.subprocess.PIPE
)
# Stream output line by line
async for line in process.stdout:
    yield line
```

**Savings**: ~1-100MB depending on tool output

### 5. Singleton Pattern

Share configuration across components:

```python
class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**Savings**: ~1KB per duplicate avoided

## Performance Characteristics

### Startup Time

| Phase | Time | Memory |
|-------|------|--------|
| Python interpreter | 0.5s | 15MB |
| Import core modules | 0.5s | 10MB |
| Load configuration | 0.1s | 1MB |
| Initialize agent | 0.5s | 5MB |
| **Total** | **~2s** | **~31MB** |

### Runtime Memory

| Component | Memory | Notes |
|-----------|--------|-------|
| Python interpreter | 15MB | Base overhead |
| Core modules | 10MB | config, agent, llm |
| LLM client (Anthropic) | 5MB | Lazy loaded |
| Tools (all) | 6MB | Bash, search, files |
| Conversation history | 1-10MB | Grows with usage |
| **Total** | **40-50MB** | Typical usage |
| **Peak** | **80-100MB** | Large responses |

### Response Latency

| Operation | Latency | Notes |
|-----------|---------|-------|
| Configuration load | <10ms | Cached after first load |
| Tool execution (bash) | 10-1000ms | Depends on command |
| Tool execution (search) | 200-1000ms | Network dependent |
| LLM API call | 500-5000ms | Provider dependent |
| **Total (typical)** | **1-6s** | End-to-end query |

## Comparison with Go Version

| Metric | PicoClaw (Go) | Nucleo | Ratio |
|--------|---------------|-----------------|-------|
| **RAM Usage** | <10MB | ~50MB | 5x |
| **Boot Time** | <1s | ~2s | 2x |
| **Binary Size** | 20MB | N/A | - |
| **Dependencies** | Static | Runtime | - |
| **Development Speed** | Medium | Fast | - |
| **Ecosystem** | Go packages | PyPI | - |

### Trade-offs

**Go Advantages**:
- Lower memory footprint (5x)
- Faster startup (2x)
- Single binary deployment
- Better for embedded devices

**Python Advantages**:
- Faster development
- Richer AI/ML ecosystem
- More familiar to data scientists
- Better debugging tools
- Dynamic typing flexibility

## Future Optimizations

### 1. Reduce Python Overhead

Use PyPy for ~2x memory reduction:
```bash
pypy3 main.py chat
```

### 2. Implement Caching

Cache LLM responses for repeated queries:
```python
@lru_cache(maxsize=100)
async def cached_llm_call(prompt: str):
    return await llm.chat(prompt)
```

### 3. Optimize Tool Loading

Load tools on-demand instead of at initialization:
```python
def get_tool(name: str) -> Tool:
    if name not in _loaded_tools:
        _loaded_tools[name] = _load_tool(name)
    return _loaded_tools[name]
```

### 4. Compress History

Use zlib compression for old messages:
```python
import zlib
compressed = zlib.compress(json.dumps(old_messages).encode())
```

### 5. Use C Extensions

Replace slow Python code with Cython:
```python
# tools/bash.pyx (Cython)
cdef extern from "unistd.h":
    int execv(const char *path, char *const argv[])
```

## Extending the System

### Adding a New Tool

1. Create `nucleo/tools/mytool.py`:

```python
from .base import Tool

class MyTool(Tool):
    name = "mytool"
    description = "Does something useful"
    parameters = {
        'param1': {
            'type': 'string',
            'description': 'First parameter',
            'required': True
        }
    }
    
    async def execute(self, param1: str, **kwargs):
        # Implementation
        return {'result': 'success'}
```

2. Register in `agent.py`:

```python
def _init_tools(self):
    # ... existing tools ...
    if tools_config.get('mytool', {}).get('enabled'):
        self.tools['mytool'] = MyTool(tools_config.get('mytool'))
```

3. Configure in `config.json`:

```json
{
  "tools": {
    "mytool": {
      "enabled": true,
      "option1": "value1"
    }
  }
}
```

### Adding a New Channel

1. Create `nucleo/channels/mychannel.py`:

```python
class MyChannel:
    async def start(self):
        # Setup channel
        pass
    
    async def send_message(self, text: str):
        # Send message
        pass
    
    async def on_message(self, message):
        # Handle incoming message
        pass
```

2. Integrate with gateway in `main.py`

## Security Considerations

### 1. Tool Sandboxing

- Bash: Restrict allowed commands
- Files: Sandbox to workspace directory
- Search: Rate limit API calls

### 2. Input Validation

- Sanitize user input
- Validate tool parameters
- Check file paths

### 3. API Key Protection

- Never log API keys
- Use environment variables
- Restrict config file permissions

### 4. Resource Limits

- Timeout for tool execution
- Max file sizes
- History size limits

## Conclusion

Nucleo achieves a good balance between:
- Memory efficiency (~50MB vs 1GB+ for alternatives)
- Development speed (Python ecosystem)
- Feature completeness (tools, channels, etc.)
- Maintainability (clean architecture)

While not as efficient as the Go version, it's significantly lighter than alternatives like OpenClaw while maintaining comparable functionality.
