"""Configuration management for the bot"""
import os
from dotenv import load_dotenv

class Config:
    """Configuration class to centralize all settings"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Bot settings
        self.token = os.environ.get("BOT_TOKEN")
        self.db_uri = os.environ.get("DATABASE_URI")
        self.nickname = os.environ.get("BOT_NICKNAME")
        self.game = os.environ.get("BOT_GAME")
        self.cmd_prefix = os.environ.get("CMD_PREFIX", default="!")
        self.local_tz = os.environ.get("LOCAL_TZ", default="America/New_York")

        # Discord limitations
        self.max_message_len = os.environ.get("MAX_MESSAGE_LEN", default=2000)

        # Validate critical settings
        if not self.token:
            raise ValueError("BOT_TOKEN environment variable is not set")
        if not self.db_uri:
            raise ValueError("DATABASE_URI environment variable is not set")
