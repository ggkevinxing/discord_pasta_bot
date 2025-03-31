""" Main module for Discord Pasta Bot """

import time
import asyncio
import logging
import os
import sys
import discord
from discord.ext import commands


from pymongo import MongoClient
from dotenv import load_dotenv

from keepalive import KeepAliveServer
from quote_timestamp_util import format_date_for_quotes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot")

# Load environment variables
load_dotenv()

# Environment configuration
TOKEN = os.environ.get("BOT_TOKEN")
DB_URI = os.environ.get("DATABASE_URI")
NICKNAME = os.environ.get("BOT_NICKNAME")
GAME = os.environ.get("BOT_GAME")
CMD_PREFIX = os.environ.get("CMD_PREFIX", default="!")
LOCAL_TZ = os.environ.get("LOCAL_TZ", default="America/New_York")

MAX_MESSAGE_LEN = 2000

# Setup intents (required in newer Discord API versions)
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content
intents.members = True  # Needed for nickname changes

# Initialize bot with command prefix
bot = commands.Bot(command_prefix=CMD_PREFIX, intents=intents, help_command=None)

# Database connection
if DB_URI:
    logger.info("Connecting to database")
    db_client = MongoClient(DB_URI)
    db = db_client['Morton']
else:
    logger.error("ERROR: Database URI not set")
    sys.exit(1)

# Command cooldowns
cooldowns = {}

# Setup events
@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    logger.info(f"Logged in as: {bot.user} (ID: {bot.user.id})")

    # Set initial activity
    if GAME:
        logger.info(f"Setting activity to: {GAME}")
        await bot.change_presence(activity=discord.Game(name=GAME))

    logger.info("Bot is ready!")

@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new guild (server)"""
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

    # Set nickname if specified
    if NICKNAME:
        try:
            me = guild.me
            await me.edit(nick=NICKNAME)
            logger.info(f"Changed nickname to {NICKNAME} in {guild.name}")
        except discord.Forbidden:
            logger.warning(f"Could not change nickname in {guild.name}: Missing permissions")
        except Exception as e:
            logger.error(f"Error changing nickname: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for command errors"""
    if isinstance(error, commands.CommandNotFound):
        command = ctx.message.content[len(CMD_PREFIX):]  # Remove the prefix
        collection = db[str(ctx.guild.id)]
        pasta_document = collection.find_one({'_id': command})

        if pasta_document is not None:
            await ctx.send(pasta_document['content'])
        else:
            await ctx.send(f"ERROR: Message starts with '{CMD_PREFIX}' but I don't recognize this command. Use {CMD_PREFIX}help or {CMD_PREFIX}commands to see what's available.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"ERROR: User {ctx.author.display_name} has insufficient permissions to use command.")
    else:
        logger.error(f"Command error: {error}")

# Admin commands
@bot.command(name="add")
@commands.has_permissions(administrator=True)
async def add_cmd(ctx, command: str = None, *, pasta: str = None):
    """Add a custom command to the bot"""
    if not command or not pasta:
        await ctx.send(f"ERROR: Invalid format. Use {CMD_PREFIX}add <command> <response text>")
        return

    # Remove prefix if it's included in the command
    if command.startswith(CMD_PREFIX):
        command = command[len(CMD_PREFIX):]

    built_in_commands = bot.commands
    built_in_commands_and_aliases = [cmd.name for cmd in built_in_commands] + [alias for cmd in built_in_commands for alias in cmd.aliases]
    # Check if command is valid
    if command in built_in_commands_and_aliases:
        await ctx.send("ERROR: Cannot override hardcoded commands.")
        return

    if not command.strip() or not command.isalnum():
        await ctx.send("ERROR: Command must be alphanumeric with no spaces.")
        return

    if len(CMD_PREFIX + "remove " + command) >= MAX_MESSAGE_LEN:
        await ctx.send("ERROR: Command is too long.")

    # Check that pasta doesn't start with CMD_PREFIX
    if pasta.startswith(CMD_PREFIX):
        await ctx.send(f"ERROR: Command response cannot start with {CMD_PREFIX}")
        return

    # Add command to database
    collection = db[str(ctx.guild.id)]
    write_document = {'_id': command, 'content': pasta}
    result = collection.update_one({'_id': command}, {'$set': write_document}, upsert=True)

    # Check if command was added or replaced
    if result.upserted_id is not None:
        await ctx.send(f"SUCCESS: Command '{CMD_PREFIX}{command}' has been added")
    else:
        await ctx.send(f"SUCCESS: Command '{CMD_PREFIX}{command}' has been replaced")

@bot.command(name="remove", aliases=['rm'])
@commands.has_permissions(administrator=True)
async def remove_cmd(ctx, command: str = None):
    """Remove a custom command from the bot"""
    if not command:
        await ctx.send(f"ERROR: {CMD_PREFIX}remove failed - Invalid input format. Use {CMD_PREFIX}remove <command>")
        return

    # Remove CMD_PREFIX if it's included in the command
    if command.startswith(CMD_PREFIX):
        command = command[len(CMD_PREFIX):]

    # Remove command from database
    collection = db[str(ctx.guild.id)]
    result = collection.delete_one({'_id': command})

    if result.deleted_count == 0:
        await ctx.send(f"ERROR: Could not remove, Command '{CMD_PREFIX}{command}' not found. On the bright side, you wanted to remove it anyways, right?")
    else:
        await ctx.send(f"SUCCESS: Command '{CMD_PREFIX}{command}' has been removed")

@bot.command(name="changegame")
@commands.has_permissions(administrator=True)
async def change_game(ctx, *, game: str = None):
    """Change the bot's playing status"""
    if not game:
        await ctx.send("ERROR: Please provide a game name")
        return

    await bot.change_presence(activity=discord.Game(name=game))
    await ctx.send(f"SUCCESS: Changed playing status to '{game}'")

@bot.command(name="changenick")
@commands.has_permissions(administrator=True)
async def change_nickname(ctx, *, nickname: str = None):
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

@bot.command(name="quote", aliases=["q", "rt"])
async def quote_msg(ctx):
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
    timestamp = format_date_for_quotes(reference_message.created_at, LOCAL_TZ)
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

@bot.command(name="commands", aliases=["help"])
async def get_cmds(ctx):
    """List all available commands"""
    header = f"{ctx.guild.name} commands:"
    await ctx.send(header)

    # Get built-in commands
    built_in_commands = "Built-in commands:\n"
    built_in_commands += f"{CMD_PREFIX}add <command> <response> - Add a new command\n"
    built_in_commands += f"{CMD_PREFIX}remove <command> - Remove a command\n"
    built_in_commands += f"{CMD_PREFIX}changegame <game> - Change bot's playing status\n"
    built_in_commands += f"{CMD_PREFIX}changenick <nickname> - Change bot's nickname\n"
    built_in_commands += f"{CMD_PREFIX}commands or {CMD_PREFIX}help - Show this help message\n\n"
    await ctx.send(built_in_commands)

    # Get custom commands from database
    collection = db[str(ctx.guild.id)]
    cmds = collection.find().batch_size(10).sort('_id', 1)

    has_any_custom_commands = False
    custom_commands = "Custom commands:\n"
    temp = ""

    for command in cmds:
        line = f"{CMD_PREFIX}{command['_id']}\n"
        if has_any_custom_commands is False:
            has_any_custom_commands = True
            await ctx.send(custom_commands)
        if len(custom_commands + temp + line) > MAX_MESSAGE_LEN:
            await ctx.send(temp)
            temp = ""
        temp += line

    if temp:
        await ctx.send(temp)

# Helper function for easter eggs
async def post_txt(textfilename, user):
    """Post the contents of a text file to the channel"""
    global cooldowns

    # Set cooldown
    cooldowns[textfilename] = True

    file = f"{textfilename}.txt"
    message = ""

    try:
        with open(file, "rb") as f:
            for l in f:
                line = l.decode(errors='ignore')
                # Respect Discord's message length limit
                if len(message + line) > MAX_MESSAGE_LEN:
                    await user.send(message)
                    message = ""
                if line.strip():
                    message += line

        if message:
            await user.send(message)

    except FileNotFoundError:
        logger.error(f"Text file not found: {file}")
    except Exception as e:
        logger.error(f"Error posting text file: {e}")

    # Reset cooldown after 5 minutes
    await asyncio.sleep(300)
    cooldowns[textfilename] = False

# Easter egg listener
@bot.event
async def on_message(message):
    """Process messages for easter eggs and command handling"""
    # Ignore messages from bots and DMs
    if message.author.bot or message.guild is None:
        if message.author != bot.user and message.guild is None:
            await message.channel.send("ERROR: I don't currently have support for any commands in private messages. Sorry!")
        return

    # Log messages
    logger.info(f"{message.guild.name} | {message.channel.name} | {message.author.name}: {message.content}")

    # Easter eggs
    infinity_triggers = [
        "In time you will know what it's like to lose.",
        "In Time",
        "Destiny still arrives.",
        "Fun isn't something one considers from balancing the universe.",
        "In",
        "Fun"
    ]

    if any(message.content.startswith(trigger) for trigger in infinity_triggers):
        if not cooldowns.get("avengers-iw", False):
            await post_txt("avengers-iw", message.author)
        else:
            await message.channel.send("Anti-Avengers Initiative is on cooldown. I'm probably still posting it to someone right now. Enjoy your freedom while you can!")

    # Process commands
    await bot.process_commands(message)

def run_bot():
    """Run the bot with keepalive server and auto-restart"""
    # Initialize keepalive server
    keepalive = KeepAliveServer()
    keepalive.start()

    while True:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            logger.critical("Invalid token. Please check your BOT_TOKEN environment variable.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.info("Restarting in 2 minutes...")
            time.sleep(120)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down.")
            sys.exit(0)

if __name__ == "__main__":
    run_bot()
