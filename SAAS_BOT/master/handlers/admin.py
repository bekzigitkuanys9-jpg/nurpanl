from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy import select
from ..database.saas_engine import saas_session
from ..database.saas_models import SaasClient, SaasPayment
from ..bot_runner import start_client_bot, stop_client_bot, active_client_bots
from config import config

router = Router()


def is_master_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


# ─── Approve payment ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("saas_approve_"))
async def approve_client(callback: CallbackQuery, bot: Bot):
    if not is_master_admin(callback.from_user.id):
        await callback.answer("⛔ No access!", show_alert=True)
        return

    _, _, payment_id, client_tg_id = callback.data.split("_", 3)
    payment_id, client_tg_id = int(payment_id), int(client_tg_id)

    async with saas_session() as session:
        payment = await session.scalar(select(SaasPayment).where(SaasPayment.id == payment_id))
        client = await session.scalar(select(SaasClient).where(SaasClient.tg_id == client_tg_id))

        if not payment or not client:
            await callback.answer("Not found.", show_alert=True)
            return
        if payment.status != "pending":
            await callback.answer(f"Already processed: {payment.status}", show_alert=True)
            return

        payment.status = "approved"
        client.is_active = True
        client.state = "active"
        client.expires_at = datetime.utcnow() + timedelta(days=30)
        await session.commit()

    # Start client bot
    await start_client_bot(client)

    # Update admin message
    new_cap = (callback.message.caption or "") + f"\n\n✅ <b>APPROVED</b> — @{callback.from_user.username}"
    try:
        await callback.message.edit_caption(caption=new_cap, reply_markup=None, parse_mode="HTML")
    except Exception:
        pass

    # Notify client
    try:
        await bot.send_message(
            chat_id=client_tg_id,
            text=(
                f"✅ <b>Your bot is now active!</b>\n\n"
                f"🤖 @{client.bot_username}\n"
                f"📅 Valid until: <b>{client.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
                f"Open your bot and send /start to access your admin panel!\n"
                f"Your Telegram ID is your admin ID: <code>{client_tg_id}</code>"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("✅ Approved!")


# ─── Reject payment ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("saas_reject_"))
async def reject_client(callback: CallbackQuery, bot: Bot):
    if not is_master_admin(callback.from_user.id):
        await callback.answer("⛔ No access!", show_alert=True)
        return

    _, _, payment_id, client_tg_id = callback.data.split("_", 3)
    payment_id, client_tg_id = int(payment_id), int(client_tg_id)

    async with saas_session() as session:
        payment = await session.scalar(select(SaasPayment).where(SaasPayment.id == payment_id))
        if not payment or payment.status != "pending":
            await callback.answer("Already processed.", show_alert=True)
            return
        payment.status = "rejected"
        await session.commit()

    new_cap = (callback.message.caption or "") + f"\n\n❌ <b>REJECTED</b> — @{callback.from_user.username}"
    try:
        await callback.message.edit_caption(caption=new_cap, reply_markup=None, parse_mode="HTML")
    except Exception:
        pass

    try:
        await bot.send_message(
            chat_id=client_tg_id,
            text="❌ <b>Payment rejected.</b>\n\nPlease contact support: @nurdapanel",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("❌ Rejected.")


# ─── Admin /clients command ───────────────────────────────────────
@router.message(Command("clients"))
async def list_clients(message: Message):
    if not is_master_admin(message.from_user.id):
        return

    async with saas_session() as session:
        clients = (await session.execute(select(SaasClient))).scalars().all()

    if not clients:
        await message.answer("No clients yet.")
        return

    text = "📋 <b>ALL CLIENTS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for c in clients:
        status = "✅" if c.is_active else "❌"
        exp = c.expires_at.strftime('%d.%m.%Y') if c.expires_at else "—"
        running = "🟢" if c.tg_id in active_client_bots else "🔴"
        text += (
            f"{status}{running} @{c.bot_username or '?'}\n"
            f"   👤 tg_id: <code>{c.tg_id}</code>\n"
            f"   📅 Expires: {exp}\n\n"
        )

    await message.answer(text, parse_mode="HTML")


# ─── Admin /suspend command ───────────────────────────────────────
@router.message(Command("suspend"))
async def suspend_client_cmd(message: Message):
    if not is_master_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Usage: /suspend <tg_id>")
        return

    client_tg_id = int(parts[1])
    async with saas_session() as session:
        client = await session.scalar(select(SaasClient).where(SaasClient.tg_id == client_tg_id))
        if not client:
            await message.answer("Client not found.")
            return
        client.is_active = False
        await session.commit()

    await stop_client_bot(client_tg_id)
    await message.answer(f"✅ Bot @{client.bot_username} has been suspended.")
