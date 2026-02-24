"""Lightweight message bus for Nucleo channels."""

from typing import Callable, List
import asyncio
from .message import InboundMessage, OutboundMessage


class MessageBus:
    """Async pub/sub message bus for inbound and outbound channel messages."""
    
    def __init__(self):
        """Initialize message bus."""
        self._inbound_subscribers: List[Callable[[InboundMessage], None]] = []
        self._outbound_subscribers: List[Callable[[OutboundMessage], None]] = []
        self._lock = asyncio.Lock()
    
    async def subscribe_inbound(self, callback: Callable[[InboundMessage], None]) -> None:
        """Subscribe to inbound messages from channels.
        
        Args:
            callback: Async function that receives InboundMessage
        """
        async with self._lock:
            self._inbound_subscribers.append(callback)
    
    async def subscribe_outbound(self, callback: Callable[[OutboundMessage], None]) -> None:
        """Subscribe to outbound messages to channels.
        
        Args:
            callback: Async function that receives OutboundMessage
        """
        async with self._lock:
            self._outbound_subscribers.append(callback)
    
    async def publish_inbound(self, message: InboundMessage) -> None:
        """Publish inbound message from a channel.
        
        Args:
            message: InboundMessage to publish
        """
        # Create tasks for all subscribers
        tasks = []
        async with self._lock:
            subscribers = list(self._inbound_subscribers)
        
        for callback in subscribers:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(message))
            else:
                # Handle sync callbacks
                callback(message)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def publish_outbound(self, message: OutboundMessage) -> None:
        """Publish outbound message to be sent via a channel.
        
        Args:
            message: OutboundMessage to publish
        """
        # Create tasks for all subscribers
        tasks = []
        async with self._lock:
            subscribers = list(self._outbound_subscribers)
        
        for callback in subscribers:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(message))
            else:
                # Handle sync callbacks
                callback(message)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
