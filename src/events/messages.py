"""Message event handlers and easter eggs"""
import logging
import asyncio
import discord

logger = logging.getLogger("bot.events.messages")

class MessageEvents:
    """Message event handlers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = bot.cooldowns
        self.config = bot.config
        
        # Register event handlers
        self.bot.event(self.on_message)
    
    async def on_message(self, message):
        """Process messages for easter eggs and command handling"""
        # Ignore messages from bots and DMs
        if message.author.bot or message.guild is None:
            if message.author != self.bot.user and message.guild is None:
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
            if not self.cooldowns.get("avengers-iw", False):
                await self.post_txt("avengers-iw", message.author)
            else:
                await message.channel.send(
                    "Anti-Avengers Initiative is on cooldown. I'm probably still posting it to someone right now. "
                    "Enjoy your freedom while you can!"
                )

        # Process commands
        await self.bot.process_commands(message)
    
    async def post_txt(self, textfilename, user):
        """Post the contents of a text file to the channel"""
        # Set cooldown
        self.cooldowns[textfilename] = True

        file = f"assets/{textfilename}.txt"
        message = ""

        try:
            with open(file, "rb") as f:
                for l in f:
                    line = l.decode(errors='ignore')
                    # Respect Discord's message length limit
                    if len(message + line) > self.config.max_message_len:
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
        self.cooldowns[textfilename] = False

def setup(bot):
    """Set up message event handlers"""
    MessageEvents(bot)
    logger.info("Message events handlers loaded")