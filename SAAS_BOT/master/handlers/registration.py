import re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from sqlalchemy import select
from ..database.saas_engine import saas_session
from ..database.saas_models import SaasClient, SaasPayment
from ..master.keyboards import master_main_keyboard, share_contact_keyboard, master_approve_keyboard
from config import config

router = Router()

SUBSCRIPTION_PRICE = 5000
MASTER_KASPI_PHONE = config.kaspi_phone
MASTER_KASPI_RECEIVER = config.kaspi_receiver


# ─── /start ────────────────────────────────────────────────────────
@router.message(CommandStart())
async def master_start(message: Message):
    async with saas_session() as session:
        client = await session.scalar(
            select(SaasClient).where(SaasClient.tg_id == message.from_user.id)
        )
        if not client:
            client = SaasClient(
                tg_id=message.from_user.id,
                username=message.from_user.username,
                state="start"
            )
            session.add(client)
            await session.commit()

    await message.answer(
        "🤖 <b>Welcome to Bot Builder!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Get your own <b>Reseller Bot</b> for only "
        f"<b>{SUBSCRIPTION_PRICE:,} ₸/month</b>\n\n"
        "Your bot will have:\n"
        "✅ Product & key management\n"
        "✅ Kaspi payment system\n"
        "✅ Admin panel\n"
        "✅ User management\n\n"
        "Press <b>Buy Bot Subscription</b> to start! 👇",
        parse_mode="HTML",
        reply_markup=master_main_keyboard()
    )


# ─── Buy subscription ──────────────────────────────────────────────
@router.callback_query(F.data == "saas_buy")
async def start_registration(callback: CallbackQuery):
    async with saas_session() as session:
        client = await session.scalar(
            select(SaasClient).where(SaasClient.tg_id == callback.from_user.id)
        )
        if client and client.is_active:
            await callback.answer("✅ Your bot is already active!", show_alert=True)
            return

        if not client:
            client = SaasClient(tg_id=callback.from_user.id, username=callback.from_user.username)
            session.add(client)

        client.state = "awaiting_token"
        await session.commit()

    await callback.message.edit_text(
        "🔑 <b>Step 1/3 — Bot Token</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. Open <a href='https://t.me/BotFather'>@BotFather</a>\n"
        "2. Send /newbot and follow the steps\n"
        "3. Copy your <b>BOT_TOKEN</b> and send it here:\n\n"
        "<i>(Example: 123456789:AAEb4dYa9IrEY6rnPX6QXQ...)</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


# ─── Receive bot token ─────────────────────────────────────────────
@router.message(F.text)
async def handle_text_input(message: Message, bot: Bot):
    async with saas_session() as session:
        client = await session.scalar(
            select(SaasClient).where(SaasClient.tg_id == message.from_user.id)
        )
        if not client:
            return

        # --- State: awaiting_token ---
        if client.state == "awaiting_token":
            token = message.text.strip()
            # validate token format
            if not re.match(r'^\d+:[A-Za-z0-9_-]{35,}$', token):
                await message.answer("❌ Invalid token format. Please send a valid BotFather token.")
                return
            # validate token by calling getMe
            try:
                test_bot = Bot(token=token)
                me = await test_bot.get_me()
                await test_bot.session.close()
            except Exception:
                await message.answer("❌ Token is invalid or bot does not exist. Try again.")
                return

            client.bot_token = token
            client.bot_username = me.username
            client.state = "awaiting_kaspi_phone"
            await session.commit()

            await message.answer(
                f"✅ Bot validated: <b>@{me.username}</b>\n\n"
                "📞 <b>Step 2/3 — Your Kaspi Number</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Send your <b>Kaspi phone number</b> that your customers will pay to:\n"
                "<i>(Example: +77012345678)</i>",
                parse_mode="HTML"
            )

        # --- State: awaiting_kaspi_phone ---
        elif client.state == "awaiting_kaspi_phone":
            phone = message.text.strip()
            if not phone.startswith("+") or len(phone) < 10:
                await message.answer("❌ Invalid phone format. Use +77XXXXXXXXX")
                return
            client.kaspi_phone = phone
            client.state = "awaiting_kaspi_receiver"
            await session.commit()

            await message.answer(
                "👤 <b>Step 3/3 — Kaspi Receiver Name</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Send the <b>full name</b> of the Kaspi account holder:\n"
                "<i>(Example: Aizhan K.)</i>",
                parse_mode="HTML"
            )

        # --- State: awaiting_kaspi_receiver ---
        elif client.state == "awaiting_kaspi_receiver":
            client.kaspi_receiver = message.text.strip()
            client.state = "awaiting_payment"
            await session.commit()

            await message.answer(
                "💳 <b>Almost done! Make the payment:</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<blockquote>🏦 <b>Kaspi Bank</b>\n"
                f"📞 <code>{MASTER_KASPI_PHONE}</code>\n"
                f"👤 {MASTER_KASPI_RECEIVER} ✅</blockquote>\n\n"
                f"💰 Amount: <b>{SUBSCRIPTION_PRICE:,} ₸</b>\n\n"
                "<i>📸 After payment, send the receipt (photo or PDF) here:</i> 👇",
                parse_mode="HTML"
            )

        else:
            await message.answer(
                "Use the buttons below.",
                reply_markup=master_main_keyboard()
            )


# ─── Receive payment receipt ───────────────────────────────────────
@router.message(F.photo | F.document)
async def handle_receipt(message: Message, bot: Bot):
    async with saas_session() as session:
        client = await session.scalar(
            select(SaasClient).where(SaasClient.tg_id == message.from_user.id)
        )
        if not client or client.state != "awaiting_payment":
            return

        file_id = (message.photo[-1].file_id if message.photo
                   else message.document.file_id)

        payment = SaasPayment(
            client_tg_id=client.tg_id,
            amount=SUBSCRIPTION_PRICE,
            receipt_file_id=file_id,
            status="pending"
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    await message.answer(
        "⏳ <b>Receipt received!</b>\n\n"
        "Admin will review and activate your bot shortly. ✅",
        parse_mode="HTML"
    )

    # Notify owner/admin
    kb = master_approve_keyboard(payment.id, client.tg_id)
    admin_text = (
        f"🆕 <b>NEW BOT SUBSCRIPTION REQUEST</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 @{message.from_user.username or 'no_username'}\n"
        f"🆔 ID: <code>{client.tg_id}</code>\n"
        f"🤖 Bot: @{client.bot_username}\n"
        f"📞 Kaspi: {client.kaspi_phone}\n"
        f"👤 Receiver: {client.kaspi_receiver}\n"
        f"💰 Amount: <b>{SUBSCRIPTION_PRICE:,} ₸</b>\n"
        f"🔢 Payment ID: #{payment.id}"
    )
    for admin_id in config.admin_ids:
        try:
            if message.photo:
                await bot.send_photo(admin_id, photo=file_id, caption=admin_text,
                                     reply_markup=kb, parse_mode="HTML")
            else:
                await bot.send_document(admin_id, document=file_id, caption=admin_text,
                                        reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


# ─── Status ───────────────────────────────────────────────────────
@router.callback_query(F.data == "saas_status")
async def check_status(callback: CallbackQuery):
    async with saas_session() as session:
        client = await session.scalar(
            select(SaasClient).where(SaasClient.tg_id == callback.from_user.id)
        )

    if not client:
        await callback.answer("You are not registered yet.", show_alert=True)
        return

    if client.is_active and client.expires_at:
        from datetime import datetime
        days_left = (client.expires_at - datetime.utcnow()).days
        status = f"✅ Active — {days_left} days left"
        bot_info = f"@{client.bot_username}"
    elif client.state == "awaiting_payment":
        status = "⏳ Payment under review"
        bot_info = f"@{client.bot_username}" if client.bot_username else "—"
    else:
        status = "❌ Not active"
        bot_info = "—"

    await callback.message.edit_text(
        f"📊 <b>Your Bot Status</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 Bot: {bot_info}\n"
        f"📌 Status: {status}\n"
        f"📞 Kaspi: {client.kaspi_phone or '—'}\n"
        f"👤 Receiver: {client.kaspi_receiver or '—'}",
        parse_mode="HTML",
        reply_markup=master_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "saas_cancel")
async def saas_cancel(callback: CallbackQuery):
    async with saas_session() as session:
        client = await session.scalar(
            select(SaasClient).where(SaasClient.tg_id == callback.from_user.id)
        )
        if client:
            client.state = "start"
            await session.commit()
    await callback.message.edit_text(
        "❌ Cancelled. Use /start to begin again.",
        reply_markup=master_main_keyboard()
    )
    await callback.answer()
