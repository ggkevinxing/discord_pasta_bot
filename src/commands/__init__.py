"""Command modules for the Discord Pasta Bot"""
from discord.ext import commands

from src.commands.admin import setup as setup_admin
from src.commands.quotes import setup as setup_quotes
from src.commands.help import setup as setup_help

# You could also include a setup_all function to load all commands at once
async def setup(bot: commands.Bot):
    """Set up all command modules for the bot"""
    await setup_admin(bot)
    await setup_quotes(bot)
    await setup_help(bot)