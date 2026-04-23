from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config.settings import settings
from keyboards.admin import admin_menu


common_router = Router()


@common_router.callback_query(F.data == "common:cancel")
async def common_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.from_user.id == settings.admin_id:
        await callback.message.answer("Действие отменено.", reply_markup=admin_menu())
    else:
        await callback.message.answer("Действие отменено.")
    await callback.answer()


@common_router.message(F.text == "/cancel")
async def cancel_by_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user.id == settings.admin_id:
        await message.answer("Действие отменено.", reply_markup=admin_menu())
    else:
        await message.answer("Действие отменено.")
