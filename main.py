import openai
import logging
import sys
import os
from aiohttp import web
import time
from dotenv import load_dotenv
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout)


# Замените на ваши ключи и ID
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Убедитесь, что ключи были успешно загружены
if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not ASSISTANT_ID:
    raise EnvironmentError("Не удалось загрузить переменные окружения из .env файла")

# Настройка вебхука
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8080

# Настройка клиента OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Хранилище thread_id для каждого пользователя
user_threads = {}


@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id

    try:
        # Создаем новый Thread для пользователя
        thread = client.beta.threads.create()

        # Сохраняем thread_id для пользователя
        user_threads[user_id] = thread.id

        # Добавляем первое сообщение в Thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Привет."
        )

        # Создаем и запускаем Run, используя существующего ассистента
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Проверяем статус и отправляем ответ пользователю
        if run.status == 'completed':
            # Получаем все сообщения из потока
            thread_messages = client.beta.threads.messages.list(thread_id=thread.id)

            # Находим последнее сообщение ассистента
            assistant_message = None
            for msg in thread_messages:
                if msg.role == "assistant":
                    assistant_message = msg
                    break

            if assistant_message:
                # Извлекаем текст из сообщения ассистента
                response_text = ""
                for content_block in assistant_message.content:
                    if content_block.type == "text":
                        response_text += content_block.text.value

                # Отправляем извлеченный текст пользователю
                await message.answer(response_text)
            else:
                await message.answer("Не удалось получить ответ от ассистента.")
        else:
            await message.answer("Ошибка: обработка не завершена.")
    except Exception as e:
        logging.error(f"Ошибка в команде /start: {e}")
        await message.answer("Ошибка. Попробуйте позже.")


@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id

    # Проверяем, есть ли сохранённый thread_id для этого пользователя
    if user_id not in user_threads:
        await message.answer("Пожалуйста, начните сначала с команды /start.")
        return

    # Если сообщение не является текстом (например, фото, видео, стикер и т.д.)
    if not message.text:
        await message.answer("О-о-о это интересно. Я жду ответа 🫴")
        return

    thread_id = user_threads[user_id]

    try:
        # Добавляем сообщение пользователя в Thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message.text
        )

        # Создаем и запускаем Run, используя существующего ассистента
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Проверяем статус и отправляем ответ пользователю
        if run.status == 'completed':
            # Получаем все сообщения из потока
            thread_messages = client.beta.threads.messages.list(thread_id=thread_id)

            # Находим последнее сообщение ассистента
            assistant_message = None
            for msg in thread_messages:
                if msg.role == "assistant":
                    assistant_message = msg
                    break

            if assistant_message:
                # Извлекаем текст из сообщения ассистента
                response_text = ""
                for content_block in assistant_message.content:
                    if content_block.type == "text":
                        response_text += content_block.text.value

                # Проверяем на наличие ключевых слов
                if any(keyword in response_text.lower() for keyword in ["число твоей души", "число твоей личности", "число твоей судьбы"]):
                    # Сначала отправляем текст с эмодзи "🗝"
                    await message.answer("🗝")
                # Проверяем на наличие фразы "нажми кнопку"
                if "нажми кнопку" in response_text.lower():
                    # Добавляем инлайн кнопку
                    spin_button = InlineKeyboardButton(text="Крути колесо", callback_data="spin_wheel")
                    keyboard = InlineKeyboardBuilder()
                    keyboard.add(spin_button)
                    await message.answer(response_text, reply_markup=keyboard.as_markup())
                else:
                    # Отправляем извлеченный текст пользователю
                    await message.answer(response_text)
            else:
                await message.answer("Не удалось получить ответ от ассистента.")
        else:
            await message.answer("Ошибка: обработка не завершена.")
    except Exception as e:
        logging.error(f"Ошибка в обработке сообщения пользователя: {e}")
        await message.answer("Ошибка. Попробуйте позже.")

#Обработчик нажатия кнопки крути колесо
@dp.callback_query(lambda c: c.data == "spin_wheel")
async def handle_spin_wheel(callback_query: types.CallbackQuery):
    try:
        # Отправляем первое сообщение
        await callback_query.message.answer("Колесо Фортуны вращается...")
        await asyncio.sleep(3)  # Задержка в 3 секунды
        # Отправляем второе сообщение
        await callback_query.message.answer("Вы выиграли мини-курс по нумерологии")
    except Exception as e:
        logging.error(f"Ошибка в обработке callback_query: {e}")
        await callback_query.message.answer("Ошибка. Попробуйте позже.")

async def on_startup(bot: Bot):
    # Установка вебхука с использованием метода SetWebhook
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")



def main() -> None:

    dp.startup.register(on_startup)

    # Создаем aiohttp.web.Application
    app = web.Application()

    # Используем SimpleRequestHandler для регистрации пути вебхука и маршрутов
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Монтируем диспетчер к приложению
    setup_application(app, dp, bot=bot)

    # Запуск приложения на сервере
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(f"Произошла ошибка: {e}")
            logging.info("Перезапуск через 5 секунд...")
            time.sleep(5)
