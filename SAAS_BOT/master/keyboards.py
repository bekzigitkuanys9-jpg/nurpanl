from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def master_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Buy Bot Subscription", callback_data="saas_buy")],
        [InlineKeyboardButton(text="📊 My Bot Status", callback_data="saas_status")],
        [InlineKeyboardButton(text="📞 Support", url="https://t.me/nurdapanel")],
    ])


def master_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Confirm", callback_data="saas_confirm")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="saas_cancel")],
    ])


def master_approve_keyboard(payment_id: int, client_tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Approve",
                callback_data=f"saas_approve_{payment_id}_{client_tg_id}"
            ),
            InlineKeyboardButton(
                text="❌ Reject",
                callback_data=f"saas_reject_{payment_id}_{client_tg_id}"
            ),
        ]
    ])


def share_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
