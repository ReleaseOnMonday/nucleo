"""Discord channel implementation for Nucleo gateway."""

import asyncio
import logging
from typing import Optional
import discord
from discord.ext import commands

from ..config import Config
from .base import BaseChannel
from .bus import MessageBus
from .message import OutboundMessage

logger = logging.getLogger(__name__)


class NucleoClient(discord.Client):
    """Discord client for Nucleo gateway."""
    
    def __init__(self, channel: 'DiscordChannel', *args, **kwargs):
        """Initialize Discord client.
        
        Args:
            channel: DiscordChannel instance
            *args, **kwargs: Arguments for discord.Client
        """
        super().__init__(*args, **kwargs)
        self.channel = channel
    
    async def on_ready(self):
        """Called when the client is ready."""
        logger.info(f"🎮 Discord logged in as {self.user}")
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages.
        
        Args:
            message: Discord message
        """
        # Ignore bot's own messages
        if message.author == self.user:
            return
        
        # Ignore if from DM and user not allowed
        if isinstance(message.channel, discord.DMChannel):
            if not self.channel.is_user_allowed(str(message.author.id)):
                await message.reply("❌ You are not authorized to use this bot.")
                return
        
        # Ignore messages from other bots in guilds
        if message.author.bot and not isinstance(message.channel, discord.DMChannel):
            return
        
        # Collect attachments
        media_paths = []
        for attachment in message.attachments:
            try:
                file_path = f"/tmp/discord_{attachment.id}_{attachment.filename}"
                await attachment.save(file_path)
                media_paths.append(file_path)
            except Exception as e:
                logger.error(f"Failed to download attachment: {e}")
        
        # Show typing indicator
        async with message.channel.typing():
            # Prepare metadata
            metadata = {
                'message_id': str(message.id),
                'username': str(message.author),
                'peer_kind': 'direct' if isinstance(message.channel, discord.DMChannel) else 'guild',
                'peer_id': str(message.channel.id),
                'guild_id': str(message.guild.id) if message.guild else None,
            }
            
            # Handle the inbound message
            await self.channel.handle_inbound_message(
                sender_id=str(message.author.id),
                chat_id=str(message.channel.id),
                content=message.content,
                media=media_paths,
                metadata=metadata,
            )


class DiscordChannel(BaseChannel):
    """Discord channel implementation using websocket."""
    
    def __init__(self, config: Config, bus: MessageBus):
        """Initialize Discord channel.
        
        Args:
            config: Nucleo configuration
            bus: Message bus
        """
        super().__init__(config, bus)
        self.token = config.get('channels.discord.token')
        if not self.token:
            raise ValueError("channels.discord.token not configured")
        
        self.client: Optional[NucleoClient] = None
    
    async def start(self) -> None:
        """Start Discord bot using websocket."""
        if self._running:
            logger.warning("Discord channel already running")
            return
        
        try:
            # Create Discord client with intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.direct_messages = True
            
            self.client = NucleoClient(self, intents=intents)
            
            self._running = True
            
            logger.info("🎮 Discord channel starting...")
            
            # Start the client (runs indefinitely)
            await self.client.start(self.token)
            
        except Exception as e:
            self._running = False
            logger.error(f"❌ Discord channel error: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop Discord bot."""
        if not self._running:
            return
        
        self._running = False
        
        if self.client:
            try:
                await self.client.close()
                logger.info("🛑 Discord channel stopped")
            except Exception as e:
                logger.error(f"Error stopping Discord: {e}")
    
    async def send(self, message: OutboundMessage) -> None:
        """Send message via Discord.
        
        Args:
            message: Message to send
        """
        if not self.client or not self.client.is_ready():
            raise RuntimeError("Discord client not ready")
        
        try:
            channel_id = int(message.chat_id)
            channel = self.client.get_channel(channel_id)
            
            if not channel:
                raise ValueError(f"Channel not found: {channel_id}")
            
            # Send text message in chunks if too long (Discord limit: 2000 chars)
            if message.content:
                content = message.content
                # Split into chunks of 2000 chars
                while len(content) > 2000:
                    chunk = content[:2000]
                    await channel.send(chunk)
                    content = content[2000:]
                
                if content:
                    await channel.send(content)
            
            # Send media files
            for file_path in message.media:
                try:
                    await channel.send(file=discord.File(file_path))
                except Exception as e:
                    logger.error(f"Failed to send file {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Failed to send Discord message: {e}")
            raise
    
    @property
    def name(self) -> str:
        """Get channel name."""
        return 'discord'
