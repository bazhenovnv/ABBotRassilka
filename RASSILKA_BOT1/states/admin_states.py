from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_broadcast_content = State()
    waiting_reply_content = State()


class UserStates(StatesGroup):
    waiting_message_to_admin = State()