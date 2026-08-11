"""
Скинулись — бот, открывающий мини-апп для сплита расходов.

Запуск:
    pip install -r requirements.txt
    export BOT_TOKEN=...          # токен от @BotFather
    export WEBAPP_URL=https://your-domain.com/app/
    python bot/bot.py
"""
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-domain.com/app/")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧾 Открыть Скинулись",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "Привет! Это бот для сплита расходов в компании.\n\n"
        "Создавай группу, добавляй траты, а бот сам посчитает, "
        "кто кому и сколько должен перевести — с минимальным числом переводов.",
        reply_markup=kb,
    )
    # Кнопка меню слева от поля ввода тоже открывает мини-апп
    await bot.set_chat_menu_button(
        chat_id=message.chat.id,
        menu_button=MenuButtonWebApp(text="Скинулись", web_app=WebAppInfo(url=WEBAPP_URL)),
    )


@dp.message(F.web_app_data)
async def on_webapp_data(message: Message):
    """
    Если мини-апп отправляет данные через Telegram.WebApp.sendData(...),
    они прилетают сюда (например, чтобы прислать в чат итоговый расклад долгов).
    В текущей демо-версии мини-апп хранит данные сам (через backend API),
    этот хендлер пригодится, если захочешь присылать сводку в чат по кнопке "Поделиться".
    """
    await message.answer(f"Получено из мини-аппа:\n{message.web_app_data.data}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
