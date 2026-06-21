"""Core bot class for Discord Pasta Bot"""
import logging
import asyncio
import discord
from discord.ext import commands

from src.utils.db import Database
from src.events import setup as setup_events
from src.commands import setup as setup_commands

logger = logging.getLogger("bot.core")

class PastaBot(commands.Bot):
    """Main bot class"""

    def __init__(self, config):
        """Initialize the bot with configuration"""
        self.config = config
        self._ready_event = asyncio.Event()

        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Set proper chunk settings to avoid unnecessary API calls
        chunk_guilds_at_startup = False  # Don't request all guild members at startup

        # Initialize bot with command prefix
        super().__init__(
            command_prefix=self.config.cmd_prefix, 
            intents=intents,
            help_command=None,
            chunk_guilds_at_startup=chunk_guilds_at_startup,
            max_messages=100  # Limit message cache size
        )

        # Connect to database
        self.db = Database(self.config.db_uri)

        # Cooldowns for easter eggs
        self.cooldowns = {}
        
        # Flag to track proper shutdown
        self._is_closing = False

    async def setup_hook(self):
        """Set up all cogs and event handlers"""
        # Set up command cogs
        await setup_commands(self)

        # Set up events
        setup_events(self)
        
        # Add our own ready handler to set the event
        self.add_listener(self._on_ready_handler, 'on_ready')

    async def _on_ready_handler(self):
        """Internal handler to set the ready event"""
        self._ready_event.set()
        
    async def wait_until_ready(self):
        """Override to use our own ready event"""
        await self._ready_event.wait()
        return await super().wait_until_ready()

    async def run_bot(self):
        """Run the bot with proper session management"""
        logger.info("Starting bot")
        try:
            # Use async context manager to properly close the session
            async with self:
                await self.start(self.config.token)
        except Exception as e:
            logger.error(f"Error in run_bot: {e}")
            raise
        finally:
            # Ensure we're set to closing state
            self._is_closing = True
    
    async def close(self):
        """
        Properly close the bot and all its connections.
        This overrides the parent method to ensure everything is closed cleanly.
        """
        if self._is_closing:
            return  # Prevent double closing
            
        self._is_closing = True
        logger.info("Closing bot connections...")
        
        # Close database connection
        if hasattr(self, 'db') and self.db:
            self.db.close()
            
        # Let the parent class close everything else
        try:
            await super().close()
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
        
        # Clear the ready event
        self._ready_event.clear()
        logger.info("Bot shutdown complete")