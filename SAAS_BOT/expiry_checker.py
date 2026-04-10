import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from .database.saas_engine import saas_session
from .database.saas_models import SaasClient
from .bot_runner import stop_client_bot, active_client_bots


async def expiry_checker(master_bot):
    """Background task that runs every hour and suspends expired bots."""
    while True:
        await asyncio.sleep(60 * 60)  # check every hour
        try:
            async with saas_session() as session:
                expired = (await session.execute(
                    select(SaasClient).where(
                        SaasClient.is_active == True,
                        SaasClient.expires_at <= datetime.utcnow()
                    )
                )).scalars().all()

                for client in expired:
                    client.is_active = False
                    await session.commit()
                    await stop_client_bot(client.tg_id)
                    logging.info(f"[SaaS] Bot @{client.bot_username} expired and stopped.")

                    # Notify client
                    try:
                        await master_bot.send_message(
                            chat_id=client.tg_id,
                            text=(
                                "⏰ <b>Your bot subscription has expired!</b>\n\n"
                                f"Bot @{client.bot_username} has been stopped.\n\n"
                                "To renew, send /start and purchase again. 🔄"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

        except Exception as e:
            logging.error(f"[SaaS] Expiry checker error: {e}")
