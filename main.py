import asyncio
import logging
import sys

from aiohttp import web
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
    cmd_web,
    cmd_img_gen,
    cmd_img_edit,
)
from handlers.messages import handle_message

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


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
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("reset",   cmd_reset))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("deep",    cmd_deep))
    app.add_handler(CommandHandler("duck",    cmd_duck))
    app.add_handler(CommandHandler("mode",    cmd_mode))
    app.add_handler(CommandHandler("web",     cmd_web))
    app.add_handler(CommandHandler("img_gen", cmd_img_gen))
    app.add_handler(CommandHandler("img_edit",cmd_img_edit))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
            handle_message,
        )
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("MultiGPT AI is running — press Ctrl+C to stop")

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
