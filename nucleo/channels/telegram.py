"""Telegram channel implementation for Nucleo gateway."""

import asyncio
import logging
from typing import Optional
from telegram import Update, error
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler

from ..config import Config
from .base import BaseChannel
from .bus import MessageBus
from .message import OutboundMessage

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram channel implementation using long polling."""
    
    def __init__(self, config: Config, bus: MessageBus):
        """Initialize Telegram channel.
        
        Args:
            config: Nucleo configuration
            bus: Message bus
        """
        super().__init__(config, bus)
        self.token = config.get('channels.telegram.token')
        if not self.token:
            raise ValueError("channels.telegram.token not configured")
        
        self.app: Optional[Application] = None
        self._app_running = False
    
    async def start(self) -> None:
        """Start Telegram bot using long polling."""
        if self._running:
            logger.warning("Telegram channel already running")
            return
        
        try:
            # Create application
            self.app = Application.builder().token(self.token).build()
            
            # Register handlers
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            self.app.add_handler(CommandHandler("start", self._handle_start))
            
            self._running = True
            self._app_running = True
            
            logger.info("🤖 Telegram channel started (polling)")
            
            # Start polling (runs indefinitely)
            await self.app.run_polling()
            
        except Exception as e:
            self._running = False
            logger.error(f"❌ Telegram channel error: {e}")
            raise
        finally:
            self._app_running = False
    
    async def stop(self) -> None:
        """Stop Telegram bot."""
        if not self._running:
            return
        
        self._running = False
        
        if self.app:
            try:
                await self.app.stop()
                logger.info("🛑 Telegram channel stopped")
            except Exception as e:
                logger.error(f"Error stopping Telegram: {e}")
    
    async def send(self, message: OutboundMessage) -> None:
        """Send message via Telegram.
        
        Args:
            message: Message to send
        """
        if not self.app:
            raise RuntimeError("Telegram app not initialized")
        
        try:
            chat_id = int(message.chat_id)
            
            # Send text message
            if message.content:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=message.content
                )
            
            # Send media files
            for file_path in message.media:
                try:
                    with open(file_path, 'rb') as f:
                        await self.app.bot.send_document(
                            chat_id=chat_id,
                            document=f
                        )
                except Exception as e:
                    logger.error(f"Failed to send file {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            raise
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id
        
        if not self.is_user_allowed(str(user_id)):
            await update.message.reply_text(
                "❌ You are not authorized to use this bot."
            )
            return
        
        await update.message.reply_text(
            "🤖 Welcome to Nucleo!\n\n"
            "Send any message and I'll help you. "
            "I can help with tasks, answer questions, search information, and more!"
        )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return
        
        user = update.effective_user
        chat = update.effective_chat
        
        # Check if user is allowed
        if not self.is_user_allowed(str(user.id)):
            await update.message.reply_text(
                "❌ You are not authorized to use this bot."
            )
            return
        
        # Collect media files if any
        media_paths = []
        if update.message.document:
            try:
                file = await update.message.document.get_file()
                file_path = f"/tmp/telegram_{file.file_id}"
                await file.download_to_drive(file_path)
                media_paths.append(file_path)
            except Exception as e:
                logger.error(f"Failed to download file: {e}")
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        # Prepare metadata
        metadata = {
            'message_id': str(update.message.message_id),
            'username': user.username or f"user_{user.id}",
            'peer_kind': 'direct' if chat.type == 'private' else 'group',
            'peer_id': str(chat.id),
        }
        
        # Handle the inbound message
        await self.handle_inbound_message(
            sender_id=str(user.id),
            chat_id=str(chat.id),
            content=update.message.text,
            media=media_paths,
            metadata=metadata,
        )
    
    @property
    def name(self) -> str:
        """Get channel name."""
        return 'telegram'
