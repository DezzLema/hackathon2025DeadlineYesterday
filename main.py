import asyncio
import logging
from bot_setup import setup_bot
from UlstuParser import UlstuParser
from config import ULSTU_USERNAME, ULSTU_PASSWORD, LOG_LEVEL

# Настраиваем логирование
logging.basicConfig(level=getattr(logging, LOG_LEVEL))


async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализируем парсер
        parser = UlstuParser()

        logging.info("🔐 Авторизация...")
        if parser.login(ULSTU_USERNAME, ULSTU_PASSWORD):
            logging.info("✅ Авторизация успешна!")
        else:
            logging.error("❌ Ошибка авторизации!")
            return

        # Настраиваем бота
        bot, dp = setup_bot()

        logging.info("✅ Бот запущен!")
        await dp.start_polling(bot)

    except Exception as e:
        logging.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        # Закрываем сессию при завершении
        if 'parser' in locals() and parser.session:
            parser.session.close()
            logging.info("👋 Сессия закрыта")


if __name__ == '__main__':
    asyncio.run(main())