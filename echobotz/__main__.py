import os
import asyncio
from datetime import datetime
from logging import Formatter

from pytz import timezone as tz
from pyrogram import idle

from config import Config
from . import LOGGER
from .core.EchoClient import EchoBot
from .core.plugs import add_plugs
from .helper.utils.db import database
from .helper.utils.bot_cmds import _get_bot_commands
try:
    from web import _start_web, _ping
    WEB_OK = True
except ImportError:
    WEB_OK = False


def main():
    def changetz(*args):
        return datetime.now(tz(Config.TIMEZONE)).timetuple()

    Formatter.converter = changetz

    loop = asyncio.get_event_loop()
    loop.run_until_complete(database._load_all())

    EchoBot.start()
    EchoBot.set_bot_commands(_get_bot_commands())
    LOGGER.info("Bot Cmds Set Successfully")
    me = EchoBot.get_me()
    LOGGER.info(f"Bot Started as: @{me.username}")

    if os.path.isfile(".restartmsg"):
        try:
            with open(".restartmsg") as f:
                chat_id, msg_id = map(int, f.read().splitlines())

            now = datetime.now(tz(Config.TIMEZONE)).strftime(
                "%d/%m/%Y %I:%M:%S %p"
            )

            EchoBot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"<b>Restarted Successfully!</b>\n<code>{now}</code>",
                disable_web_page_preview=True,
            )

            os.remove(".restartmsg")
        except Exception as e:
            LOGGER.error(f"Restart notify error: {e}")

    add_plugs()
    
    if Config.WEB_SERVER and WEB_OK:
        LOGGER.info("Starting web server...")
        asyncio.create_task(_start_web())
        asyncio.create_task(_ping(Config.PING_URL, Config.PING_TIME))
    else:
        LOGGER.info("Web server disabled")
    
    idle()

    EchoBot.stop()
    LOGGER.info("Echo Client stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        LOGGER.error(f"Error deploying: {e}")
        try:
            EchoBot.stop()
        except Exception:
            pass
