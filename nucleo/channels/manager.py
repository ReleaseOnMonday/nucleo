"""Channel manager for Nucleo gateway."""

import asyncio
import logging
from typing import Dict, Optional
from ..config import Config
from .base import BaseChannel
from .bus import MessageBus
from .message import OutboundMessage

logger = logging.getLogger(__name__)


class ChannelManager:
    """Manages lifecycle of Nucleo channels."""

    def __init__(self, config: Config, bus: Optional[MessageBus] = None):
        """Initialize channel manager.

        Args:
            config: Nucleo configuration
            bus: Optional message bus (creates new if None)
        """
        self.config = config
        self.bus = bus or MessageBus()
        self.channels: Dict[str, BaseChannel] = {}
        self._running = False

    def register_channel(self, channel: BaseChannel) -> None:
        """Register a channel with the manager.

        Args:
            channel: Channel to register
        """
        self.channels[channel.name] = channel
        logger.info(f"📱 Registered channel: {channel.name}")

    async def start(self) -> None:
        """Start all registered channels."""
        if self._running:
            logger.warning("Channel manager already running")
            return

        self._running = True

        # Subscribe to outbound messages
        await self.bus.subscribe_outbound(self._route_outbound)

        # Start all channels
        start_tasks = []
        for channel_name, channel in self.channels.items():
            if self.config.get(f"channels.{channel_name}.enabled", False):
                logger.info(f"▶️  Starting channel: {channel_name}")
                start_tasks.append(channel.start())
            else:
                logger.info(f"⊘ Skipping disabled channel: {channel_name}")

        if start_tasks:
            results = await asyncio.gather(*start_tasks, return_exceptions=True)
            for channel_name, result in zip(self.channels.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Failed to start {channel_name}: {result}")

    async def stop(self) -> None:
        """Stop all running channels."""
        if not self._running:
            return

        self._running = False

        stop_tasks = []
        for channel_name, channel in self.channels.items():
            if channel.is_running:
                logger.info(f"⏹️  Stopping channel: {channel_name}")
                stop_tasks.append(channel.stop())

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        logger.info("✅ All channels stopped")

    async def _route_outbound(self, message: OutboundMessage) -> None:
        """Route outbound message to appropriate channel.

        Args:
            message: OutboundMessage to route
        """
        if message.channel not in self.channels:
            logger.error(f"❌ Unknown channel: {message.channel}")
            return

        channel = self.channels[message.channel]
        if not channel.is_running:
            logger.error(f"❌ Channel not running: {message.channel}")
            return

        try:
            await channel.send(message)
        except Exception as e:
            logger.error(f"❌ Failed to send via {message.channel}: {e}")

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running
