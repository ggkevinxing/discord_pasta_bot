"""Main entry point for Discord Pasta Bot"""
import asyncio
import logging
import time
import sys

import discord

from keepalive import KeepAliveServer
from src.bot import PastaBot
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

config = Config()
bot = PastaBot(config)

async def run_bot(b):
    """Run the bot with keepalive server and auto-restart"""
    # Initialize keepalive server
    keepalive = KeepAliveServer()
    keepalive.start()
    
    while True:
        try:
            # Run the bot
            await b.run_bot()
        except ValueError as e:
            # Configuration errors
            logger.critical(f"Configuration error: {e}")
            sys.exit(1)
            
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
            
        finally:
            # Clean up resources
            if bot:
                bot.close()

if __name__ == "__main__":
    asyncio.run(run_bot(bot))