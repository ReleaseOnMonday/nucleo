"""Base channel class for Nucleo channel implementations."""

from abc import ABC, abstractmethod
from typing import Optional
from ..config import Config
from .message import InboundMessage, OutboundMessage
from .bus import MessageBus


class BaseChannel(ABC):
    """Abstract base class for Nucleo channel implementations."""

    def __init__(self, config: Config, bus: MessageBus):
        """Initialize channel.

        Args:
            config: Nucleo configuration
            bus: Message bus for publishing/subscribing
        """
        self.config = config
        self.bus = bus
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if channel is running."""
        return self._running

    @abstractmethod
    async def start(self) -> None:
        """Start the channel listener/connection.

        Raises:
            Exception: If start fails
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel listener/connection."""
        pass

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None:
        """Send message via this channel.

        Args:
            message: OutboundMessage to send

        Raises:
            Exception: If send fails
        """
        pass

    async def handle_inbound_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Handle inbound message and publish to bus.

        Args:
            sender_id: ID of message sender
            chat_id: ID of chat/conversation
            content: Message content
            media: Optional list of file paths
            metadata: Optional platform-specific metadata
        """
        if media is None:
            media = []
        if metadata is None:
            metadata = {}

        message = InboundMessage(
            platform=self.name,
            sender_id=sender_id,
            chat_id=chat_id,
            content=content,
            media=media,
            metadata=metadata,
        )

        await self.bus.publish_inbound(message)

    @property
    @abstractmethod
    def name(self) -> str:
        """Get channel name (e.g., 'telegram', 'discord').

        Returns:
            Channel name
        """
        pass

    def is_user_allowed(self, user_id: str) -> bool:
        """Check if user is allowed to use this channel.

        Args:
            user_id: User ID to check

        Returns:
            True if user is allowed, False otherwise
        """
        allowed_users_key = f"channels.{self.name}.allowed_users"
        allowed_users = self.config.get(allowed_users_key, [])

        if not allowed_users:
            # Empty list means allow all
            return True

        return str(user_id) in [str(u) for u in allowed_users]
