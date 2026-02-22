# Complete Ollama Setup Guide - FREE Local AI

## 🎯 What You Get

- ✅ **100% Free** - No API costs ever
- ✅ **No Login Required** - Run locally
- ✅ **Unlimited Usage** - No rate limits
- ✅ **Privacy** - All data stays on your machine
- ✅ **Works Offline** - No internet needed (after setup)

## 📋 Prerequisites

- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 5-10GB free space for models
- **OS**: Linux (your Docker Ubuntu) or Windows/Mac

## 🚀 Step-by-Step Installation

### Step 1: Install Ollama

**On Docker Ubuntu (your setup):**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

**On Windows (alternative):**
- Download: https://ollama.com/download/windows
- Run installer
- Done! Ollama starts automatically

### Step 2: Start Ollama Server

```bash
# Start server (keep this running in one terminal)
ollama serve

# You should see:
# Ollama is running
```

**Note**: Keep this terminal open. Open a new terminal for next steps.

### Step 3: Download a Model

**Recommended models (choose ONE to start):**

```bash
# OPTION 1: Fast & Small (RECOMMENDED TO START)
ollama pull llama3.2
# Size: 2GB, Speed: Fast, Quality: Good

# OPTION 2: Better Quality
ollama pull llama3.1:8b
# Size: 4.7GB, Speed: Medium, Quality: Better

# OPTION 3: Best Quality
ollama pull llama3.1:70b
# Size: 40GB, Speed: Slow, Quality: Best (needs 64GB RAM!)

# OPTION 4: Code-Focused
ollama pull codellama
# Size: 3.8GB, Speed: Medium, Quality: Good for coding

# OPTION 5: Multilingual
ollama pull qwen2.5
# Size: 4.4GB, Speed: Medium, Quality: Good for non-English
```

**Download time**: 2-10 minutes depending on your internet speed.

### Step 4: Test Ollama

```bash
# Quick test
ollama run llama3.2

# Type: Hello!
# Should respond with AI message
# Type: /bye to exit
```

If this works, you're ready! 🎉

### Step 5: Configure Nucleo for Ollama

**Replace the `llm.py` file:**
1. Download the new `llm.py` from the `ollama-version` folder I created
2. Replace `nucleo/llm.py` with it

**Create `config.json`:**
```json
{
  "agent": {
    "model": "llama3.2",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "providers": {
    "ollama": {
      "enabled": true,
      "base_url": "http://localhost:11434"
    }
  },
  "tools": {
    "bash": {
      "enabled": true,
      "allowed_commands": ["ls", "cat", "pwd", "echo", "date"]
    },
    "files": {
      "enabled": true,
      "workspace": "./workspace"
    }
  }
}
```

### Step 6: Install Python Dependencies

```bash
# Only need httpx for Ollama (no anthropic needed!)
pip install httpx
```

### Step 7: Run Nucleo!

```bash
# Make sure Ollama is running in another terminal:
# ollama serve

# Then run Nucleo:
python main.py chat
```

## 🎮 Usage Examples

```bash
# Interactive chat
python main.py chat

You: What is 2+2?
Assistant: 4

You: List files in current directory
Assistant: [Uses bash tool to run 'ls']

You: exit
```

```bash
# Single query
python main.py query "Explain what Python is"
```

## 🔧 Troubleshooting

### Problem: "Cannot connect to Ollama"

**Solution**:
```bash
# Make sure Ollama is running:
ollama serve

# Check it's accessible:
curl http://localhost:11434
# Should return: "Ollama is running"
```

### Problem: "Model not found"

**Solution**:
```bash
# Download the model first:
ollama pull llama3.2

# List available models:
ollama list
```

### Problem: Slow responses

**Solutions**:
1. **Use smaller model**: `llama3.2` instead of `llama3.1:70b`
2. **Reduce max_tokens** in config: `"max_tokens": 2048`
3. **Check CPU usage**: Ollama uses CPU/RAM, not GPU (unless you have one)

### Problem: Out of memory

**Solutions**:
1. **Use smaller model**: `llama3.2` (2GB) or `phi3` (2.3GB)
2. **Close other applications**
3. **Increase Docker memory limit** if running in Docker

## 📊 Model Comparison

| Model | Size | RAM Needed | Speed | Quality | Best For |
|-------|------|------------|-------|---------|----------|
| llama3.2 | 2GB | 8GB | Fast | Good | General chat, quick tasks |
| llama3.1:8b | 4.7GB | 12GB | Medium | Better | Complex tasks, coding |
| llama3.1:70b | 40GB | 64GB | Slow | Best | Production, critical tasks |
| mistral | 4.1GB | 12GB | Medium | Excellent | Balanced performance |
| phi3 | 2.3GB | 8GB | Fast | Good | Quick tasks, low memory |
| codellama | 3.8GB | 12GB | Medium | Good | Programming help |
| qwen2.5 | 4.4GB | 12GB | Medium | Good | Multilingual support |

## 🆚 Ollama vs Cloud APIs

| Feature | Ollama (Local) | Anthropic API | Winner |
|---------|----------------|---------------|--------|
| **Cost** | Free forever | $3-15 per million tokens | Ollama |
| **Privacy** | 100% local | Sent to servers | Ollama |
| **Speed** | Depends on CPU | Usually faster | API |
| **Quality** | Good | Excellent | API |
| **Internet** | Not needed | Required | Ollama |
| **Setup** | More complex | Very easy | API |
| **Limits** | Hardware only | Rate limits | Ollama |

## 💡 Tips for Best Performance

### 1. Choose Right Model
```bash
# For learning/testing:
ollama pull llama3.2

# For serious work:
ollama pull llama3.1:8b
```

### 2. Optimize Config
```json
{
  "agent": {
    "temperature": 0.3,  // Lower = more focused
    "max_tokens": 2048   // Fewer tokens = faster
  }
}
```

### 3. Use Tools Wisely
```json
{
  "tools": {
    "bash": {"enabled": true},   // Useful
    "files": {"enabled": true},  // Useful
    "search": {"enabled": false} // Not needed with local model
  }
}
```

## 🔄 Switching Models

```bash
# Try different models easily:
ollama pull mistral
ollama pull phi3

# Update config.json:
{
  "agent": {
    "model": "mistral"  // Change this
  }
}

# Restart Nucleo - that's it!
```

## 📈 Advanced: Running Multiple Models

```bash
# Download multiple models:
ollama pull llama3.2
ollama pull codellama

# Switch in config for different tasks:
# - Use llama3.2 for chat
# - Use codellama for coding help
```

## 🎯 Quick Reference

```bash
# Ollama Commands
ollama serve              # Start server
ollama pull MODEL         # Download model
ollama list              # List downloaded models
ollama rm MODEL          # Remove model
ollama run MODEL         # Test model interactively

# Nucleo Commands
python main.py chat      # Interactive mode
python main.py query "Q" # Single question
```

## ✅ Complete Setup Checklist

- [ ] Ollama installed (`curl -fsSL https://ollama.com/install.sh | sh`)
- [ ] Ollama running (`ollama serve`)
- [ ] Model downloaded (`ollama pull llama3.2`)
- [ ] Model tested (`ollama run llama3.2`)
- [ ] Updated `llm.py` with Ollama support
- [ ] Created `config.json` with Ollama settings
- [ ] Installed httpx (`pip install httpx`)
- [ ] Nucleo working (`python main.py query "test"`)

## 🎊 Success!

You now have a **completely free, private, unlimited AI assistant** running locally!

No API keys, no costs, no limits! ♎
