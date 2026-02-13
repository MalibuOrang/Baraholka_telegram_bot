import logging

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from bot.database import crud
from bot.keyboards.inline import my_ad_actions_kb
from bot.keyboards.reply import BTN_MY_ADS, BTN_KEEP, edit_step_kb, main_menu_kb
from bot.states.ad_states import EditAdStates
from bot.utils import format_ad_md

router = Router()
log = logging.getLogger(__name__)


async def _delete_publication_messages(
    bot: Bot,
    ad_id: int,
    chat_id: int | None,
    message_ids: list[int],
) -> None:
    if not chat_id or not message_ids:
        return
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            log.warning(
                "Failed to delete published message for ad #%s (chat=%s, message=%s): %s",
                ad_id,
                chat_id,
                message_id,
                exc,
            )


@router.message(Command("my"))
@router.message(F.text == BTN_MY_ADS)
async def my_ads(message: Message) -> None:
    ads = await crud.get_user_ads(message.from_user.id)
    if not ads:
        await message.answer("У вас пока нет объявлений.", reply_markup=main_menu_kb())
        return

    await message.answer("Ваши объявления:", reply_markup=main_menu_kb())
    for ad in ads:
        text = format_ad_md(ad, with_status=True)
        kb = my_ad_actions_kb(ad.id)
        if len(ad.photos) > 1:
            media = [
                InputMediaPhoto(media=ad.photos[0], caption=text, parse_mode=ParseMode.MARKDOWN_V2)
            ] + [InputMediaPhoto(media=p) for p in ad.photos[1:]]
            await message.answer_media_group(media=media)
            await message.answer("Действия:", reply_markup=kb)
        elif ad.photos:
            await message.answer_photo(
                ad.photos[0],
                caption=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )
        else:
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


@router.callback_query(F.data.startswith("mydel:"))
async def delete_my_ad_callback(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user:
        await callback.answer("Ошибка пользователя", show_alert=True)
        return

    ad_id_raw = callback.data.split(":")[-1]
    if not ad_id_raw.isdigit():
        await callback.answer("Некорректный ID", show_alert=True)
        return

    ad_id = int(ad_id_raw)
    result = await crud.get_ad_full_by_id(ad_id)
    if not result:
        await callback.answer("Не удалось удалить: нет прав или ID не найден.", show_alert=True)
        return
    ad, pub_chat_id, pub_message_ids = result
    if ad.user_id != callback.from_user.id:
        await callback.answer("Не удалось удалить: нет прав или ID не найден.", show_alert=True)
        return

    await _delete_publication_messages(bot, ad_id, pub_chat_id, pub_message_ids)
    ok = await crud.delete_user_ad(ad_id, callback.from_user.id)
    if not ok:
        await callback.answer("Не удалось удалить: нет прав или ID не найден.", show_alert=True)
        return

    await callback.answer("Объявление удалено")
    try:
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.callback_query(F.data.startswith("myedit:"))
async def edit_my_ad_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user:
        await callback.answer("Ошибка пользователя", show_alert=True)
        return

    ad_id_raw = callback.data.split(":")[-1]
    if not ad_id_raw.isdigit():
        await callback.answer("Некорректный ID", show_alert=True)
        return

    ad_id = int(ad_id_raw)
    result = await crud.get_ad_full_by_id(ad_id)
    if not result:
        await callback.answer("Нет прав или ID не найден.", show_alert=True)
        return
    ad, _, _ = result
    if ad.user_id != callback.from_user.id:
        await callback.answer("Нет прав или ID не найден.", show_alert=True)
        return
    await state.clear()
    await state.set_state(EditAdStates.title)
    await state.update_data(
        ad_id=ad_id,
        title=ad.title,
        description=ad.description,
        price_text=ad.price_text,
        price_value=ad.price_value,
        category=ad.category,
        city=ad.city,
        photos=list(ad.photos),
        photos_original=list(ad.photos),
        photos_replaced=False,
    )
    await callback.message.answer(
        f"Текущий заголовок: {ad.title}\nВведите новый заголовок или нажмите «{BTN_KEEP}».",
        reply_markup=edit_step_kb(),
    )
    await callback.answer("Редактирование")


@router.message(Command("delete"))
async def delete_ad(message: Message, command: CommandObject, bot: Bot) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /delete ID")
        return

    ad_id = int(command.args)
    result = await crud.get_ad_full_by_id(ad_id)
    if not result:
        await message.answer("Не удалось удалить: нет прав или ID не найден.")
        return
    ad, pub_chat_id, pub_message_ids = result
    if ad.user_id != message.from_user.id:
        await message.answer("Не удалось удалить: нет прав или ID не найден.")
        return

    await _delete_publication_messages(bot, ad_id, pub_chat_id, pub_message_ids)
    ok = await crud.delete_user_ad(ad_id, message.from_user.id)
    if ok:
        await message.answer("Объявление удалено.")
    else:
        await message.answer("Не удалось удалить: нет прав или ID не найден.")
