"""Main entry point for Discord Pasta Bot"""
import asyncio
import logging
import sys
import random
import signal
import atexit

import discord

from keepalive import KeepAliveServer
from src.bot import PastaBot
from config import Config
from src.utils.session import (
    close_all_sessions, 
    register_session_cleanup,
)
from src.utils.log_util import format_http_exception, header_value

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Global variables for cleanup
keepalive_server = None
bot = None

async def graceful_shutdown(sig=None):
    """Handle graceful shutdown"""
    if sig:
        logger.info(f"Received shutdown signal: {sig.name}")
    
    logger.info("Initiating graceful shutdown...")
    
    global bot, keepalive_server
    
    # Shutdown sequence
    tasks = []
    
    # 1. Stop the keepalive server
    if keepalive_server and keepalive_server.is_running:
        logger.info("Stopping keepalive server...")
        keepalive_server.stop()
    
    # 2. Close the bot if it exists
    if bot:
        logger.info("Closing bot...")
        try:
            await bot.close()
        except Exception as e:
            logger.error(f"Error closing bot: {e}")
    
    # 3. Close all remaining HTTP sessions
    logger.info("Closing all HTTP sessions...")
    await close_all_sessions()
    
    logger.info("Shutdown complete")

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    # Signal handlers are not supported on Windows with add_signal_handler
    # So we skip this on Windows
    if sys.platform == 'win32':
        logger.debug("Signal handlers not available on Windows, skipping")
        return
    
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(graceful_shutdown(s))
        )

async def run_bot(config_obj):
    """Run the bot with keepalive server and auto-restart"""
    global keepalive_server, bot
    
    # Initialize keepalive server
    keepalive_server = KeepAliveServer()
    keepalive_server.start()
    
    # Create the bot instance
    bot = PastaBot(config_obj)
    
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            # Run the bot
            await bot.run_bot()
            # If we get here, the bot disconnected normally, reset retry count
            retry_count = 0
            
        except ValueError as e:
            # Configuration errors
            logger.critical(f"Configuration error: {e}")
            await graceful_shutdown()
            sys.exit(1)
            
        except discord.errors.LoginFailure:
            logger.critical("Invalid token. Please check your BOT_TOKEN environment variable.")
            await graceful_shutdown()
            sys.exit(1)
            
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited (typically a global/CF IP block when raised here)
                retry_count += 1
                # Calculate backoff time: exponential with jitter
                backoff_time = min(300, (2 ** retry_count) + (random.randint(0, 1000) / 1000))
                # Honor the server-supplied Retry-After if it's longer than our backoff,
                # so we don't re-enter before the block has genuinely expired.
                response = getattr(e, "response", None)
                headers = getattr(response, "headers", None) if response is not None else None
                retry_after_header = header_value(headers, "retry-after")
                if retry_after_header is not None:
                    try:
                        server_backoff = float(retry_after_header)
                        backoff_time = max(backoff_time, server_backoff)
                    except ValueError:
                        # Some endpoints return an HTTP-date; we just keep our own
                        # backoff and surface the raw header for diagnosis.
                        pass
                logger.warning(
                    f"Rate limited at run_bot level (attempt {retry_count}/{max_retries}). "
                    f"Backoff {backoff_time:.2f}s (retry-after header: {retry_after_header}). "
                    f"Details:\n  {format_http_exception(e, context={'attempt': retry_count})}"
                )
                # Clean up before waiting
                if bot:
                    await bot.close()
                # Wait before retry
                await asyncio.sleep(backoff_time)
                # Create a fresh bot instance
                bot = PastaBot(config_obj)
            else:
                logger.error(f"HTTP Error: {e}")
                retry_count += 1
                # Clean up
                if bot:
                    await bot.close()
                await asyncio.sleep(60)  # Wait a minute before retry for other HTTP errors
                # Create a fresh bot instance
                bot = PastaBot(config_obj)
                
        except Exception as e:
            logger.error(f"Error: {e}")
            retry_count += 1
            # Exponential backoff with jitter
            backoff_time = min(300, (2 ** retry_count) + (random.randint(0, 1000) / 1000))
            logger.info(f"Restarting in {backoff_time:.2f} seconds... (attempt {retry_count}/{max_retries})")
            # Clean up
            if bot:
                await bot.close()
            await asyncio.sleep(backoff_time)
            # Create a fresh bot instance  
            bot = PastaBot(config_obj)
    
    logger.critical(f"Maximum retry attempts ({max_retries}) reached. Exiting.")
    await graceful_shutdown()
    sys.exit(1)

async def main():
    """Main entry point with proper async setup and teardown"""
    # Register session cleanup handlers
    register_session_cleanup()
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Register cleanup function for normal exit
    atexit.register(lambda: asyncio.run(graceful_shutdown()))
    
    # Load configuration
    config = Config()
    
    try:
        # Run the bot with proper session management
        await run_bot(config)
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}")
        await graceful_shutdown()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())