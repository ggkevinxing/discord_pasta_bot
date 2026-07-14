"""Message event handlers and easter eggs"""
import asyncio
import logging
import time
from pathlib import Path

logger = logging.getLogger("bot.events.messages")

# Where easter-egg text files are read from, resolved from this file's
# location so it works regardless of CWD.
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


def _asset_path(filename: str) -> Path:
    """Resolve a filename under the project's assets/ directory."""
    return ASSETS_DIR / filename


# Easter-egg registry. Each entry is keyed by a stable name (used as the
# cooldown slot in bot.cooldowns) and declares:
#   - triggers:        message prefixes that activate this egg
#   - asset:           filename under ASSETS_DIR that gets DMed to the triggerer
#   - cooldown:        seconds during which repeat triggers are rejected
#   - cooldown_message: text sent to the channel when a trigger fires while on cooldown
EASTER_EGGS = {
    "avengers-iw": {
        "triggers": [
            "In time you will know what it's like to lose.",
            "In Time",
            "Destiny still arrives.",
            "Fun isn't something one considers from balancing the universe.",
            "In",
            "Fun",
        ],
        "asset": "avengers-iw.txt",
        "cooldown": 300,
        "cooldown_message": (
            "Anti-Avengers Initiative is on cooldown. I'm probably still posting it to someone right now. "
            "Enjoy your freedom while you can!"
        ),
    },
}


class MessageEvents:
    """Message event handlers"""

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = bot.cooldowns
        self.config = bot.config

        # Strong references for fire-and-forget tasks so the GC doesn't drop
        # them mid-DM-stream. Tasks remove themselves when done.
        self._background_tasks: set[asyncio.Task] = set()

        # Register event handlers
        self.bot.event(self.on_message)

    async def on_message(self, message):
        """Process messages for easter eggs and command handling."""
        # Ignore our own messages (always short-circuit)
        if message.author == self.bot.user:
            return

        # Reject DMs with a clear explanation
        if message.guild is None:
            await message.channel.send(
                "ERROR: I don't currently have support for any commands in private messages. Sorry!"
            )
            return

        # Ignore other bots in guilds
        if message.author.bot:
            return

        logger.info(
            f"{message.guild.name} | {message.channel.name} | {message.author.name}: {message.content}"
        )

        # Easter eggs — at most one fires per message
        for name, egg in EASTER_EGGS.items():
            if not any(message.content.startswith(trigger) for trigger in egg["triggers"]):
                continue
            if self._is_on_cooldown(name):
                await message.channel.send(egg["cooldown_message"])
            else:
                # Set the cooldown timestamp synchronously (no await between
                # the check and the assignment) so a second trigger that
                # arrives before the spawned task starts running still sees
                # the cooldown as active and gets the "on cooldown" reply.
                self.cooldowns[name] = time.monotonic() + egg["cooldown"]
                # Detached task so the DM stream does not block process_commands
                self._spawn(self._send_text_file(message.author.send, _asset_path(egg["asset"])))
            break

        await self.bot.process_commands(message)

    def _spawn(self, coro) -> None:
        """Schedule a coroutine as a tracked fire-and-forget task."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _is_on_cooldown(self, name: str) -> bool:
        """Return True if the named egg's cooldown is still active.

        Cooldowns are stored as monotonic-clock expiry timestamps in
        ``bot.cooldowns``. A missing key (treated as 0.0) means no cooldown.
        """
        expiry = self.cooldowns.get(name, 0.0)
        return expiry > time.monotonic()

    async def _send_text_file(self, send, path: Path) -> None:
        """Stream the contents of ``path`` via ``send`` in chunks ≤ max_message_len."""
        buffer = ""
        try:
            with open(path, "rb") as f:
                for raw in f:
                    line = raw.decode(errors="ignore")
                    if len(buffer + line) > self.config.max_message_len:
                        await send(buffer)
                        buffer = ""
                    if line.strip():
                        buffer += line
                if buffer:
                    await send(buffer)
        except FileNotFoundError:
            logger.error(f"Text file not found: {path}")
        except Exception as e:
            logger.error(f"Error posting text file: {e}")


def setup(bot):
    """Set up message event handlers"""
    MessageEvents(bot)
    logger.info("Message events handlers loaded")