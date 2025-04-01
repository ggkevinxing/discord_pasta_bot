"""Main entry point for Discord Pasta Bot"""
import asyncio
import logging
import random
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
    
    retry_count = 0
    max_retries = 20
    
    while retry_count < max_retries:
        try:
            # Run the bot
            await b.run_bot()
            # If we get here, the bot disconnected normally, reset retry count
            retry_count = 0
            
        except ValueError as e:
            # Configuration errors
            logger.critical(f"Configuration error: {e}")
            sys.exit(1)
            
        except discord.errors.LoginFailure:
            logger.critical("Invalid token. Please check your BOT_TOKEN environment variable.")
            sys.exit(1)
            
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_count += 1
                # Calculate backoff time: exponential with jitter
                backoff_time = min(300, (2 ** retry_count) + (random.randint(0, 1000) / 1000))
                logger.warning(f"Rate limited (attempt {retry_count}/{max_retries}). Retrying in {backoff_time:.2f} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"HTTP Error: {e}")
                retry_count += 1
                await asyncio.sleep(60)  # Wait a minute before retry for other HTTP errors
                
        except Exception as e:
            logger.error(f"Error: {e}")
            retry_count += 1
            # Exponential backoff with jitter
            backoff_time = min(300, (2 ** retry_count) + (random.randint(0, 1000) / 1000))
            logger.info(f"Restarting in {backoff_time:.2f} seconds... (attempt {retry_count}/{max_retries})")
            await asyncio.sleep(backoff_time)
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down.")
            sys.exit(0)
            
        finally:
            # Clean up resources
            if bot:
                bot.close()
    
    logger.critical(f"Maximum retry attempts ({max_retries}) reached. Exiting.")
    sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_bot(bot))