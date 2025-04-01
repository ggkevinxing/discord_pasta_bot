"""Quote commands for the Discord Pasta Bot"""
import logging
import discord
from discord.ext import commands

from src.utils.timestamp import format_date_for_quotes

logger = logging.getLogger("bot.commands.quotes")

class QuoteCommands(commands.Cog):
    """Commands for quoting other messages"""

    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @commands.command(name="quote", aliases=["q", "rt"])
    async def quote_msg(self, ctx):
        """Quote a message with optional additional content"""
        # Check if this is a reply to another message
        if not ctx.message.reference:
            await ctx.send("ERROR: You need to reply to a message to quote it")
            return

        # Get the message being replied to
        try:
            reference_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            await ctx.send("ERROR: Could not find the message you're replying to")
            return

        # Get original message details
        original_content = reference_message.content
        original_author = reference_message.author.display_name
        timestamp = format_date_for_quotes(reference_message.created_at, self.config.local_tz)
        msg_url = reference_message.jump_url

        # Prep quoter
        quoter = ctx.message.author.display_name
        formatted_quoter = f"{quoter} quoted:"

        # Create an embed that resembles a forwarded message
        embed = discord.Embed(description=original_content, url=msg_url, title="←")
        embed.set_footer(text=f"{original_author} • {timestamp}")
        embed.set_author(name=formatted_quoter, url=msg_url)

        # Send the manually created "forwarded" message
        await ctx.send(embed=embed)

        # Delete the original command message
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("ERROR: I don't have permission to delete messages")

async def setup(bot):
    """Add the quote commands to the bot"""
    await bot.add_cog(QuoteCommands(bot))
    logger.info("Quote commands cog loaded")
