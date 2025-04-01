"""Admin commands for the bot"""
import logging
import discord
from discord.ext import commands

logger = logging.getLogger("bot.commands.admin")

class AdminCommands(commands.Cog):
    """Admin commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.config = bot.config
    
    @commands.command(name="add")
    @commands.has_permissions(administrator=True)
    async def add_cmd(self, ctx, command: str = None, *, pasta: str = None):
        """Add a custom command to the bot"""
        if not command or not pasta:
            await ctx.send(f"ERROR: Invalid format. Use {self.config.cmd_prefix}add <command> <response text>")
            return

        # Remove prefix if it's included in the command
        if command.startswith(self.config.cmd_prefix):
            command = command[len(self.config.cmd_prefix):]

        # Check if command is valid
        built_in_commands = self.bot.commands
        built_in_commands_and_aliases = [
            cmd.name for cmd in built_in_commands
        ] + [
            alias for cmd in built_in_commands for alias in cmd.aliases
        ]
        
        if command in built_in_commands_and_aliases:
            await ctx.send("ERROR: Cannot override hardcoded commands.")
            return

        if not command.strip() or not command.isalnum():
            await ctx.send("ERROR: Command must be alphanumeric with no spaces.")
            return

        if len(self.config.cmd_prefix + "remove " + command) >= self.config.max_message_len:
            await ctx.send("ERROR: Command is too long.")
            return

        # Check that pasta doesn't start with CMD_PREFIX
        if pasta.startswith(self.config.cmd_prefix):
            await ctx.send(f"ERROR: Command response cannot start with {self.config.cmd_prefix}")
            return

        # Add command to database
        is_new = self.db.add_command(ctx.guild.id, command, pasta)

        # Send appropriate response
        if is_new:
            await ctx.send(f"SUCCESS: Command '{self.config.cmd_prefix}{command}' has been added")
        else:
            await ctx.send(f"SUCCESS: Command '{self.config.cmd_prefix}{command}' has been replaced")

    @commands.command(name="remove", aliases=['rm'])
    @commands.has_permissions(administrator=True)
    async def remove_cmd(self, ctx, command: str = None):
        """Remove a custom command from the bot"""
        if not command:
            await ctx.send(
                f"ERROR: {self.config.cmd_prefix}remove failed - Invalid input format. "
                f"Use {self.config.cmd_prefix}remove <command>"
            )
            return

        # Remove CMD_PREFIX if it's included in the command
        if command.startswith(self.config.cmd_prefix):
            command = command[len(self.config.cmd_prefix):]

        # Remove command from database
        success = self.db.remove_command(ctx.guild.id, command)

        if not success:
            await ctx.send(
                f"ERROR: Could not remove, Command '{self.config.cmd_prefix}{command}' not found. "
                f"On the bright side, you wanted to remove it anyways, right?"
            )
        else:
            await ctx.send(f"SUCCESS: Command '{self.config.cmd_prefix}{command}' has been removed")

    @commands.command(name="changegame")
    @commands.has_permissions(administrator=True)
    async def change_game(self, ctx, *, game: str = None):
        """Change the bot's playing status"""
        if not game:
            await ctx.send("ERROR: Please provide a game name")
            return

        await self.bot.change_presence(activity=discord.Game(name=game))
        await ctx.send(f"SUCCESS: Changed playing status to '{game}'")

    @commands.command(name="changenick")
    @commands.has_permissions(administrator=True)
    async def change_nickname(self, ctx, *, nickname: str = None):
        """Change the bot's nickname on the server"""
        if not nickname:
            await ctx.send("ERROR: Please provide a nickname")
            return
            
        try:
            await ctx.guild.me.edit(nick=nickname)
            await ctx.send(f"SUCCESS: Changed nickname to '{nickname}'")
        except discord.Forbidden:
            await ctx.send("ERROR: I don't have permission to change my nickname")
        except Exception as e:
            await ctx.send(f"ERROR: Could not change nickname: {e}")

async def setup(bot):
    """Add the admin commands to the bot"""
    await bot.add_cog(AdminCommands(bot))
    logger.info("Admin commands cog loaded")