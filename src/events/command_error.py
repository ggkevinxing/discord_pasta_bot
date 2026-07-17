"""Command error event handlers for the Discord Pasta Bot"""
import logging
import discord
from discord.ext import commands

from src.utils.log_util import log_http_exception, unwrap_http_exception

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
            # discord.py wraps command body errors in CommandInvokeError; unwrap
            # so we can match the actual HTTPException (e.g. a 429) underneath.
            http_error = unwrap_http_exception(error)
            if http_error is not None:
                log_http_exception(
                    logger,
                    http_error,
                    context={
                        "command": ctx.command.qualified_name if ctx.command else "(unknown)",
                        # Use a textual "dm" sentinel (not an int-looking "(dm)"
                        # sentinel) so log-filtering on guild_id= doesn't mix a
                        # real snowflake with a placeholder.
                        "guild_id": ctx.guild.id if ctx.guild else "dm",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "message_id": ctx.message.id,
                    },
                )
                # Deliberately don't send a reply on 429 — speaking more would
                # consume another token against the same bucket we're blocked on.
            else:
                logger.error(f"Command error: {error}")

def setup(bot):
    """Set up command error event handlers"""
    CommandErrorEvents(bot)
    logger.info("Command error events handlers loaded")
