import openai
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Замените на ваши ключи и ID
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Настройка клиента OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Хранилище thread_id для каждого пользователя
user_threads = {}

@dp.message(Command("start"))
async def start_command(message: types.Message):
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
async def handle_message(message: types.Message):
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
                # Отправляем извлеченный текст пользователю
                await message.answer(response_text)
            else:
                await message.answer("Не удалось получить ответ от ассистента.")
        else:
            await message.answer("Ошибка: обработка не завершена.")
    except Exception as e:
        logging.error(f"Ошибка в обработке сообщения пользователя: {e}")
        await message.answer("Ошибка. Попробуйте позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
