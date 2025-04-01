"""Ready event handlers for the Discord Pasta Bot"""
import logging
import discord

logger = logging.getLogger("bot.events.ready")

class ReadyEvents:
    """On-ready and guild join event handlers"""

    def __init__(self, bot):
        self.bot = bot.bot
        self.config = bot.config

        # Register event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_guild_join)

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        logger.info(f"Logged in as: {self.bot.user} (ID: {self.bot.user.id})")

        # Set initial activity
        if self.config.game:
            logger.info(f"Setting activity to: {self.config.game}")
            await self.bot.change_presence(activity=discord.Game(name=self.config.game))

        # Log connected guilds
        guild_list = [f"{guild.name} (ID: {guild.id})" for guild in self.bot.guilds]
        logger.info(f"Connected to {len(self.bot.guilds)} guilds:")
        for guild in guild_list:
            logger.info(f"  - {guild}")

        logger.info("Bot is ready!")

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild (server)"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        # Set nickname if specified
        if self.config.nickname:
            try:
                me = guild.me
                await me.edit(nick=self.config.nickname)
                logger.info(f"Changed nickname to {self.config.nickname} in {guild.name}")
            except discord.Forbidden:
                logger.warning(f"Could not change nickname in {guild.name}: Missing permissions")
            except Exception as e:
                logger.error(f"Error changing nickname: {e}")

        # Send welcome message to first available text channel
        try:
            general_channel = None
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    general_channel = channel
                    if channel.name == "general":
                        break

            if general_channel:
                await general_channel.send(
                    f"Hello! I'm a customizable command bot. Use `{self.config.cmd_prefix}help` "
                    f"to see available commands. Server admins can add custom commands with "
                    f"`{self.config.cmd_prefix}add <command> <response>`."
                )
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

def setup(bot):
    """Set up ready event handlers"""
    ReadyEvents(bot)
    logger.info("Ready events handlers loaded")
