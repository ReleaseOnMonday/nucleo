"""Message types for Nucleo channels."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class InboundMessage:
    """Message received from a channel platform."""

    platform: str
    sender_id: str
    chat_id: str
    content: str
    media: List[str] = field(default_factory=list)  # File paths
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate required fields."""
        if not self.platform or not self.sender_id or not self.chat_id:
            raise ValueError("platform, sender_id, and chat_id are required")


@dataclass
class OutboundMessage:
    """Message to be sent to a channel platform."""

    channel: str
    chat_id: str
    content: str
    media: List[str] = field(default_factory=list)  # File paths to send
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate required fields."""
        if not self.channel or not self.chat_id:
            raise ValueError("channel and chat_id are required")
