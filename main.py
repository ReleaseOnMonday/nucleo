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
    """Start Nucleo gateway with configured channels.
    
    Connects Telegram, Discord, and other channels for unified messaging.
    """
    print("♎ Nucleo Gateway")
    print("=" * 50)
    
    # Load configuration
    config = Config().load()
    
    # Check if any channels are enabled
    enabled_channels = []
    for platform in ['telegram', 'discord']:
        if config.get(f'channels.{platform}.enabled', False):
            enabled_channels.append(platform)
    
    if not enabled_channels:
        print("⚠️  No channels enabled in config.json")
        print("\nTo enable channels:")
        print("  1. Copy config.example.json to config.json")
        print("  2. Add bot tokens:")
        print("     - Telegram: Get token from @BotFather")
        print("     - Discord: Get token from https://discord.com/developers")
        print("  3. Set 'enabled': true for desired channels")
        print("  4. (Optional) Set 'allowed_users' to restrict access")
        print("\nExample config:")
        print('  "channels": {')
        print('    "telegram": {')
        print('      "enabled": true,')
        print('      "token": "YOUR_BOT_TOKEN_HERE",')
        print('      "allowed_users": []')
        print('    }')
        print('  }')
        return
    
    print(f"🚀 Starting gateway with channels: {', '.join(enabled_channels)}")
    print()
    
    try:
        # Import channel classes
        from nucleo.channels import (
            ChannelManager,
            MessageBus,
            TelegramChannel,
            DiscordChannel,
        )
        
        # Create message bus
        bus = MessageBus()
        
        # Create channel manager
        manager = ChannelManager(config, bus)
        
        # Register channels
        if config.get('channels.telegram.enabled', False):
            try:
                telegram = TelegramChannel(config, bus)
                manager.register_channel(telegram)
                print("✅ Registered Telegram channel")
            except ValueError as e:
                print(f"⚠️  Telegram error: {e}")
        
        if config.get('channels.discord.enabled', False):
            try:
                discord = DiscordChannel(config, bus)
                manager.register_channel(discord)
                print("✅ Registered Discord channel")
            except ValueError as e:
                print(f"⚠️  Discord error: {e}")
        
        if not manager.channels:
            print("❌ No channels registered")
            return
        
        print()
        
        # Create agent with bus connection
        agent = Agent(config, bus=bus)
        
        # Subscribe agent to inbound messages
        async def handle_inbound(message):
            """Handle inbound message from any channel."""
            try:
                # Get channel name for logging
                channel_name = message.platform.upper()
                user_id = message.sender_id
                
                print(f"\n📨 [{channel_name}] Message from {user_id}: {message.content[:50]}...")
                
                # Chat with agent
                response_chunks = []
                async for chunk in agent.chat(message.content, stream=True, metadata={
                    'platform': message.platform,
                    'sender_id': message.sender_id,
                    'chat_id': message.chat_id,
                }):
                    response_chunks.append(chunk)
                
                response = ''.join(response_chunks)
                
                # Send response back via the channel
                from nucleo.channels import OutboundMessage
                outbound = OutboundMessage(
                    channel=message.platform,
                    chat_id=message.chat_id,
                    content=response,
                )
                
                print(f"💬 [{channel_name}] Sending response: {response[:50]}...")
                await bus.publish_outbound(outbound)
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                import traceback
                traceback.print_exc()
        
        await bus.subscribe_inbound(handle_inbound)
        
        # Start all channels
        print("Starting channels...")
        await manager.start()
        
        print("\n✨ Nucleo Gateway is running!")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        
        # Keep running until interrupted
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping gateway...")
            await manager.stop()
            print("✅ Gateway stopped")
    
    except ImportError as e:
        print(f"❌ Failed to import channel modules: {e}")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


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
