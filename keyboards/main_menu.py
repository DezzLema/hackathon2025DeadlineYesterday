from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton

async def send_welcome_message(bot, chat_id):
    """Отправляет приветственное сообщение с кнопками выбора роли"""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="👨‍🎓 Абитуриент", payload="role_abiturient"),
        CallbackButton(text="👨‍🎓 Студент", payload="role_student"),
    )
    builder.row(
        CallbackButton(text="👨‍🏫 Преподаватель", payload="role_teacher"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text="🎓 Добро пожаловать в нашего бота - Цифровой вуз!\n\n"
             "Выбери нужный вариант:\n",
        attachments=[builder.as_markup()]
    )