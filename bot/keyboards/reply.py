from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

CATEGORIES = [
    "Одежда",
    "Электроника",
    "Мебель",
    "Транспорт",
    "Детские товары",
    "Животные",
    "Услуги",
    "Другое",
]

BTN_NEW_AD = "📝 Подать объявление"
BTN_MY_ADS = "📂 Мои объявления"
BTN_SEARCH = "🔎 Поиск"
BTN_CATEGORIES = "🗂 Категории"
BTN_HELP = "ℹ️ Помощь"
BTN_CANCEL = "❌ Отмена"
BTN_DONE = "✅ Готово"
BTN_SKIP_PHOTO = "⏭ Пропустить фото"
BTN_PUBLISH = "🚀 Опубликовать"
BTN_BACK = "⬅️ Назад"
BTN_KEEP = "Оставить как есть"
BTN_SKIP_PHONE = "Пропустить телефон"
BTN_CLEAR_PHONE = "Убрать телефон"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_AD), KeyboardButton(text=BTN_MY_ADS)],
            [KeyboardButton(text=BTN_SEARCH), KeyboardButton(text=BTN_CATEGORIES)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def category_kb() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=cat)] for cat in CATEGORIES]
    rows.append([KeyboardButton(text=BTN_CANCEL)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def browse_categories_kb() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=cat)] for cat in CATEGORIES]
    rows.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def photos_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DONE), KeyboardButton(text=BTN_SKIP_PHOTO)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def phone_optional_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SKIP_PHONE), KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PUBLISH), KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def edit_step_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_KEEP), KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def edit_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_KEEP), KeyboardButton(text=BTN_CLEAR_PHONE)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )
