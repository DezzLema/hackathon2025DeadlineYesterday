import logging
import os
from maxapi.types import BotStarted, Command, MessageCreated, InputMediaBuffer
from UlstuParser import UlstuParser
from config import SCHEDULE_URL

# Создаем парсер
parser = UlstuParser()


async def send_table_image(bot, chat_id):
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


async def generate_and_send_table(bot, chat_id):
    """Генерирует расписание и отправляет его в чат"""
    try:
        await bot.send_message(chat_id=chat_id, text="🔄 Генерирую расписание...")

        # Генерируем расписание
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)

        # Конвертируем в bytes и сохраняем
        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open("schedule.png", "wb") as f:
            f.write(image_bytes_io.getvalue())

        # Отправляем изображение
        with open("schedule.png", "rb") as file:
            image_data = file.read()

        input_media = InputMediaBuffer(
            buffer=image_data,
            filename="schedule.png"
        )

        await bot.send_message(
            chat_id=chat_id,
            text="📅 Ваше расписание",
            attachments=[input_media]
        )

        logging.info("✅ Расписание сгенерировано и отправлено")

    except Exception as e:
        logging.error(f"❌ Ошибка при генерации расписания: {e}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при генерации расписания")


async def bot_started_handler(bot, event: BotStarted):
    """Обработчик события запуска бота"""
    try:
        await bot.send_message(chat_id=event.chat_id, text="🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)
        await send_table_image(bot, event.chat_id)
    except Exception as e:
        await bot.send_message(chat_id=event.chat_id, text="❌ Ошибка при запуске")


async def start_handler(bot, event: MessageCreated):
    """Обработчик команды /start"""
    try:
        await event.message.answer("🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)

        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open("schedule.png", "wb") as f:
            f.write(image_bytes_io.getvalue())

        await event.message.answer("📅 *Расписание готово!*\nФайл сохранен как 'schedule.png'")

    except Exception as e:
        await event.message.answer("❌ Ошибка при получении расписания")


async def table_handler(bot, event: MessageCreated):
    """Обработчик команды /table - генерирует и отправляет расписание"""
    logging.info("🔄 Обработчик /table вызван")
    try:
        # Получаем chat_id из event.message.recipient.chat_id
        chat_id = event.message.recipient.chat_id
        logging.info(f"🔄 Генерирую расписание для chat_id: {chat_id}")

        await generate_and_send_table(bot, chat_id)
        logging.info("✅ generate_and_send_table завершен")

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /table: {e}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await event.message.answer("❌ Ошибка при генерации расписания")


async def debug_handler(bot, event: MessageCreated):
    """Обработчик команды /debug - показывает отладочную информацию"""
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


async def help_handler(bot, event: MessageCreated):
    """Обработчик команды /help"""
    await event.message.answer(
        "ℹ️ *Команды:*\n"
        "/start - Создать и сохранить расписание\n"
        "/table - Сгенерировать и получить расписание в виде изображения\n"
        "/debug - Отладочная информация\n"
        "/help - Справка"
    )


async def message_handler(bot, event: MessageCreated):
    """Обработчик обычных сообщений"""
    try:
        text = event.message.content.text.strip()
        if text and not text.startswith('/'):
            await event.message.answer(
                "🤔 Используйте /start для создания расписания или /table для получения изображения")
    except Exception as e:
        logging.error(f"Ошибка: {e}")