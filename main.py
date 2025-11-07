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


async def generate_and_send_table(chat_id, group_number=None):
    """Генерирует расписание и отправляет его в чат"""
    try:
        if group_number:
            await bot.send_message(chat_id=chat_id, text=f"🔄 Генерирую расписание для группы {group_number}...")
            schedule_image = parser.get_schedule_image_by_number(group_number)
            filename = f"schedule_group_{group_number}.png"
        else:
            await bot.send_message(chat_id=chat_id, text="🔄 Генерирую расписание...")
            schedule_image = parser.get_schedule_image(parser.get_group_url(61))  # группа по умолчанию
            filename = "schedule.png"

        # Конвертируем в bytes и сохраняем
        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open(filename, "wb") as f:
            f.write(image_bytes_io.getvalue())

        # Отправляем изображение
        with open(filename, "rb") as file:
            image_data = file.read()

        input_media = InputMediaBuffer(
            buffer=image_data,
            filename=filename
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


# Обработчики команд
@dp.bot_started()
async def bot_started(event: BotStarted):
    try:
        await bot.send_message(chat_id=event.chat_id, text="🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(parser.get_group_url(61))
        await send_table_image(event.chat_id)
    except Exception as e:
        await bot.send_message(chat_id=event.chat_id, text="❌ Ошибка при запуске")


@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    try:
        await event.message.answer("🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(parser.get_group_url(61))

        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open("schedule.png", "wb") as f:
            f.write(image_bytes_io.getvalue())

        await event.message.answer("📅 *Расписание готово!*\nФайл сохранен как 'schedule.png'")

    except Exception as e:
        await event.message.answer("❌ Ошибка при получении расписания")


@dp.message_created(Command('table'))
async def send_table_command(event: MessageCreated):
    """Обработчик команды /table - генерирует и отправляет расписание"""
    logging.info("🔄 Обработчик /table вызван")
    try:
        # Получаем chat_id из event.message.recipient.chat_id
        chat_id = event.message.recipient.chat_id
        logging.info(f"🔄 Генерирую расписание для chat_id: {chat_id}")

        await generate_and_send_table(chat_id)
        logging.info("✅ generate_and_send_table завершен")

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /table: {e}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await event.message.answer("❌ Ошибка при генерации расписания")


@dp.message_created(Command('group'))
async def group_command(event: MessageCreated):
    """Обработчик команды /group <номер> - расписание конкретной группы"""
    try:
        # Получаем текст команды из event
        command_text = event.message.body.text.strip()
        parts = command_text.split()

        if len(parts) < 2:
            await event.message.answer(
                "❌ Укажите номер группы\n"
                f"Пример: `/group 61`\n"
                f"Доступные группы: от {MIN_GROUP_NUMBER} до {MAX_GROUP_NUMBER}"
            )
            return

        group_number = int(parts[1])

        if group_number < MIN_GROUP_NUMBER or group_number > MAX_GROUP_NUMBER:
            await event.message.answer(
                f"❌ Номер группы должен быть от {MIN_GROUP_NUMBER} до {MAX_GROUP_NUMBER}"
            )
            return

        chat_id = event.message.recipient.chat_id
        await generate_and_send_table(chat_id, group_number)

    except ValueError:
        await event.message.answer("❌ Номер группы должен быть числом")
    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /group: {e}")
        await event.message.answer("❌ Ошибка при получении расписания группы")


@dp.message_created(Command('groups'))
async def groups_command(event: MessageCreated):
    """Обработчик команды /groups - информация о доступных группах"""
    try:
        groups_info = (
            f"📚 *Доступные группы:*\n\n"
            f"• Номера групп: от {MIN_GROUP_NUMBER} до {MAX_GROUP_NUMBER}\n"
            f"• Всего групп: {MAX_GROUP_NUMBER - MIN_GROUP_NUMBER + 1}\n\n"
            f"*Команды:*\n"
            f"`/group <номер>` - расписание конкретной группы\n"
            f"`/table` - расписание группы по умолчанию\n"
            f"`/search <название>` - поиск группы по названию\n\n"
            f"*Пример:* `/group 61`"
        )

        await event.message.answer(groups_info)

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /groups: {e}")
        await event.message.answer("❌ Ошибка при получении информации о группах")


@dp.message_created(Command('search'))
async def search_command(event: MessageCreated):
    """Обработчик команды /search - поиск группы по названию"""
    try:
        # Получаем текст команды из event
        command_text = event.message.content.text.strip()
        parts = command_text.split()

        if len(parts) < 2:
            await event.message.answer(
                "❌ Укажите название группы для поиска\n"
                "Пример: `/search ИВТ`"
            )
            return

        search_query = ' '.join(parts[1:]).upper()
        await event.message.answer(f"🔍 Ищу группы содержащие: {search_query}\n\n*Это может занять некоторое время...*")

        # Парсим все группы для поиска
        all_groups = parser.parse_all_groups()

        found_groups = []
        for group_num, group_data in all_groups.items():
            if search_query in group_data['name'].upper():
                found_groups.append((group_num, group_data['name']))

        if found_groups:
            groups_text = "🎯 *Найденные группы:*\n\n"
            for group_num, group_name in found_groups[:10]:  # Показываем первые 10
                groups_text += f"• {group_name} (№{group_num})\n"
                groups_text += f"  Используйте: `/group {group_num}`\n\n"

            if len(found_groups) > 10:
                groups_text += f"*... и еще {len(found_groups) - 10} групп*"

            await event.message.answer(groups_text)
        else:
            await event.message.answer(f"❌ Группы содержащие '{search_query}' не найдены")

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /search: {e}")
        await event.message.answer("❌ Ошибка при поиске групп")


@dp.message_created(Command('debug'))
async def debug_info(event: MessageCreated):
    """Показывает отладочную информацию"""
    try:
        group_name, week_number, schedules = parser.parse_group_schedule(parser.get_group_url(61))

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
        "/start - Создать и сохранить расписание\n"
        "/table - Расписание группы по умолчанию\n"
        "/group <номер> - Расписание конкретной группы\n"
        "/groups - Список доступных групп\n"
        "/search <название> - Поиск группы по названию\n"
        "/debug - Отладочная информация\n"
        "/help - Справка"
    )


@dp.message_created()
async def handle_message(event: MessageCreated):
    try:
        text = event.message.content.text.strip()
        if text and not text.startswith('/'):
            await event.message.answer(
                "🤔 Используйте /start для создания расписания или /table для получения изображения"
            )
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