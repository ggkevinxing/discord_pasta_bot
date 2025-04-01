"""Command error event handlers for the Discord Pasta Bot"""
import logging
from discord.ext import commands

logger = logging.getLogger("bot.events.command_error")

class CommandErrorEvents:
    """On-command error event handlers"""

    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.db = bot.db

        # Register event handlers
        self.bot.event(self.on_command_error)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            command = ctx.message.content[len(self.config.cmd_prefix):]
            pasta_document = self.db.get_command(ctx.guild.id, command)

            if pasta_document is not None:
                await ctx.send(pasta_document['content'])
            else:
                await ctx.send(
                    f"ERROR: Message starts with '{self.config.cmd_prefix}' but I don't recognize "
                    f"this command. Use {self.config.cmd_prefix}help or "
                    f"{self.config.cmd_prefix}commands to see what's available."
                )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"ERROR: User {ctx.author.display_name} has insufficient permissions to use command.")
        else:
            logger.error(f"Command error: {error}")

def setup(bot):
    """Set up command error event handlers"""
    CommandErrorEvents(bot)
    logger.info("Command error events handlers loaded")
