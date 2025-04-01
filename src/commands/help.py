"""Help and command listing commands for the Discord Pasta Bot"""
import logging
from discord.ext import commands

logger = logging.getLogger("bot.commands.help")

class HelpCommands(commands.Cog):
    """Commands for listing available bot commands"""

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.config = bot.config

    @commands.command(name="commands", aliases=["help"])
    async def get_cmds(self, ctx):
        """List all available commands"""
        header = f"{ctx.guild.name} commands:"
        await ctx.send(header)

        # Get built-in commands
        built_in_commands = "Built-in commands:\n"
        built_in_commands += f"{self.config.cmd_prefix}add <command> <response> - Add a new command\n"
        built_in_commands += f"{self.config.cmd_prefix}remove <command> - Remove a command\n"
        built_in_commands += f"{self.config.cmd_prefix}changegame <game> - Change bot's playing status\n"
        built_in_commands += f"{self.config.cmd_prefix}changenick <nickname> - Change bot's nickname\n"
        built_in_commands += f"{self.config.cmd_prefix}quote - Quote a message (use by replying to a message)\n"
        built_in_commands += f"{self.config.cmd_prefix}commands or {self.config.cmd_prefix}help - Show this help message\n\n"
        await ctx.send(built_in_commands)

        # Get custom commands from database
        cmds = self.db.get_all_commands(ctx.guild.id)

        has_any_custom_commands = False
        custom_commands = "Custom commands:\n"
        temp = ""

        for command in cmds:
            line = f"{self.config.cmd_prefix}{command['_id']}\n"
            if has_any_custom_commands is False:
                has_any_custom_commands = True
                await ctx.send(custom_commands)
            if len(custom_commands + temp + line) > self.config.max_message_len:
                await ctx.send(temp)
                temp = ""
            temp += line

        if temp:
            await ctx.send(temp)
        elif not has_any_custom_commands:
            await ctx.send("No custom commands have been added yet.")

async def setup(bot):
    """Add the help commands to the bot"""
    await bot.add_cog(HelpCommands(bot))
    logger.info("Help commands cog loaded")
