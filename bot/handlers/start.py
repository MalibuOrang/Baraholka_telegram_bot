from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import subscription_required_kb
from bot.keyboards.reply import BTN_HELP, main_menu_kb

router = Router()

CHANNEL_URL = "https://t.me/nasha_baraholka_zp"
CHANNEL_USERNAME = "@nasha_baraholka_zp"


async def _is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return member.status not in {"left", "kicked"}


async def _send_subscription_required(message: Message) -> None:
    await message.answer(
        "Чтобы продолжить, подпишитесь на канал @nasha_baraholka_zp и нажмите «Проверить подписку».",
        reply_markup=subscription_required_kb(CHANNEL_URL),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    if not await _is_subscribed(bot, message.from_user.id):
        await _send_subscription_required(message)
        return

    text = (
        "Привет! Это бот местной барахолки.\n\n"
        "Доступно:\n"
        "/new - подать объявление\n"
        "/my - мои объявления\n"
        "/search текст - поиск\n"
        "/category - выбор категории\n"
        "/view ID - просмотр\n"
        "/delete ID - удалить\n"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "sub:check")
async def check_subscription(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user:
        await callback.answer("Ошибка проверки", show_alert=True)
        return

    if not await _is_subscribed(bot, callback.from_user.id):
        await callback.answer("Подписка не найдена. Подпишитесь и повторите.", show_alert=True)
        return

    if callback.message:
        await callback.message.answer("Подписка подтверждена. Доступ открыт.", reply_markup=main_menu_kb())
    await callback.answer("Готово")


@router.message(lambda m: m.text == BTN_HELP)
async def help_menu(message: Message) -> None:
    await message.answer(
        "Быстрые команды:\n"
        "/new\n/my\n/search телефон\n/category\n/view 123\n/delete 123",
        reply_markup=main_menu_kb(),
    )
