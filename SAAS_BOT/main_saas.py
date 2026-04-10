import asyncio
import logging
import os
import sys

# Add PAY APP BOT root to Python path
BOT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BOT_ROOT)

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from sqlalchemy import select

from config import config
from database.saas_engine import create_saas_db, saas_session
from database.saas_models import SaasClient
from bot_runner import start_client_bot
from expiry_checker import expiry_checker
from master.handlers import registration, admin as admin_handler


async def health_check(request):
    from bot_runner import active_client_bots
    return web.Response(
        text=f"OK | Active bots: {len(active_client_bots)}",
        status=200
    )


async def keep_alive(url: str):
    import aiohttp
    while True:
        await asyncio.sleep(14 * 60)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/healthz") as resp:
                    logging.info(f"Keep-alive ping: {resp.status}")
        except Exception as e:
            logging.error(f"Keep-alive failed: {e}")


async def on_startup(bot: Bot):
    actual_url = os.environ.get("RENDER_EXTERNAL_URL") or config.webhook_url
    if config.use_webhook and actual_url:
        await bot.set_webhook(
            f"{actual_url}{config.webhook_path}",
            drop_pending_updates=True
        )
        logging.info(f"Master bot webhook: {actual_url}{config.webhook_path}")

    asyncio.create_task(keep_alive(actual_url or ""))

    # Restore all active client bots
    async with saas_session() as session:
        active_clients = (await session.execute(
            select(SaasClient).where(SaasClient.is_active == True)
        )).scalars().all()

    for client in active_clients:
        await start_client_bot(client)
        logging.info(f"[SaaS] Restored client bot @{client.bot_username}")

    # Start expiry checker
    asyncio.create_task(expiry_checker(bot))
    logging.info(f"[SaaS] Expiry checker started. {len(active_clients)} client bots restored.")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)


async def main():
    logging.basicConfig(level=logging.INFO)

    # Init SaaS database
    await create_saas_db()

    # Master bot
    bot = Bot(token=config.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Register master bot handlers
    dp.include_router(registration.router)
    dp.include_router(admin_handler.router)

    if config.use_webhook:
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.webhook_path)
        app.router.add_get("/", health_check)
        app.router.add_get("/healthz", health_check)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=config.webapp_host, port=config.webapp_port)
        logging.info(f"Master bot starting on port {config.webapp_port}...")
        await site.start()
        await asyncio.Event().wait()
    else:
        logging.info("Master bot starting in polling mode...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("SaaS Master Bot stopped.")
