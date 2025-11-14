import logging
from maxapi.types import MessageCreated, Command, BotStarted
from services.schedule_service import ScheduleService
from services.user_service import UserService
from keyboards.main_menu import send_welcome_message
from keyboards.student_menu import send_student_menu

logging.basicConfig(level=logging.INFO)


def register_command_handlers(dp, bot, schedule_service: ScheduleService, user_service: UserService):
    @dp.bot_started()
    async def bot_started(event: BotStarted):
        try:
            await send_welcome_message(bot, event.chat_id)
        except Exception as e:
            await bot.send_message(chat_id=event.chat_id, text="❌ Ошибка при запуске")

    @dp.message_created(Command('start'))
    async def start_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            user_service.clear_temp_states(chat_id)
            await send_welcome_message(bot, chat_id)
        except Exception as e:
            await event.message.answer("❌ Ошибка при запуске")

    @dp.message_created(Command('student'))
    async def student_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            await user_service.process_role_selection(bot, chat_id, "student")
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике /student: {e}")
            await event.message.answer("❌ Ошибка при выборе роли")

    @dp.message_created(Command('abiturient'))
    async def abiturient_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            await user_service.process_role_selection(bot, chat_id, "abiturient")
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике /abiturient: {e}")
            await event.message.answer("❌ Ошибка при выборе роли")

    @dp.message_created(Command('teacher'))
    async def teacher_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            await user_service.process_role_selection(bot, chat_id, "teacher")
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике /teacher: {e}")
            await event.message.answer("❌ Ошибка при выборе роли")

    @dp.message_created(Command('group'))
    async def group_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            command_text = event.message.body.text.strip()
            parts = command_text.split()

            if len(parts) < 2:
                await event.message.answer(
                    "❌ Укажите название группы\n"
                    f"Пример: `/group ИВТИИбд-32`"
                )
                return

            group_name = ' '.join(parts[1:]).strip()
            await schedule_service.handle_group_command(bot, chat_id, group_name)

        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике /group: {e}")
            await event.message.answer("❌ Ошибка при поиске группы")

    @dp.message_created(Command('groups'))
    async def groups_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            await schedule_service.send_groups_info(bot, chat_id)
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике /groups: {e}")
            await event.message.answer("❌ Ошибка при получении информации о группах")

    @dp.message_created(Command('search'))
    async def search_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            command_text = event.message.body.text.strip()
            parts = command_text.split()

            if len(parts) < 2:
                await event.message.answer(
                    "❌ Укажите часть названия группы для поиска\n"
                    "Пример: `/search ИВТ` или `/search ПИ`"
                )
                return

            search_query = ' '.join(parts[1:]).upper()
            await schedule_service.handle_search_command(bot, chat_id, search_query)

        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике /search: {e}")
            await event.message.answer("❌ Ошибка при поиске групп")

    @dp.message_created(Command('profile'))
    async def profile_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            await user_service.send_profile_info(bot, chat_id)
        except Exception as e:
            logging.error(f"❌ Ошибка в команде /profile: {e}")
            await event.message.answer("❌ Ошибка при получении профиля")

    @dp.message_created(Command('help'))
    async def help_command(event: MessageCreated):
        try:
            chat_id = event.message.recipient.chat_id
            await user_service.send_help_info(bot, chat_id)
        except Exception as e:
            logging.error(f"❌ Ошибка в команде /help: {e}")
            await event.message.answer("❌ Ошибка при получении справки")