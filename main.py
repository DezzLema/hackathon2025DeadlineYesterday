import asyncio
import logging
import os
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated, InputMediaBuffer
from UlstuParser import UlstuParser
from config import *

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Создаем парсер
parser = UlstuParser()

async def send_table_image(chat_id):
    """Отправляет существующий PNG файл с расписанием в чат"""
    logging.info("🔍 Начало send_table_image")
    try:
        # Проверяем, существует ли файл schedule.png
        if not os.path.exists("schedule.png"):
            logging.warning("❌ Файл schedule.png не найден")
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Файл расписания не найден. Сначала используйте /start для создания расписания."
            )
            return

        logging.info("✅ Файл schedule.png найден")

        with open("schedule.png", "rb") as file:
            image_data = file.read()

        logging.info("✅ Файл прочитан в память")

        input_media = InputMediaBuffer(
            buffer=image_data,
            filename="schedule.png"
        )

        logging.info("✅ InputMediaBuffer создан")

        # Отправляем сообщение
        await bot.send_message(
            chat_id=chat_id,
            text="📅 Ваше расписание",
            attachments=[input_media]
        )

        logging.info("✅ Изображение отправлено в чат")

    except Exception as e:
        logging.error(f"❌ Ошибка в send_table_image: {e}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при отправке расписания")

    except Exception as e:
        logging.error(f"❌ Ошибка при отправке изображения: {e}")
        logging.error(f"❌ Тип ошибки: {type(e).__name__}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при отправке расписания")


# Обработчики команд
@dp.bot_started()
async def bot_started(event: BotStarted):
    try:
        await bot.send_message(chat_id=event.chat_id, text="🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)
        await send_table_image(event.chat_id)
    except Exception as e:
        await bot.send_message(chat_id=event.chat_id, text="❌ Ошибка при запуске")


@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    try:
        await event.message.answer("🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)

        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open("schedule.png", "wb") as f:
            f.write(image_bytes_io.getvalue())

        await event.message.answer("📅 *Расписание готово!*\nФайл сохранен как 'schedule.png'")

    except Exception as e:
        await event.message.answer("❌ Ошибка при получении расписания")


@dp.message_created(Command('table'))
async def send_table_command(event: MessageCreated):
    """Обработчик команды /table - отправляет существующий PNG с расписанием"""
    logging.info("🔄 Обработчик /table вызван")
    try:
        await event.message.answer("🔄 Отправляю изображение расписания...")

        # Получаем chat_id из event.message.recipient.chat_id
        chat_id = event.message.recipient.chat_id
        logging.info(f"🔄 Вызываю send_table_image с chat_id: {chat_id}")

        await send_table_image(chat_id)
        logging.info("✅ send_table_image завершен")

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /table: {e}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await event.message.answer("❌ Ошибка при отправке расписания")


@dp.message_created(Command('debug'))
async def debug_info(event: MessageCreated):
    """Показывает отладочную информацию"""
    try:
        group_name, week_number, schedules = parser.parse_group_schedule(SCHEDULE_URL)

        debug_text = f"""
🔍 *Отладочная информация:*

📊 Группа: {group_name}
📅 Неделя: {week_number}
📚 Занятий: {len(schedules)}

📋 *Расписание:*
"""

        if schedules:
            for lesson in schedules[:10]:  # Показываем первые 10 занятий
                debug_text += f"""
{lesson['day']} {lesson['pair']} пара: {lesson['subject']}
   Тип: {lesson['type']}
   Преп: {lesson['teacher']}
   Ауд: {lesson['classroom']}
"""
        else:
            debug_text += "\n❌ Занятия не найдены"

        await event.message.answer(debug_text)

    except Exception as e:
        await event.message.answer(f"❌ Ошибка отладки: {e}")


@dp.message_created(Command('help'))
async def help_command(event: MessageCreated):
    await event.message.answer(
        "ℹ️ *Команды:*\n"
        "/start - Создать и получить расписание\n"
        "/table - Получить расписание в виде изображения (требует /start)\n"
        "/debug - Отладочная информация\n"
        "/help - Справка"
    )


@dp.message_created()
async def handle_message(event: MessageCreated):
    try:
        text = event.message.content.text.strip()
        if text and not text.startswith('/'):
            await event.message.answer(
                "🤔 Используйте /start для создания расписания или /table для получения изображения")
    except Exception as e:
        logging.error(f"Ошибка: {e}")


async def main():
    try:
        logging.info("🔐 Авторизация...")
        if parser.login(ULSTU_USERNAME, ULSTU_PASSWORD):
            logging.info("✅ Бот запущен!")
        else:
            logging.error("❌ Ошибка авторизации!")

        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
    finally:
        if parser.session:
            parser.session.close()


if __name__ == '__main__':
    asyncio.run(main())
