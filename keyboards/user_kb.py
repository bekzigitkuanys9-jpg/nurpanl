from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from locales import get_text

# ─── CONTACT SHARE (first-time users) ────────────────────────────

def share_contact_keyboard(lang: str = "kk") -> ReplyKeyboardMarkup:
    """Keyboard with a request_contact button for identity verification."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(lang, "share_contact"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kk")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ]
    )

# ─── USER KEYBOARDS ───────────────────────────────────────────────

def main_menu_keyboard(lang: str = "kk") -> ReplyKeyboardMarkup:
    """Main dashboard keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "btn_products")), KeyboardButton(text=get_text(lang, "btn_topup"))],
            [KeyboardButton(text=get_text(lang, "btn_keys")),  KeyboardButton(text=get_text(lang, "btn_referral"))],
            [KeyboardButton(text=get_text(lang, "btn_profile")), KeyboardButton(text=get_text(lang, "btn_links"))],
            [KeyboardButton(text=get_text(lang, "btn_settings"))]
        ],
        resize_keyboard=True
    )


def products_keyboard(products, is_vip: bool = False, lang: str = "kk") -> InlineKeyboardMarkup:
    """Buttons in a grid (2 per row) matching the user's screenshot."""
    rows = []
    current_row = []
    for p in products:
        label = f"🔑 {p.name}"
        current_row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"buy_{p.id}"
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    
    if current_row:
        rows.append(current_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)
