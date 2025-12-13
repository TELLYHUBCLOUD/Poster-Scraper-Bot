# ruff: noqa: E402

from datetime import datetime
from logging import Formatter
from asyncio import gather

from pytz import timezone
from pyrogram import idle

from config import Config
from . import LOGGER, bot_loop
from .core.EchoClient import EchoClient
from .core.plugs import add_plugs
from .helper.utils.db import database
from .helper.utils.bot_cmds import _get_bot_commands


async def main():
    await database._load_all()

    def changetz(*args):
        return datetime.now(timezone(Config.TIMEZONE)).timetuple()

    Formatter.converter = changetz

    await gather(
        EchoClient.start_bot(),
    )

    await EchoClient.bot.set_bot_commands(_get_bot_commands())

    add_plugs()

    LOGGER.info("Echo Bot fully started")

    await idle()

    await EchoClient.stop()


bot_loop.run_until_complete(main())
bot_loop.run_forever()
