"""
Nucleo Gateway Documentation

The Nucleo Gateway enables AI assistant access via multiple messaging platforms:
- Telegram
- Discord

## Quick Start

### 1. Configure Your Channels

Copy the example config and add bot tokens:

```bash
cp config.example.json config.json
```

Edit `config.json` and add your bot tokens:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_TELEGRAM_BOT_TOKEN",
      "allowed_users": []  // Empty = allow all. Add user IDs to restrict
    },
    "discord": {
      "enabled": true,
      "token": "YOUR_DISCORD_BOT_TOKEN",
      "allowed_users": []  // Empty = allow all. Add user IDs to restrict
    }
  },
  // ... rest of config
}
```

### 2. Telegram Setup

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow prompts
3. Copy the token you receive
4. Paste it in config.json under `channels.telegram.token`
5. Optional: Restrict access by adding your user ID to `allowed_users`

To get your user ID:
- Send `/start` to `@NucleoBot` (your bot)
- The response will include your user ID (or check logs)

### 3. Discord Setup

1. Go to https://discord.com/developers/applications
2. Click "New Application" and name it "Nucleo"
3. Go to "Bot" tab and click "Add Bot"
4. Under TOKEN, click "Copy" to copy the token
5. Paste it in config.json under `channels.discord.token`
6. Go to OAuth2 > URL Generator
7. Select scopes: `bot`
8. Select permissions: `Send Messages`, `Read Messages/View Channels`, `Attach Files`
9. Copy the generated URL and open it to invite the bot to a server

### 4. Start the Gateway

```bash
python main.py gateway
```

You should see:
```
♎ Nucleo Gateway
==================================================
✅ Registered Telegram channel
✅ Registered Discord channel

Starting channels...
🤖 Telegram channel started (polling)
🎮 Discord logged in as NucleoBot#1234

✨ Nucleo Gateway is running!
Press Ctrl+C to stop
```

### 5. Test It Out

- Send a message on Telegram or Discord
- Nucleo will process it and respond
- Stop with Ctrl+C

## Architecture

### Components

1. **MessageBus** - Lightweight pub/sub for async message routing
2. **BaseChannel** - Abstract class for all channel implementations
3. **ChannelManager** - Manages channel lifecycle and message routing
4. **TelegramChannel** - Long polling implementation
5. **DiscordChannel** - Websocket implementation

### Message Flow

```
User sends message
    ↓
Channel listens and normalizes
    ↓
Publish to MessageBus (inbound)
    ↓
Agent processes message with chat()
    ↓
Agent publishes response via MessageBus (outbound)
    ↓
ChannelManager routes to appropriate channel
    ↓
Channel sends response to user
```

### Configuration

Each channel supports:

- `enabled` - Boolean to enable/disable
- `token` - Bot token for authentication
- `allowed_users` - List of user IDs to allow (empty = all users)

## Features

### Supported
- ✅ Text messages
- ✅ File uploads/downloads (with agents tools)
- ✅ Multiple users simultaneously
- ✅ User whitelisting
- ✅ Streaming responses
- ✅ Tool execution (bash, files, search)
- ✅ Conversation history per user

### Coming Soon
- 🔄 Slack integration
- 🔄 WhatsApp integration
- 🔄 Voice message transcription
- 🔄 Rich formatting (markdown, etc.)
- 🔄 Message reactions
- 🔄 Thread support

## Troubleshooting

### Telegram not responding
- Check token is correct in config.json
- Verify bot token format
- Check @BotFather shows "bot joined"
- Look for error messages in console

### Discord not responding
- Check token is correct in config.json
- Verify bot has permissions in server
- Check SERVER_ID or channel permissions
- Ensure bot role is high enough

### Messages not processing
- Check config.json is valid JSON
- Verify Agent config (LLM API keys, etc.)
- Check console logs for errors
- Try sending simple text message first

## Advanced Usage

### Programmatic Gateway Use

```python
from nucleo import Agent, Config
from nucleo.channels import ChannelManager, TelegramChannel, DiscordChannel, MessageBus

# Create components
config = Config().load()
bus = MessageBus()
agent = Agent(config, bus=bus)
manager = ChannelManager(config, bus)

# Register channels
telegram = TelegramChannel(config, bus)
discord = DiscordChannel(config, bus)
manager.register_channel(telegram)
manager.register_channel(discord)

# Handle inbound messages
async def handle_message(msg):
    async for chunk in agent.chat(msg.content, stream=True, metadata={
        'platform': msg.platform,
        'sender_id': msg.sender_id,
        'chat_id': msg.chat_id,
    }):
        # Send response
        pass

await bus.subscribe_inbound(handle_message)
await manager.start()
```

### Custom Channel Implementation

Extend `BaseChannel` to create new channels:

```python
from nucleo.channels import BaseChannel, OutboundMessage

class MyChannel(BaseChannel):
    @property
    def name(self) -> str:
        return 'mychannel'
    
    async def start(self) -> None:
        self._running = True
        # Listen for messages
    
    async def stop(self) -> None:
        self._running = False
    
    async def send(self, message: OutboundMessage) -> None:
        # Send message via your platform
        pass
```

## Performance Considerations

- **Telegram**: Uses polling (1-3 sec latency per default timeout)
- **Discord**: Uses websocket (< 100ms latency)
- **Memory**: ~100MB per running gateway
- **Concurrent users**: Limited by LLM rate limits
- **Message throughput**: ~10-100 msgs/sec depending on response time

## Security

- Bot tokens are sensitive - never commit to git
- Use `.env` files or environment variables
- Consider using `allowed_users` for production
- Monitor logs for suspicious activity
- Rotate tokens regularly

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review console logs for errors
3. Check Nucleo documentation
4. Report issues with:
   - Config snippet (sanitized)
   - Error message from console
   - Reproduction steps
"""
