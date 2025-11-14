import asyncio
import logging
import os
from maxapi import Bot, Dispatcher

from config.config import BOT_TOKEN
from handlers.commands import register_command_handlers
from handlers.callbacks import register_callback_handlers
from handlers.messages import register_message_handlers
from services.schedule_service import ScheduleService
from services.user_service import UserService
from config import *
from database.database import user_db

logging.basicConfig(level=logging.INFO)

# Создаем экземпляры сервисов
schedule_service = ScheduleService()
user_service = UserService()

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


async def main():
    try:

        # Регистрируем все обработчики
        register_command_handlers(dp, bot, schedule_service, user_service)
        register_callback_handlers(dp, bot, schedule_service, user_service)
        register_message_handlers(dp, bot, schedule_service, user_service)

        # Проверяем базу данных перед запуском
        logging.info("🔍 Проверяем базу данных...")
        if not user_db.check_database_health():
            logging.error("❌ Проблемы с базой данных, пытаемся восстановить...")
            user_db.force_recreate_database()

        logging.info("✅ Бот запущен!")
        await dp.start_polling(bot)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
    finally:
        if schedule_service.parser.session:
            schedule_service.parser.session.close()


if __name__ == '__main__':
    asyncio.run(main())