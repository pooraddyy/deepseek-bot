import asyncio
import concurrent.futures
import logging
import sys

from aiohttp import web
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, PORT
from handlers.callbacks import handle_callback
from handlers.commands import (
    cmd_start,
    cmd_reset,
    cmd_status,
    cmd_deep,
    cmd_duck,
    cmd_mode,
    cmd_search,
    cmd_web,
    cmd_imggen,
    cmd_imgedit,
)
from handlers.messages import handle_message

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start",   "Start the bot / show help"),
    BotCommand("deep",    "Switch to a DeepSeek model"),
    BotCommand("duck",    "Switch to a DuckDuckGo AI model"),
    BotCommand("imggen",  "Generate an image from a prompt"),
    BotCommand("imgedit", "Edit a photo with a caption"),
    BotCommand("web",     "Force a one-off web search"),
    BotCommand("search",  "Toggle web search on / off"),
    BotCommand("mode",    "Switch Fast / Reasoning mode"),
    BotCommand("status",  "Show current model and settings"),
    BotCommand("reset",   "Clear the current conversation"),
    BotCommand("help",    "Show help message"),
]


async def _health(_request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info("Health server listening on port %d", PORT)


async def start_bot() -> None:
    loop = asyncio.get_running_loop()
    loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=32))

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("reset",   cmd_reset))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("deep",    cmd_deep))
    app.add_handler(CommandHandler("duck",    cmd_duck))
    app.add_handler(CommandHandler("mode",    cmd_mode))
    app.add_handler(CommandHandler("search",  cmd_search))
    app.add_handler(CommandHandler("web",     cmd_web))
    app.add_handler(CommandHandler("imggen",  cmd_imggen))
    app.add_handler(CommandHandler("imgedit", cmd_imgedit))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
            handle_message,
        )
    )

    await app.initialize()
    await app.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot commands registered (%d commands)", len(BOT_COMMANDS))

    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("MultiGPT AI is running")

    try:
        await asyncio.Event().wait()
    finally:
        logger.info("Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def main() -> None:
    await asyncio.gather(start_health_server(), start_bot())


if __name__ == "__main__":
    asyncio.run(main())
