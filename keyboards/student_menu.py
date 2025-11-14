from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton

async def send_student_menu(bot, chat_id):
    """Отправляет меню для студентов с восемью кнопками"""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="📅 Получить расписание", payload="student_schedule"),
    )
    builder.row(
        CallbackButton(text="💰 Стипендиальные выплаты", payload="student_scholarship"),
        CallbackButton(text="🏠 Общежитие", payload="student_dormitory"),
    )
    builder.row(
        CallbackButton(text="🎓 Студенческая жизнь", payload="student_life"),
        CallbackButton(text="💼 Центр Карьеры", payload="student_career"),
    )
    builder.row(
        CallbackButton(text="🎭 Мероприятия", payload="student_events"),
    )
    builder.row(
        CallbackButton(text="📄 Заказ справки", payload="student_certificate"),
    )
    builder.row(
        CallbackButton(text="👥 Профком", payload="student_profkom"),
    )
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_main"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text="🎓 Студенческое меню \n\nВыберите нужный раздел:",
        attachments=[builder.as_markup()]
    )