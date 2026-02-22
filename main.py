#!/usr/bin/env python3
"""Nucleo CLI entry point."""

import asyncio
import sys
from pathlib import Path

from nucleo import Agent, Config


async def chat_interactive():
    """Interactive chat mode."""
    print("♎ Nucleo - Interactive Chat")
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'reset' to clear history\n")
    
    # Load configuration
    config = Config().load()
    agent = Agent(config)
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye! 👋")
                break
            
            if user_input.lower() == 'reset':
                agent.reset()
                print("🔄 Conversation history cleared\n")
                continue
            
            # Stream response
            print("Assistant: ", end='', flush=True)
            async for chunk in agent.chat(user_input, stream=True):
                print(chunk, end='', flush=True)
            print("\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


async def query_once(message: str):
    """Single query mode.
    
    Args:
        message: User message
    """
    config = Config().load()
    agent = Agent(config)
    
    print("♎ Nucleo \n")
    print(f"You: {message}\n")
    print("Assistant: ", end='', flush=True)
    
    async for chunk in agent.chat(message, stream=True):
        print(chunk, end='', flush=True)
    
    print("\n")


def print_usage():
    """Print usage information."""
    print("""
♎ Nucleo - Ultra-lightweight AI Assistant

Usage:
    python main.py chat                    # Interactive chat mode
    python main.py query "your question"   # Single query
    python main.py gateway                 # Start gateway (Telegram/Discord)
    python main.py init                    # Initialize configuration

Examples:
    python main.py chat
    python main.py query "What is 2+2?"
    python main.py gateway

Configuration:
    Create config.json (see config.example.json for template)
    
Environment Variables:
    NUCLEO_CONFIG - Path to config file (default: ./config.json)
""")


def init_config():
    """Initialize configuration file."""
    config_path = Path("config.json")
    example_path = Path("config.example.json")
    
    if config_path.exists():
        print("⚠️  config.json already exists")
        response = input("Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted")
            return
    
    if example_path.exists():
        import shutil
        shutil.copy(example_path, config_path)
        print("✅ Created config.json from example")
        print("\n📝 Please edit config.json and add your API keys:")
        print("   - providers.anthropic.api_key")
        print("   - tools.search.api_key (optional)")
    else:
        print("❌ config.example.json not found")


async def start_gateway():
    """Start gateway for Telegram/Discord.
    
    Note: This is a placeholder. Full implementation would include
    channel handlers similar to the Go version.
    """
    print("♎ Nucleo Gateway")
    print("⚠️  Gateway mode not yet implemented")
    print("Coming soon: Telegram, Discord, Whatsapp and other channels")
    
    # TODO: Implement channel handlers
    # from nucleo.channels import TelegramChannel, DiscordChannel
    # ...


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'chat':
        asyncio.run(chat_interactive())
    
    elif command == 'query':
        if len(sys.argv) < 3:
            print("❌ Error: query requires a message")
            print("Usage: python main.py query 'your question'")
            return
        message = ' '.join(sys.argv[2:])
        asyncio.run(query_once(message))
    
    elif command == 'gateway':
        asyncio.run(start_gateway())
    
    elif command == 'init':
        init_config()
    
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()


if __name__ == '__main__':
    main()
