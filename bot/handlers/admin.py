import logging

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from bot.config import get_settings
from bot.database import crud
from bot.keyboards.inline import contact_author_kb
from bot.utils import format_ad_md

router = Router()
log = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Недостаточно прав.")
        return
    pending = await crud.list_ads(status="pending", limit=20)
    if not pending:
        await message.answer("Нет объявлений на модерации.")
        return
    lines = ["Pending объявления:"]
    for ad in pending:
        lines.append(f"#{ad.id} | {ad.title} | @{ad.username or 'no_username'}")
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("ad:"))
async def moderation_actions(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    _, action, ad_id_raw = callback.data.split(":")
    ad_id = int(ad_id_raw)
    ad = await crud.get_ad_by_id(ad_id)
    if not ad:
        await callback.answer("Не найдено", show_alert=True)
        return

    if action == "ap":
        settings = get_settings()
        try:
            if settings.publication_chat_id:
                text = format_ad_md(ad)
                kb = contact_author_kb(ad.username, ad.user_id)
                published_message_ids: list[int] = []
                if len(ad.photos) > 1:
                    media = [
                        InputMediaPhoto(media=ad.photos[0], caption=text, parse_mode=ParseMode.MARKDOWN_V2)
                    ] + [InputMediaPhoto(media=p) for p in ad.photos[1:]]
                    sent_messages = await bot.send_media_group(settings.publication_chat_id, media=media)
                    published_message_ids.extend([m.message_id for m in sent_messages])
                    if kb:
                        sent_kb = await bot.send_message(
                            settings.publication_chat_id,
                            "Связаться с автором:",
                            reply_markup=kb,
                        )
                        published_message_ids.append(sent_kb.message_id)
                elif ad.photos:
                    sent = await bot.send_photo(
                        settings.publication_chat_id,
                        ad.photos[0],
                        caption=text,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=kb,
                    )
                    published_message_ids.append(sent.message_id)
                else:
                    sent = await bot.send_message(
                        settings.publication_chat_id,
                        text,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        reply_markup=kb,
                    )
                    published_message_ids.append(sent.message_id)
                await crud.set_publication_info(ad_id, settings.publication_chat_id, published_message_ids)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            log.warning("Failed to publish approved ad #%s: %s", ad_id, exc)
            await callback.answer(
                "Не удалось опубликовать в канал: проверьте PUBLICATION_CHAT_ID и права бота.",
                show_alert=True,
            )
            return

        await crud.update_ad_status(ad_id, "published")
        await bot.send_message(ad.user_id, f"Ваше объявление #{ad.id} одобрено.")
        await callback.answer("Approved")
        return

    if action == "rj":
        await crud.update_ad_status(ad_id, "rejected")
        await bot.send_message(ad.user_id, f"Ваше объявление #{ad.id} отклонено.")
        await callback.answer("Rejected")
