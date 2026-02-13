from aiogram.fsm.state import State, StatesGroup


class AdCreateStates(StatesGroup):
    title = State()
    description = State()
    price = State()
    category = State()
    city = State()
    phone = State()
    photos = State()
    confirm = State()


class SearchStates(StatesGroup):
    waiting_query = State()


class EditAdStates(StatesGroup):
    title = State()
    description = State()
    price = State()
    category = State()
    city = State()
    phone = State()
    photos = State()
    confirm = State()
