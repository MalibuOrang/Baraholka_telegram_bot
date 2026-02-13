from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, Message

from bot.config import get_settings
from bot.database import crud
from bot.database.models import AdCreate
from bot.keyboards.inline import admin_moderation_kb
from bot.keyboards.reply import (
    BTN_CANCEL,
    BTN_DONE,
    BTN_KEEP,
    BTN_NEW_AD,
    BTN_PUBLISH,
    BTN_CLEAR_PHONE,
    BTN_SKIP_PHONE,
    BTN_SKIP_PHOTO,
    CATEGORIES,
    cancel_kb,
    category_kb,
    confirm_kb,
    edit_step_kb,
    edit_phone_kb,
    main_menu_kb,
    phone_optional_kb,
    photos_kb,
)
from bot.states.ad_states import AdCreateStates, EditAdStates
from bot.utils import format_ad_md

router = Router()
log = logging.getLogger(__name__)


def _parse_price(raw: str) -> tuple[str, float | None] | None:
    txt = raw.strip().lower()
    if txt in {"договорная", "бесплатно"}:
        return txt.capitalize(), None
    normalized = txt.replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", normalized):
        return None
    return f"{normalized} ₽", float(normalized)


@router.message(Command("new"))
@router.message(lambda m: m.text == BTN_NEW_AD)
async def start_new_ad(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    limit_used = await crud.count_ads_last_24h(message.from_user.id)
    if limit_used >= settings.daily_ads_limit:
        await message.answer("Лимит: 3 объявления за 24 часа.", reply_markup=main_menu_kb())
        return

    await state.clear()
    await state.set_state(AdCreateStates.title)
    await state.update_data(phone=None)
    await message.answer("Введите заголовок (до 100 символов):", reply_markup=cancel_kb())


@router.message(AdCreateStates.title, F.text == BTN_CANCEL)
@router.message(AdCreateStates.description, F.text == BTN_CANCEL)
@router.message(AdCreateStates.price, F.text == BTN_CANCEL)
@router.message(AdCreateStates.category, F.text == BTN_CANCEL)
@router.message(AdCreateStates.city, F.text == BTN_CANCEL)
@router.message(AdCreateStates.phone, F.text == BTN_CANCEL)
@router.message(AdCreateStates.photos, F.text == BTN_CANCEL)
@router.message(AdCreateStates.confirm, F.text == BTN_CANCEL)
async def cancel_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Создание объявления отменено.", reply_markup=main_menu_kb())


@router.message(EditAdStates.title, F.text == BTN_CANCEL)
@router.message(EditAdStates.description, F.text == BTN_CANCEL)
@router.message(EditAdStates.price, F.text == BTN_CANCEL)
@router.message(EditAdStates.category, F.text == BTN_CANCEL)
@router.message(EditAdStates.city, F.text == BTN_CANCEL)
@router.message(EditAdStates.phone, F.text == BTN_CANCEL)
@router.message(EditAdStates.photos, F.text == BTN_CANCEL)
@router.message(EditAdStates.confirm, F.text == BTN_CANCEL)
async def cancel_edit_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Редактирование отменено.", reply_markup=main_menu_kb())


@router.message(AdCreateStates.title, F.text)
async def set_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title or len(title) > 100:
        await message.answer("Заголовок должен быть 1..100 символов.")
        return
    await state.update_data(title=title)
    await state.set_state(AdCreateStates.description)
    await message.answer("Введите описание (до 2000 символов):")


@router.message(AdCreateStates.description, F.text)
async def set_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if not description or len(description) > 2000:
        await message.answer("Описание должно быть 1..2000 символов.")
        return
    await state.update_data(description=description)
    await state.set_state(AdCreateStates.price)
    await message.answer("Введите цену (число) или: договорная / бесплатно")


@router.message(AdCreateStates.price, F.text)
async def set_price(message: Message, state: FSMContext) -> None:
    parsed = _parse_price(message.text)
    if not parsed:
        await message.answer("Неверный формат цены. Пример: 1500 или договорная.")
        return
    price_text, price_value = parsed
    await state.update_data(price_text=price_text, price_value=price_value)
    await state.set_state(AdCreateStates.category)
    await message.answer("Выберите категорию:", reply_markup=category_kb())


@router.message(AdCreateStates.category, F.text)
async def set_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip()
    if category not in CATEGORIES:
        await message.answer("Выберите категорию кнопкой.")
        return
    await state.update_data(category=category)
    await state.set_state(AdCreateStates.city)
    await message.answer("Введите город/район текстом:")


@router.message(AdCreateStates.city, F.text)
async def set_city(message: Message, state: FSMContext) -> None:
    city = message.text.strip()
    if not city or len(city) > 100:
        await message.answer("Город/район должен быть 1..100 символов.")
        return
    await state.update_data(city=city, photos=[])
    await state.set_state(AdCreateStates.phone)
    await message.answer(
        "Введите телефон или нажмите «Пропустить телефон».",
        reply_markup=phone_optional_kb(),
    )


@router.message(AdCreateStates.phone, F.contact)
async def capture_phone(message: Message, state: FSMContext) -> None:
    if message.contact and message.contact.user_id == message.from_user.id:
        await state.update_data(phone=message.contact.phone_number)
        await state.set_state(AdCreateStates.photos)
        await message.answer("Телефон сохранен. Отправьте до 4 фото.", reply_markup=photos_kb())


@router.message(AdCreateStates.phone, F.text == BTN_SKIP_PHONE)
async def skip_phone(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=None)
    await state.set_state(AdCreateStates.photos)
    await message.answer("Отправьте до 4 фото. Когда закончите: «Готово».", reply_markup=photos_kb())


@router.message(AdCreateStates.phone, F.text)
async def set_phone_text(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if len(phone) > 30:
        await message.answer("Телефон слишком длинный. Введите до 30 символов.")
        return
    await state.update_data(phone=phone)
    await state.set_state(AdCreateStates.photos)
    await message.answer("Телефон сохранен. Отправьте до 4 фото.", reply_markup=photos_kb())


@router.message(EditAdStates.phone, F.contact)
async def edit_phone_contact(message: Message, state: FSMContext) -> None:
    if message.contact and message.contact.user_id == message.from_user.id:
        await state.update_data(phone=message.contact.phone_number)
        await state.set_state(EditAdStates.photos)
        await message.answer(
            "Телефон сохранен. Отправьте до 4 фото.",
            reply_markup=photos_kb(),
        )


@router.message(AdCreateStates.photos, F.photo)
async def add_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = data.get("photos", [])
    if len(photos) >= 4:
        await message.answer("Максимум 4 фото.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"Фото добавлено: {len(photos)}/4")


@router.message(AdCreateStates.photos, F.text == BTN_SKIP_PHOTO)
@router.message(AdCreateStates.photos, F.text == BTN_DONE)
async def finish_photos(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    preview_ad = AdCreate(
        user_id=message.from_user.id,
        username=message.from_user.username,
        phone=data.get("phone"),
        title=data["title"],
        description=data["description"],
        price_text=data["price_text"],
        price_value=data.get("price_value"),
        category=data["category"],
        photos=data.get("photos", []),
        city=data["city"],
    )
    from bot.database.models import AdRecord

    fake = AdRecord(
        id=0,
        user_id=preview_ad.user_id,
        username=preview_ad.username,
        phone=preview_ad.phone,
        title=preview_ad.title,
        description=preview_ad.description,
        price_text=preview_ad.price_text,
        price_value=preview_ad.price_value,
        category=preview_ad.category,
        photos=preview_ad.photos,
        city=preview_ad.city,
        status="draft",
        created_at="",
        published_at=None,
    )
    await state.set_state(AdCreateStates.confirm)
    if len(preview_ad.photos) > 1:
        media = [
            InputMediaPhoto(
                media=preview_ad.photos[0],
                caption=format_ad_md(fake),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        ] + [InputMediaPhoto(media=p) for p in preview_ad.photos[1:]]
        await message.answer_media_group(media=media)
        await message.answer("Проверьте объявление и нажмите «Опубликовать».", reply_markup=confirm_kb())
    elif preview_ad.photos:
        await message.answer_photo(
            photo=preview_ad.photos[0],
            caption=format_ad_md(fake),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=confirm_kb(),
        )
    else:
        await message.answer(
            format_ad_md(fake),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=confirm_kb(),
        )


async def _send_to_moderation(bot: Bot, ad_id: int) -> None:
    settings = get_settings()
    ad = await crud.get_ad_by_id(ad_id)
    if not ad:
        return
    text = format_ad_md(ad, with_status=True)
    if settings.moderation_chat_id:
        if len(ad.photos) > 1:
            media = [
                InputMediaPhoto(media=ad.photos[0], caption=text, parse_mode=ParseMode.MARKDOWN_V2)
            ] + [InputMediaPhoto(media=p) for p in ad.photos[1:]]
            await bot.send_media_group(settings.moderation_chat_id, media=media)
            await bot.send_message(
                settings.moderation_chat_id,
                "Модерация объявления:",
                reply_markup=admin_moderation_kb(ad.id),
            )
        elif ad.photos:
            await bot.send_photo(
                settings.moderation_chat_id,
                ad.photos[0],
                caption=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=admin_moderation_kb(ad.id),
            )
        else:
            await bot.send_message(
                settings.moderation_chat_id,
                text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=admin_moderation_kb(ad.id),
            )


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


@router.message(AdCreateStates.confirm, F.text == BTN_PUBLISH)
async def publish_ad(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    ad = AdCreate(
        user_id=message.from_user.id,
        username=message.from_user.username,
        phone=data.get("phone"),
        title=data["title"],
        description=data["description"],
        price_text=data["price_text"],
        price_value=data.get("price_value"),
        category=data["category"],
        photos=data.get("photos", []),
        city=data["city"],
    )

    try:
        ad_id = await crud.create_ad(ad)
        settings = get_settings()

        if settings.moderation_chat_id:
            await _send_to_moderation(bot, ad_id)
            await message.answer(
                f"Объявление #{ad_id} отправлено на модерацию.",
                reply_markup=main_menu_kb(),
            )
        else:
            await crud.update_ad_status(ad_id, "published")
            await message.answer(
                f"Объявление #{ad_id} опубликовано.",
                reply_markup=main_menu_kb(),
            )

        await state.clear()
    except Exception as exc:
        log.exception("create ad failed: %s", exc)
        await message.answer("Ошибка при сохранении объявления. Попробуйте позже.")


@router.message(Command("edit"))
async def start_edit_ad(message: Message, command: CommandObject, state: FSMContext) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /edit ID")
        return
    ad_id = int(command.args)
    result = await crud.get_ad_full_by_id(ad_id)
    if not result:
        await message.answer("Нет прав или ID не найден.")
        return
    ad, _, _ = result
    if ad.user_id != message.from_user.id:
        await message.answer("Нет прав или ID не найден.")
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
        phone=ad.phone,
        photos=list(ad.photos),
        photos_original=list(ad.photos),
        photos_replaced=False,
    )
    await message.answer(
        f"Текущий заголовок: {ad.title}\nВведите новый заголовок или нажмите «{BTN_KEEP}».",
        reply_markup=edit_step_kb(),
    )


@router.message(EditAdStates.title, F.text)
async def edit_title(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if message.text == BTN_KEEP:
        title = data["title"]
    else:
        title = message.text.strip()
        if not title or len(title) > 100:
            await message.answer("Заголовок должен быть 1..100 символов.")
            return
    await state.update_data(title=title)
    await state.set_state(EditAdStates.description)
    await message.answer(
        f"Текущее описание: {data['description']}\nВведите новое описание или нажмите «{BTN_KEEP}».",
        reply_markup=edit_step_kb(),
    )


@router.message(EditAdStates.description, F.text)
async def edit_description(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if message.text == BTN_KEEP:
        description = data["description"]
    else:
        description = message.text.strip()
        if not description or len(description) > 2000:
            await message.answer("Описание должно быть 1..2000 символов.")
            return
    await state.update_data(description=description)
    await state.set_state(EditAdStates.price)
    await message.answer(
        f"Текущая цена: {data['price_text']}\nВведите новую цену или нажмите «{BTN_KEEP}».",
        reply_markup=edit_step_kb(),
    )


@router.message(EditAdStates.price, F.text)
async def edit_price(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if message.text == BTN_KEEP:
        await state.update_data(price_text=data["price_text"], price_value=data.get("price_value"))
    else:
        parsed = _parse_price(message.text)
        if not parsed:
            await message.answer("Неверный формат цены. Пример: 1500 или договорная.")
            return
        price_text, price_value = parsed
        await state.update_data(price_text=price_text, price_value=price_value)
    await state.set_state(EditAdStates.category)
    await message.answer(
        f"Текущая категория: {data['category']}\nВыберите новую или нажмите «{BTN_KEEP}».",
        reply_markup=edit_step_kb(),
    )


@router.message(EditAdStates.category, F.text)
async def edit_category(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if message.text == BTN_KEEP:
        category = data["category"]
    else:
        category = message.text.strip()
        if category not in CATEGORIES:
            await message.answer("Выберите категорию кнопкой.")
            return
    await state.update_data(category=category)
    await state.set_state(EditAdStates.city)
    await message.answer(
        f"Текущий город/район: {data['city']}\nВведите новый или нажмите «{BTN_KEEP}».",
        reply_markup=edit_step_kb(),
    )


@router.message(EditAdStates.city, F.text)
async def edit_city(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if message.text == BTN_KEEP:
        city = data["city"]
    else:
        city = message.text.strip()
        if not city or len(city) > 100:
            await message.answer("Город/район должен быть 1..100 символов.")
            return
    await state.update_data(city=city)
    await state.set_state(EditAdStates.phone)
    await message.answer(
        f"Текущий телефон: {data.get('phone') or 'не указан'}\nВведите новый телефон или нажмите «{BTN_KEEP}».",
        reply_markup=edit_phone_kb(),
    )


@router.message(EditAdStates.phone, F.text == BTN_CLEAR_PHONE)
async def edit_phone_clear(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=None)
    await state.set_state(EditAdStates.photos)
    await message.answer(
        "Телефон удален. Отправьте до 4 фото.",
        reply_markup=photos_kb(),
    )


@router.message(EditAdStates.phone, F.text)
async def edit_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if message.text == BTN_KEEP:
        phone = data.get("phone")
    else:
        phone = message.text.strip()
        if len(phone) > 30:
            await message.answer("Телефон слишком длинный. Введите до 30 символов.")
            return
    await state.update_data(phone=phone)
    await state.set_state(EditAdStates.photos)
    await message.answer(
        "Отправьте до 4 фото. Нажмите «Пропустить фото», чтобы оставить текущие, или «Готово».",
        reply_markup=photos_kb(),
    )


@router.message(EditAdStates.photos, F.photo)
async def edit_add_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = data.get("photos", [])
    if not data.get("photos_replaced"):
        photos = []
        await state.update_data(photos_replaced=True)
    if len(photos) >= 4:
        await message.answer("Максимум 4 фото.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"Фото добавлено: {len(photos)}/4")


@router.message(EditAdStates.photos, F.text == BTN_SKIP_PHOTO)
@router.message(EditAdStates.photos, F.text == BTN_DONE)
async def edit_finish_photos(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    photos = data.get("photos", [])
    if not data.get("photos_replaced"):
        photos = data.get("photos_original", [])

    from bot.database.models import AdRecord

    fake = AdRecord(
        id=0,
        user_id=message.from_user.id,
        username=message.from_user.username,
        phone=data.get("phone"),
        title=data["title"],
        description=data["description"],
        price_text=data["price_text"],
        price_value=data.get("price_value"),
        category=data["category"],
        photos=photos,
        city=data["city"],
        status="draft",
        created_at="",
        published_at=None,
    )
    await state.update_data(photos=photos)
    await state.set_state(EditAdStates.confirm)
    if len(photos) > 1:
        media = [
            InputMediaPhoto(media=photos[0], caption=format_ad_md(fake), parse_mode=ParseMode.MARKDOWN_V2)
        ] + [InputMediaPhoto(media=p) for p in photos[1:]]
        await message.answer_media_group(media=media)
        await message.answer("Проверьте объявление и нажмите «Опубликовать».", reply_markup=confirm_kb())
    elif photos:
        await message.answer_photo(
            photo=photos[0],
            caption=format_ad_md(fake),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=confirm_kb(),
        )
    else:
        await message.answer(
            format_ad_md(fake),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=confirm_kb(),
        )


@router.message(EditAdStates.confirm, F.text == BTN_PUBLISH)
async def edit_publish_ad(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    ad_id = data["ad_id"]
    # Delete previously published messages before re-moderation
    result = await crud.get_ad_full_by_id(ad_id)
    if result:
        _, pub_chat_id, pub_message_ids = result
        await _delete_publication_messages(bot, ad_id, pub_chat_id, pub_message_ids)
    await crud.update_ad(
        ad_id=ad_id,
        phone=data.get("phone"),
        title=data["title"],
        description=data["description"],
        price_text=data["price_text"],
        price_value=data.get("price_value"),
        category=data["category"],
        city=data["city"],
        photos=data.get("photos", []),
    )
    settings = get_settings()
    if settings.moderation_chat_id:
        await _send_to_moderation(bot, ad_id)
        await message.answer(
            f"Объявление #{ad_id} отправлено на модерацию.",
            reply_markup=main_menu_kb(),
        )
    else:
        await crud.update_ad_status(ad_id, "published")
        await message.answer(
            f"Объявление #{ad_id} опубликовано.",
            reply_markup=main_menu_kb(),
        )
    await state.clear()
