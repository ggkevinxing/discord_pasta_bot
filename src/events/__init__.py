"""Event handlers for the Discord Pasta Bot"""
from src.events.ready import setup as setup_ready
from src.events.messages import setup as setup_messages
from src.events.command_error import setup as setup_command_error

# You can provide direct imports or a setup function
def setup(bot):
    """Register all event handlers"""
    setup_ready(bot)
    setup_messages(bot)
    setup_command_error(bot)