import time
import os
import sys
import discord
from discord.ext import commands
import asyncio
import logging

from pymongo import MongoClient
from dotenv import load_dotenv

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

MAX_MESSAGE_LEN = 2000

# Setup intents (required in newer Discord API versions)
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content
intents.members = True  # Needed for nickname changes

# Initialize bot with command prefix
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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

class CustomHelpCommand(commands.HelpCommand):
    """Custom help command that lists all custom commands from the database"""
    
    async def send_bot_help(self, mapping):
        ctx = self.context
        await get_cmds(ctx)

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
        command = ctx.message.content[1:]  # Remove the prefix
        collection = db[str(ctx.guild.id)]
        pasta_document = collection.find_one({'_id': command})
        
        if pasta_document is not None:
            await ctx.send(pasta_document['content'])
        else:
            await ctx.send("ERROR: Message starts with '!' but I don't recognize this command. Use !help or !commands to see what's available.")
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
        await ctx.send("ERROR: Invalid format. Use !add <command> <response text>")
        return
        
    # Remove ! if it's included in the command
    if command.startswith("!"):
        command = command[1:]
        
    # Check if command is valid
    if command in ("add", "help", "commands", "remove", "changegame", "changenick"):
        await ctx.send("ERROR: Cannot override hardcoded commands.")
        return
        
    if not command.strip() or not command.isalnum():
        await ctx.send("ERROR: Command must be alphanumeric with no spaces.")
        return
        
    # Check that pasta doesn't start with !
    if pasta.startswith("!"):
        await ctx.send("ERROR: Command response cannot start with !")
        return
        
    # Add command to database
    collection = db[str(ctx.guild.id)]
    write_document = {'_id': command, 'content': pasta}
    result = collection.update_one({'_id': command}, {'$set': write_document}, upsert=True)
    
    # Check if command was added or replaced
    if result.upserted_id is not None:
        await ctx.send(f"SUCCESS: Command '!{command}' has been added")
    else:
        await ctx.send(f"SUCCESS: Command '!{command}' has been replaced")

@bot.command(name="remove")
@commands.has_permissions(administrator=True)
async def remove_cmd(ctx, command: str = None):
    """Remove a custom command from the bot"""
    if not command:
        await ctx.send("ERROR: !remove failed - Invalid input format. Use !remove <command>")
        return
        
    # Remove ! if it's included in the command
    if command.startswith("!"):
        command = command[1:]
        
    # Remove command from database
    collection = db[str(ctx.guild.id)]
    result = collection.delete_one({'_id': command})
    
    if result.deleted_count == 0:
        await ctx.send(f"ERROR: Could not remove, Command '!{command}' not found. On the bright side, you wanted to remove it anyways, right?")
    else:
        await ctx.send(f"SUCCESS: Command '!{command}' has been removed")

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

@bot.command(name="commands", aliases=["help"])
async def get_cmds(ctx):
    """List all available commands"""
    header = f"{ctx.guild.name} commands:"
    init_msg = await ctx.send(header)
    
    # Get built-in commands
    built_in_commands = "Built-in commands:\n"
    built_in_commands += "!add <command> <response> - Add a new command\n"
    built_in_commands += "!remove <command> - Remove a command\n"
    built_in_commands += "!changegame <game> - Change bot's playing status\n"
    built_in_commands += "!changenick <nickname> - Change bot's nickname\n"
    built_in_commands += "!commands or !help - Show this help message\n\n"
    built_in_commands += "Custom commands:"
    
    await ctx.send(built_in_commands)
    
    # Get custom commands from database
    collection = db[str(ctx.guild.id)]
    commands = collection.find().batch_size(10).sort('_id', 1)
    temp = ""

    for command in commands:
        line = f"!{command['_id']}\n"
        if len(temp + line) > MAX_MESSAGE_LEN:
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
    """Run the bot with auto-restart on errors"""
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