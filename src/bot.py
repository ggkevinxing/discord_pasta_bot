"""Core bot class for Discord Pasta Bot"""
import logging
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

        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Initialize bot with command prefix
        super().__init__(
            command_prefix=self.config.cmd_prefix, 
            intents=intents, 
            help_command=None
        )

        # Connect to database
        self.db = Database(self.config.db_uri)

        # Cooldowns for easter eggs
        self.cooldowns = {}

    async def setup_hook(self):
        """Set up all cogs and event handlers"""
        # Set up command cogs
        await setup_commands(self)

        # Set up events
        setup_events(self)

        

    async def run_bot(self):
        """Run the bot"""
        logger.info("Starting bot")
        await self.start(self.config.token)

    def close(self):
        """Close all connections"""
        self.db.close()
