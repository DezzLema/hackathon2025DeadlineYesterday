import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)


class StateService:
    def __init__(self):
        self.user_states: Dict[int, Dict[str, Any]] = {}

    def set_user_state(self, chat_id: int, state: str, data: Any = None):
        """Устанавливает состояние пользователя"""
        if chat_id not in self.user_states:
            self.user_states[chat_id] = {}

        self.user_states[chat_id]['current_state'] = state
        if data is not None:
            self.user_states[chat_id]['state_data'] = data

        logging.info(f"🔄 Установлено состояние '{state}' для пользователя {chat_id}")

    def get_user_state(self, chat_id: int) -> str:
        """Получает текущее состояние пользователя"""
        if chat_id in self.user_states:
            return self.user_states[chat_id].get('current_state')
        return None

    def get_user_state_data(self, chat_id: int) -> Any:
        """Получает данные состояния пользователя"""
        if chat_id in self.user_states:
            return self.user_states[chat_id].get('state_data')
        return None

    def clear_user_state(self, chat_id: int):
        """Очищает состояние пользователя"""
        if chat_id in self.user_states:
            del self.user_states[chat_id]
            logging.info(f"🔄 Очищено состояние пользователя {chat_id}")

    def is_awaiting_group_input(self, chat_id: int) -> bool:
        """Проверяет, ожидает ли бот ввода группы"""
        return self.get_user_state(chat_id) == 'awaiting_group_input'

    def is_awaiting_teacher_input(self, chat_id: int) -> bool:
        """Проверяет, ожидает ли бот ввода преподавателя"""
        return self.get_user_state(chat_id) == 'awaiting_teacher_input'


# Глобальный экземпляр сервиса состояний
state_service = StateService()