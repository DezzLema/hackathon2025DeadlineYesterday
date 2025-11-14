from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton


def get_back_button():
    """Возвращает кнопку 'Назад' в главное меню"""
    return CallbackButton(text="🔙 Назад", payload="back_to_main")


def get_back_to_student_menu_button():
    """Возвращает кнопку 'Назад' в меню студента"""
    return CallbackButton(text="🔙 Назад", payload="back_to_student_menu")


def get_back_to_profkom_button():
    """Возвращает кнопку 'Назад' в меню профкома"""
    return CallbackButton(text="🔙 Назад", payload="back_to_profkom")


def get_back_to_profkom_button():
    """Возвращает кнопку 'Назад' в меню профкома"""
    return CallbackButton(text="🔙 Назад", payload="back_to_profkom")


def get_back_to_abiturient_menu_button():
    """Возвращает кнопку 'Назад' в меню абитуриента"""
    return CallbackButton(text="🔙 Назад", payload="back_to_abiturient_menu")


def get_back_to_group_selection_button():
    """Возвращает кнопку 'Назад' к выбору группы"""
    return CallbackButton(text="🔙 Назад", payload="back_to_group_selection")
