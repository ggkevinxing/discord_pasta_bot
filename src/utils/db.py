"""Database utility for MongoDB operations"""
import logging
from pymongo import MongoClient

logger = logging.getLogger("bot.database")

class Database:
    """MongoDB database wrapper for the bot"""

    def __init__(self, uri):
        """Initialize database connection"""
        self.client = None
        self.db = None

        try:
            logger.info("Connecting to database")
            self.client = MongoClient(uri)
            self.db = self.client['Morton']
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_collection(self, guild_id):
        """Get collection for a specific guild"""
        return self.db[str(guild_id)]

    def add_command(self, guild_id, command, content):
        """Add or update a custom command"""
        collection = self.get_collection(guild_id)
        document = {'_id': command, 'content': content}
        result = collection.update_one({'_id': command}, {'$set': document}, upsert=True)
        return result.upserted_id is not None

    def remove_command(self, guild_id, command):
        """Remove a custom command"""
        collection = self.get_collection(guild_id)
        result = collection.delete_one({'_id': command})
        return result.deleted_count > 0

    def get_command(self, guild_id, command):
        """Get a command's content"""
        collection = self.get_collection(guild_id)
        return collection.find_one({'_id': command})

    def get_all_commands(self, guild_id):
        """Get all custom commands for a guild"""
        collection = self.get_collection(guild_id)
        return collection.find().sort('_id', 1)

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
