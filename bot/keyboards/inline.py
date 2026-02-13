from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def contact_author_kb(username: str | None, user_id: int) -> InlineKeyboardMarkup | None:
    if username:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 Связаться с автором", url=f"https://t.me/{username}")]
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Связаться с автором", url=f"tg://user?id={user_id}")]
        ]
    )


def admin_moderation_kb(ad_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"ad:ap:{ad_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"ad:rj:{ad_id}"),
            ]
        ]
    )


def my_ad_actions_kb(ad_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Редактировать", callback_data=f"myedit:{ad_id}"),
                InlineKeyboardButton(text="Удалить", callback_data=f"mydel:{ad_id}"),
            ]
        ]
    )


def subscription_required_kb(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="sub:check")],
        ]
    )
