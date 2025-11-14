import logging
from maxapi.types import MessageCallback

from state_service import state_service
from services.schedule_service import ScheduleService
from services.user_service import UserService
from keyboards.student_menu import send_student_menu
from keyboards.main_menu import send_welcome_message

logging.basicConfig(level=logging.INFO)


def register_callback_handlers(dp, bot, schedule_service: ScheduleService, user_service: UserService):
    @dp.message_callback()
    async def handle_callback(event: MessageCallback):
        try:
            chat_id = event.message.recipient.chat_id
            payload = event.callback.payload

            logging.info(f"🔍 Callback получен: chat_id={chat_id}, payload={payload}")

            if payload and payload.startswith("role_"):
                role = payload.split("_")[1]
                await user_service.process_role_selection(bot, chat_id, role)

            elif payload == "teacher_schedule":
                state_service.set_user_state(chat_id, 'awaiting_teacher_input')
                await schedule_service.send_teacher_input_prompt(bot, chat_id)

            elif payload == "student_menu":
                await send_student_menu(bot, chat_id)

            elif payload == "student_schedule":
                await schedule_service.handle_student_schedule_callback(bot, chat_id)

            elif payload == "back_to_main":
                user_service.clear_temp_states(chat_id)
                await send_welcome_message(bot, chat_id)

            elif payload == "back_to_student_menu":
                user_service.clear_temp_states(chat_id)
                await send_student_menu(bot, chat_id)

            else:
                # Обработка остальных callback-ов
                await handle_other_callbacks(bot, chat_id, payload)

        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике callback: {e}")
            try:
                await bot.send_message(
                    chat_id=event.message.recipient.chat_id,
                    text="❌ Ошибка при обработке выбора"
                )
            except:
                pass

    async def handle_other_callbacks(bot, chat_id, payload):
        """Обработка остальных callback-пейлоадов"""
        callback_handlers = {
            "profkom_staff": lambda: schedule_service.send_profkom_staff_info(bot, chat_id),
            "profkom_payments": lambda: schedule_service.send_profkom_payments_info(bot, chat_id),
            "profkom_contacts": lambda: schedule_service.send_profkom_contacts_info(bot, chat_id),
            "student_scholarship": lambda: schedule_service.send_scholarship_info(bot, chat_id),
            "student_life": lambda: schedule_service.send_student_life_info(bot, chat_id),
            "scholarship_students": lambda: schedule_service.send_scholarship_students_info(bot, chat_id),
            "scholarship_masters": lambda: schedule_service.send_scholarship_masters_info(bot, chat_id),
            "scholarship_phd": lambda: schedule_service.send_scholarship_phd_info(bot, chat_id),
            "scholarship_college": lambda: schedule_service.send_scholarship_college_info(bot, chat_id),
            "scholarship_increased": lambda: schedule_service.send_scholarship_increased_info(bot, chat_id),
            "student_dormitory": lambda: schedule_service.send_dormitory_info(bot, chat_id),
            "dormitory_provision": lambda: schedule_service.send_dormitory_provision_info(bot, chat_id),
            "dormitory_contacts": lambda: schedule_service.send_dormitory_contacts_info(bot, chat_id),
            "student_media": lambda: schedule_service.send_student_media_info(bot, chat_id),
            "student_volunteer": lambda: schedule_service.send_student_volunteer_info(bot, chat_id),
            "student_teams": lambda: schedule_service.send_student_teams_info(bot, chat_id),
            "abiturient_info": lambda: schedule_service.send_abiturient_info(bot, chat_id),
            "abiturient_chats": lambda: schedule_service.send_abiturient_chats(bot, chat_id),
            "back_to_abiturient_menu": lambda: user_service.process_role_selection(bot, chat_id, "abiturient"),
            "student_events": lambda: schedule_service.send_events_info(bot, chat_id),
            "student_certificate": lambda: schedule_service.send_certificate_info(bot, chat_id),
            "student_profkom": lambda: schedule_service.send_profkom_info(bot, chat_id),
            "student_career": lambda: schedule_service.send_career_center_info(bot, chat_id),
            "back_to_profkom": lambda: schedule_service.send_profkom_info(bot, chat_id),
            "enter_group_name": lambda: schedule_service.handle_enter_group_name(bot, chat_id),
            "search_group": lambda: schedule_service.handle_search_group(bot, chat_id),
        }

        if payload in callback_handlers:
            await callback_handlers[payload]()
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Неизвестный callback"
            )