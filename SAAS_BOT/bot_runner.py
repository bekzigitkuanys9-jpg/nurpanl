import asyncio
import logging
import sys
import os

# Add parent directory to path so we can import PAY APP BOT modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database.engine import create_db, async_session
from database.models import User, Product, Key, Purchase, Payment
from database.github_sync import save_database
from config import config as client_config_class

from handlers import common, user, payment
from handlers import vip
from handlers.admin import panel, moderation, keys, users, products, vip_admin, broadcast
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.auth import AuthMiddleware

# Registry of running client bots: {client_tg_id: asyncio.Task}
active_client_bots: dict = {}


async def build_client_dispatcher(client) -> tuple[Bot, Dispatcher]:
    """Build a fully configured Bot + Dispatcher for a client."""
    bot = Bot(token=client.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Inject client-specific config into middlewares via closure
    class ClientAuthMiddleware(AuthMiddleware):
        pass

    dp.message.middleware(RateLimitMiddleware(limit=1))
    dp.message.middleware(ClientAuthMiddleware())
    dp.callback_query.middleware(ClientAuthMiddleware())

    # Register all standard handlers
    dp.include_router(vip.router)
    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(payment.router)
    dp.include_router(panel.router)
    dp.include_router(moderation.router)
    dp.include_router(keys.router)
    dp.include_router(users.router)
    dp.include_router(products.router)
    dp.include_router(vip_admin.router)
    dp.include_router(broadcast.router)

    return bot, dp


async def run_client_bot(client):
    """Poll a single client bot until cancelled."""
    try:
        # Set up a separate DB for this client
        client_db_url = f"sqlite+aiosqlite:///client_{client.tg_id}.db"

        # Temporarily override config values for this bot instance
        client_config_class.kaspi_phone = client.kaspi_phone or ""
        client_config_class.kaspi_receiver = client.kaspi_receiver or ""
        client_config_class.admin_ids = [client.tg_id]

        bot, dp = await build_client_dispatcher(client)
        await bot.delete_webhook(drop_pending_updates=False)
        logging.info(f"[SaaS] Client bot @{client.bot_username} started polling.")
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except asyncio.CancelledError:
        logging.info(f"[SaaS] Client bot @{client.bot_username} stopped.")
        raise
    except Exception as e:
        logging.error(f"[SaaS] Client bot @{client.bot_username} error: {e}")


async def start_client_bot(client):
    """Start a client bot as a background asyncio task."""
    if client.tg_id in active_client_bots:
        logging.info(f"[SaaS] Bot @{client.bot_username} already running.")
        return

    task = asyncio.create_task(run_client_bot(client))
    active_client_bots[client.tg_id] = task
    logging.info(f"[SaaS] Started bot @{client.bot_username} (client {client.tg_id})")


async def stop_client_bot(client_tg_id: int):
    """Cancel and remove a client bot task."""
    task = active_client_bots.pop(client_tg_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logging.info(f"[SaaS] Stopped bot for client {client_tg_id}")
