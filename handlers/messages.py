import logging
from maxapi.types import MessageCreated
from services.schedule_service import ScheduleService
from services.user_service import UserService
from state_service import state_service

logging.basicConfig(level=logging.INFO)


def register_message_handlers(dp, bot, schedule_service: ScheduleService, user_service: UserService):
    @dp.message_created()
    async def handle_message(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            text = event.message.body.text.strip() if event.message.body.text else ""

            # Проверяем, ожидаем ли мы ввод названия группы
            if state_service.is_awaiting_group_input(chat_id):
                await schedule_service.handle_group_input(bot, chat_id, text)
                return

            # Проверяем, ожидаем ли мы ввод фамилии преподавателя
            elif state_service.is_awaiting_teacher_input(chat_id):
                await schedule_service.handle_teacher_input(bot, chat_id, text)
                return

            elif text and not text.startswith('/'):
                # Обычное сообщение без команды
                await bot.send_message(
                    chat_id=chat_id,
                    text="🤔 Используйте /start для выбора роли или /help для справки\n\n"
                         "*📚 Для студентов:*\n"
                         "• Нажмите кнопку '📅 Расписание' для получения расписания\n"
                         "• `/groups` - список всех групп\n"
                         "• `/search` - поиск по названию"
                )

        except Exception as e:
            logging.error(f"Ошибка в обработчике сообщений: {e}")