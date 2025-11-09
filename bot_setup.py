from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated
from handlers import (
    bot_started_handler, start_handler, table_handler,
    debug_handler, help_handler, message_handler,
    group_handler, groups_handler, search_handler  # Добавьте новые импорты
)
from config import BOT_TOKEN

def setup_bot():
    """Настройка бота и регистрация обработчиков"""
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем обработчики
    @dp.bot_started()
    async def handle_bot_started(event: BotStarted):
        await bot_started_handler(bot, event)

    @dp.message_created(Command('start'))
    async def handle_start(event: MessageCreated):
        await start_handler(bot, event)

    @dp.message_created(Command('table'))
    async def handle_table(event: MessageCreated):
        await table_handler(bot, event)

    @dp.message_created(Command('group'))
    async def handle_group(event: MessageCreated):  # Новый обработчик
        await group_handler(bot, event)

    @dp.message_created(Command('groups'))
    async def handle_groups(event: MessageCreated):  # Новый обработчик
        await groups_handler(bot, event)

    @dp.message_created(Command('search'))
    async def handle_search(event: MessageCreated):  # Новый обработчик
        await search_handler(bot, event)

    @dp.message_created(Command('debug'))
    async def handle_debug(event: MessageCreated):
        await debug_handler(bot, event)

    @dp.message_created(Command('help'))
    async def handle_help(event: MessageCreated):
        await help_handler(bot, event)

    @dp.message_created()
    async def handle_message(event: MessageCreated):
        await message_handler(bot, event)

    return bot, dp