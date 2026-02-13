from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import InputMediaPhoto, Message

from bot.database import crud
from bot.database.models import AdRecord
from bot.keyboards.inline import contact_author_kb
from bot.keyboards.reply import (
    BTN_BACK,
    BTN_CANCEL,
    BTN_CATEGORIES,
    BTN_SEARCH,
    CATEGORIES,
    browse_categories_kb,
    cancel_kb,
    main_menu_kb,
)
from bot.states.ad_states import SearchStates
from bot.utils import format_ad_md

router = Router()


async def _send_ad_cards(message: Message, ads: list[AdRecord], title: str) -> None:
    await message.answer(title)
    for ad in ads:
        kb = contact_author_kb(ad.username, ad.user_id)
        text = format_ad_md(ad, with_status=False)
        if len(ad.photos) > 1:
            media = [
                InputMediaPhoto(media=ad.photos[0], caption=text, parse_mode=ParseMode.MARKDOWN_V2)
            ] + [InputMediaPhoto(media=p) for p in ad.photos[1:]]
            await message.answer_media_group(media=media)
            if kb:
                await message.answer("Связаться с автором:", reply_markup=kb)
        elif ad.photos:
            await message.answer_photo(
                ad.photos[0],
                caption=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )
        else:
            await message.answer(
                text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )


@router.message(default_state, F.text == BTN_SEARCH)
async def search_button(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_query)
    await message.answer("Введите текст для поиска:", reply_markup=cancel_kb())


@router.message(default_state, Command("search"))
async def search_ads(message: Message, command: CommandObject, state: FSMContext) -> None:
    if not command.args:
        await state.set_state(SearchStates.waiting_query)
        await message.answer("Введите текст для поиска:", reply_markup=cancel_kb())
        return

    query = command.args.strip()
    ads = await crud.search_ads(query)
    if not ads:
        await message.answer("Ничего не найдено.", reply_markup=main_menu_kb())
        return

    await _send_ad_cards(message, ads, f"Найдено по запросу: {query}")
    await message.answer("Поиск завершен.", reply_markup=main_menu_kb())


@router.message(SearchStates.waiting_query, F.text == BTN_CANCEL)
async def search_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Поиск отменен.", reply_markup=main_menu_kb())


@router.message(SearchStates.waiting_query, F.text)
async def search_query_input(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Введите минимум 2 символа или нажмите «Отмена».")
        return

    ads = await crud.search_ads(query)
    await state.clear()
    if not ads:
        await message.answer("Ничего не найдено.", reply_markup=main_menu_kb())
        return

    await _send_ad_cards(message, ads, f"Найдено по запросу: {query}")
    await message.answer("Поиск завершен.", reply_markup=main_menu_kb())


@router.message(default_state, Command("category"))
async def category_command(message: Message) -> None:
    await message.answer("Выберите категорию:", reply_markup=browse_categories_kb())


@router.message(default_state, F.text == BTN_CATEGORIES)
async def category_menu(message: Message) -> None:
    await message.answer("Выберите категорию:", reply_markup=browse_categories_kb())


@router.message(default_state, F.text == BTN_BACK)
async def category_back(message: Message) -> None:
    await message.answer("Главное меню.", reply_markup=main_menu_kb())


@router.message(default_state, F.text.in_(CATEGORIES))
async def show_category_ads(message: Message) -> None:
    category = message.text.strip()
    ads = await crud.get_ads_by_category(category)
    if not ads:
        await message.answer(f"В категории «{category}» пока нет объявлений.")
        return

    await _send_ad_cards(message, ads, f"Категория: {category}")


@router.message(default_state, Command("view"))
async def view_ad(message: Message, command: CommandObject) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /view ID")
        return

    ad = await crud.get_ad_by_id(int(command.args))
    if not ad or ad.status in {"deleted", "rejected"}:
        await message.answer("Объявление не найдено.")
        return

    kb = contact_author_kb(ad.username, ad.user_id)
    text = format_ad_md(ad, with_status=True)

    if len(ad.photos) > 1:
        media = [
            InputMediaPhoto(media=ad.photos[0], caption=text, parse_mode=ParseMode.MARKDOWN_V2)
        ] + [InputMediaPhoto(media=p) for p in ad.photos[1:]]
        await message.answer_media_group(media=media)
        if kb:
            await message.answer("Связаться с автором:", reply_markup=kb)
    elif ad.photos:
        await message.answer_photo(
            ad.photos[0],
            caption=text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    else:
        await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)
