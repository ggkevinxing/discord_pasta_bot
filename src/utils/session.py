"""HTTP Session utilities for the bot"""
import logging
import aiohttp
import asyncio
import discord
import weakref
import sys
import warnings

logger = logging.getLogger("bot.utils.session")

# Keep track of all sessions to ensure they get closed
_active_sessions = weakref.WeakSet()

def get_configured_connector():
    """
    Creates an aiohttp TCPConnector with optimal configuration for Discord API
    
    This helps avoid rate limiting by configuring proper TCP connection limits
    and other settings appropriate for Discord's API.
    
    Returns:
        aiohttp.TCPConnector: A properly configured connector
    """
    # Setting connector with proper limits helps avoid rate limits
    connector = aiohttp.TCPConnector(
        limit=50,  # Overall connection limit
        limit_per_host=5,  # Limit per host to avoid hammering Discord API
        force_close=True,  # Close connections after use
        enable_cleanup_closed=True  # Clean up closed connections
    )
    
    return connector

def get_configured_client_session():
    """
    Creates an aiohttp ClientSession with optimal configuration for Discord API
    
    This helps avoid rate limiting by configuring proper TCP connection limits
    and other settings appropriate for Discord's API.
    
    Returns:
        aiohttp.ClientSession: A properly configured session
    """
    connector = get_configured_connector()
    
    # Configure timeout
    timeout = aiohttp.ClientTimeout(
        total=120,  # 2 minutes total timeout
        connect=10,  # 10 seconds connection timeout
        sock_connect=10,  # 10 seconds to establish connection
        sock_read=30  # 30 seconds to read response
    )
    
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        trust_env=True  # Allow environment variables to configure proxy
    )
    
    # Keep track of this session for cleanup
    _active_sessions.add(session)
    
    return session


async def close_all_sessions():
    """
    Close all active sessions.
    Call this before shutdown to prevent resource leaks.
    """
    if not _active_sessions:
        return
        
    logger.info(f"Closing {len(_active_sessions)} active HTTP sessions")
    
    close_tasks = []
    for session in list(_active_sessions):
        if not session.closed:
            close_tasks.append(session.close())
    
    if close_tasks:
        await asyncio.gather(*close_tasks, return_exceptions=True)
    _active_sessions.clear()

# Register cleanup handlers for unclosed sessions
def register_session_cleanup():
    """
    Register cleanup handlers to ensure sessions are closed on exit
    """
    original_loop_close = asyncio.AbstractEventLoop.close
    
    def patched_loop_close(self, *args, **kwargs):
        """Close any unclosed sessions before closing the loop"""
        try:
            # Get all unclosed sessions and close them
            for session in list(_active_sessions):
                if not session.closed:
                    logger.warning(f"Unclosed session detected during shutdown: {session}")
                    if not self.is_closed():
                        self.create_task(session.close())
                    else:
                        warnings.warn(f"Loop closed, couldn't close session properly: {session}")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
        finally:
            return original_loop_close(self, *args, **kwargs)
    
    # Apply the patch
    asyncio.AbstractEventLoop.close = patched_loop_close
    
    # Also set up a shutdown handler
    try:
        import atexit
        
        def atexit_cleanup():
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(close_all_sessions())
        
        atexit.register(atexit_cleanup)
    except Exception as e:
        logger.error(f"Could not register atexit handler: {e}")