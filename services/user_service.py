import logging
from database.database import user_db
from keyboards.student_menu import send_student_menu
from keyboards.inline_keyboards import get_back_button
from services.state_service import state_service

logging.basicConfig(level=logging.INFO)


class UserService:
    def __init__(self):
        pass

    def clear_temp_states(self, chat_id):
        """Очищает временные состояния пользователя"""
        state_service.clear_user_state(chat_id)

    async def process_role_selection(self, bot, chat_id, role):
        """Обрабатывает выбор роли пользователем и сохраняет в БД"""
        try:
            current_user_info = user_db.get_user(chat_id)

            if current_user_info:
                current_role = current_user_info[1]
                current_group = current_user_info[2]

                if current_role == "student" and role != "student":
                    user_db.add_or_update_user(chat_id, role, None)
                    logging.info(
                        f"🔄 Пользователь {chat_id} сменил роль с '{current_role}' на '{role}', группа сброшена")
                else:
                    user_db.add_or_update_user(chat_id, role, current_group)
                    logging.info(f"🔄 Пользователь {chat_id} сменил роль с '{current_role}' на '{role}'")
            else:
                user_db.add_or_update_user(chat_id, role)
                logging.info(f"👤 Новый пользователь {chat_id} с ролью '{role}'")

            self.clear_temp_states(chat_id)

            # Отправляем соответствующее меню
            if role == "student":
                await send_student_menu(bot, chat_id)
            elif role == "abiturient":
                await self.send_abiturient_menu(bot, chat_id)
            elif role == "teacher":
                await self.send_teacher_menu(bot, chat_id)

        except Exception as e:
            logging.error(f"❌ Ошибка при обработке выбора роли: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка при выборе роли")

    async def send_abiturient_menu(self, bot, chat_id):
        """Отправляет меню для абитуриентов"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="📚 Информация для поступления", payload="abiturient_info"),
        )
        builder.row(
            CallbackButton(text="💬 Чаты факультетов", payload="abiturient_chats"),
        )
        builder.row(get_back_button())

        await bot.send_message(
            chat_id=chat_id,
            text="Вы выбрали роль: Абитуриент\n\nВыберите нужный раздел:",
            attachments=[builder.as_markup()]
        )

    async def send_teacher_menu(self, bot, chat_id):
        """Отправляет меню для преподавателей"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        builder = InlineKeyboardBuilder()
        builder.row(
            get_back_button(),
            CallbackButton(text="📅 Получить расписание", payload="teacher_schedule")
        )
        await bot.send_message(
            chat_id=chat_id,
            text="Вы выбрали роль: Преподаватель\n\nЗдесь вы можете получить информацию о:\n\n• Расписании занятий\n• Учебном процессе\n• Методических материалах\n\nДля справки используйте команду /help",
            attachments=[builder.as_markup()]
        )

    async def send_profile_info(self, bot, chat_id):
        """Показывает профиль пользователя"""
        user_info = user_db.get_user(chat_id)

        if user_info:
            user_id, role, group_name = user_info

            profile_text = f"👤 *Ваш профиль*\n\n"
            profile_text += f"🆔 ID: `{user_id}`\n"
            profile_text += f"🎭 Роль: {role}\n"

            if group_name:
                profile_text += f"📚 Группа: {group_name}\n\n"
                profile_text += f"💡 *Быстрые команды:*\n"
                profile_text += f"• Нажмите '📅 Расписание' для расписания вашей группы\n"
                profile_text += f"• `/group {group_name}` - тоже самое через команду"
            else:
                profile_text += f"📚 Группа: не установлена\n\n"
                profile_text += f"💡 *Чтобы установить группу:*\n"
                profile_text += f"• Нажмите '📅 Расписание' и введите название группы\n"
                profile_text += f"• Используйте `/group <название>`"
        else:
            profile_text = "❌ Профиль не найден.\nИспользуйте /start для начала работы."

        await bot.send_message(chat_id=chat_id, text=profile_text)

    async def send_help_info(self, bot, chat_id):
        """Отправляет справку"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        user_info = user_db.get_user(chat_id)

        if user_info:
            user_id, role, group_name = user_info
            status = role
            group_info = f", группа: {group_name}" if group_name else ""
        else:
            status = "не выбрана"
            group_info = ""

        help_text = f"ℹ️ *Справка:*\n\n👤 Ваш статус: {status}{group_info}\n\n*Основные команды:*\n"
        help_text += "/start - Выбор роли и начало работы\n"
        help_text += "/help - Эта справка\n"
        help_text += "/profile - Показать ваш профиль\n\n"

        if status == "student":
            help_text += "*📚 Команды для студентов:*\n"
            help_text += "/group <название> - Расписание конкретной группы\n"
            help_text += "/groups - Список доступных групп\n"
            help_text += "/search <часть названия> - Поиск группы по названию\n"
            help_text += "*💡 Примеры использования:*\n"
            help_text += "`/group ИВТИИбд-32` - расписание группы ИВТИИбд-32\n"
            help_text += "`/search ИВТ` - поиск всех групп с 'ИВТ' в названии\n"
            help_text += "`/groups` - просмотр всех доступных групп"

            if group_name:
                help_text += f"\n\n*🎯 Ваша сохраненная группа:* {group_name}"
                help_text += f"\nИспользуйте кнопку '📅 Расписание' для быстрого доступа"

        builder = InlineKeyboardBuilder()
        builder.row(get_back_button())

        await bot.send_message(
            chat_id=chat_id,
            text=help_text,
            attachments=[builder.as_markup()]
        )