import logging
import os
from maxapi.types import InputMediaBuffer
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton
from state_service import state_service

from UlstuParser import UlstuParser
from groups_dict import GROUPS_DICT
from config import *
from database import user_db
from keyboards.inline_keyboards import get_back_button, get_back_to_student_menu_button, get_back_to_profkom_button
from services.user_service import UserService

logging.basicConfig(level=logging.INFO)

SCHEDULE_DIR = "schedule"


class ScheduleService:
    def __init__(self):
        self.parser = UlstuParser()
        self.user_service = UserService()
        self._ensure_schedule_dir()

        # Авторизация при создании сервиса
        if not self.parser.login(ULSTU_USERNAME, ULSTU_PASSWORD):
            logging.error("❌ Ошибка авторизации в UlstuParser!")

    def _ensure_schedule_dir(self):
        """Создает папку для расписаний если её нет"""
        if not os.path.exists(SCHEDULE_DIR):
            os.makedirs(SCHEDULE_DIR)

    async def send_table_image(self, bot, chat_id):
        """Отправляет существующий PNG файл с расписанием в чат"""
        logging.info("🔍 Начало send_table_image")
        try:
            schedule_path = os.path.join(SCHEDULE_DIR, "schedule.png")
            if not os.path.exists(schedule_path):
                logging.warning("❌ Файл schedule.png не найден")
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ Файл расписания не найден. Сначала используйте /start для создания расписания."
                )
                return

            logging.info("✅ Файл schedule.png найден")

            with open(schedule_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="schedule.png"
            )

            await bot.send_message(
                chat_id=chat_id,
                text="📅 Ваше расписание",
                attachments=[input_media]
            )

            logging.info("✅ Изображение отправлено в чат")

        except Exception as e:
            logging.error(f"❌ Ошибка в send_table_image: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка при отправке расписания")

    async def generate_and_send_table(self, bot, chat_id, group_number=None):
        """Генерирует расписание и отправляет его в чат"""
        try:
            if group_number:
                group_name = self.parser.get_group_name(group_number)
                schedule_image = self.parser.get_schedule_image_by_number(group_number)
                filename = f"schedule_group_{group_number}.png"
            else:
                await bot.send_message(chat_id=chat_id, text="🔄 Генерирую расписание...")
                schedule_image = self.parser.get_schedule_image_by_number(175)
                filename = "schedule.png"

            file_path = os.path.join(SCHEDULE_DIR, filename)

            image_bytes_io = self.parser.image_generator.image_to_bytes(schedule_image)
            with open(file_path, "wb") as f:
                f.write(image_bytes_io.getvalue())

            with open(file_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename=filename
            )

            group_display_name = self.parser.get_group_name(group_number) if group_number else "ИВТИИбд-31"

            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_student_menu_button())

            await bot.send_message(
                chat_id=chat_id,
                text=f"📅 Расписание группы {group_display_name}",
                attachments=[input_media, builder.as_markup()]
            )

            logging.info(f"✅ Расписание сгенерировано и сохранено в {file_path}")

        except Exception as e:
            logging.error(f"❌ Ошибка при генерации расписания: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка при генерации расписания")

    # Добавьте здесь остальные методы для работы с расписанием...
    # send_scholarship_info, send_dormitory_info, send_profkom_info и т.д.

    async def handle_group_command(self, bot, chat_id, group_name):
        """Обработка команды /group"""
        from database import user_db

        # Проверяем роль пользователя из БД
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Эта команда доступна только для студентов.\n"
                     "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        if not group_name:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Укажите название группы\nПример: `/group ИВТИИбд-32`"
            )
            return

        # Ищем группу по названию
        group_number = self.parser.find_group_number(group_name)

        if group_number:
            found_group_name = self.parser.get_group_name(group_number)
            user_db.update_user_group(chat_id, found_group_name)
            await self.generate_and_send_table(bot, chat_id, group_number)
        else:
            # Поиск похожих групп
            similar_groups = []
            group_name_upper = group_name.upper()

            for num, name in GROUPS_DICT.items():
                if group_name_upper in name.upper():
                    similar_groups.append((num, name))

            if similar_groups:
                groups_text = "❌ Группа не найдена, но есть похожие:\n\n"
                for num, name in similar_groups[:5]:
                    groups_text += f"• {name} - используйте `/group {name}`\n"
                groups_text += f"\n🔍 Или используйте `/search {group_name}` для расширенного поиска"
                await bot.send_message(chat_id=chat_id, text=groups_text)
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Группа '{group_name}' не найдена.\n\n"
                         f"📋 *Что можно сделать:*\n"
                         f"• Используйте `/groups` для просмотра всех групп\n"
                         f"• Используйте `/search {group_name}` для поиска\n"
                         f"• Проверьте правильность написания названия группы"
                )

    async def send_groups_info(self, bot, chat_id):
        """Отправляет информацию о доступных группах"""
        from database import user_db

        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Эта команда доступна только для студентов.\n"
                     "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        groups_info = (
            f"📚 *Доступные группы:*\n\n"
            f"• Всего групп: {len(GROUPS_DICT)}\n"
            f"• Формат: Факультет-Курс (например: ИВТИИбд-32)\n\n"
            f"*Команды:*\n"
            f"`/group <название>` - расписание конкретной группы\n"
            f"`/search <часть названия>` - поиск группы\n\n"
            f"*Примеры:*\n"
            f"`/group ИВТИИбд-32`\n"
            f"`/group ПИбд-31`\n"
            f"`/group Рбд-11`"
        )

        await bot.send_message(chat_id=chat_id, text=groups_info)

    async def handle_search_command(self, bot, chat_id, search_query):
        """Обработка команды поиска"""
        from database import user_db

        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Эта команда доступна только для студентов.\n"
                     "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        await bot.send_message(chat_id=chat_id, text=f"🔍 Ищу группы содержащие: '{search_query}'")

        found_groups = []
        for group_num, group_name in GROUPS_DICT.items():
            if search_query in group_name.upper():
                found_groups.append((group_num, group_name))

        if found_groups:
            groups_text = f"🎯 *Найдено групп ({len(found_groups)}):*\n\n"
            for group_num, group_name in found_groups[:15]:
                groups_text += f"• {group_name}\n"
                groups_text += f"  Используйте: `/group {group_name}`\n\n"

            if len(found_groups) > 15:
                groups_text += f"*... и еще {len(found_groups) - 15} групп*\n"
                groups_text += f"*Уточните запрос для более точного поиска*"

            await bot.send_message(chat_id=chat_id, text=groups_text)
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Группы содержащие '{search_query}' не найдены.\n\n"
                     f"💡 *Советы:*\n"
                     f"• Используйте `/groups` для просмотра всех групп\n"
                     f"• Попробуйте сокращенное название (ИВТ, ПИ, ИСТ и т.д.)\n"
                     f"• Проверьте правильность написания"
            )

    async def send_teacher_input_prompt(self, bot, chat_id):
        """Отправляет запрос на ввод фамилии преподавателя"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton
        state_service.set_user_state(chat_id, 'awaiting_teacher_input')
        builder = InlineKeyboardBuilder()
        builder.row(get_back_button())

        await bot.send_message(
            chat_id=chat_id,
            text="👨‍🏫 Введите фамилию преподавателя (без инициалов)\n\nПримеры:\n• петров\n• иванов\n• сидоров\n\n💡 Подсказка: Вводите только фамилию, система найдет преподавателя автоматически",
            attachments=[builder.as_markup()]
        )

    async def handle_student_schedule_callback(self, bot, chat_id):
        """Обработка callback для получения расписания студента"""
        from database import user_db

        user_info = user_db.get_user(chat_id)

        if user_info and user_info[2]:  # Если у пользователя уже есть сохраненная группа
            _, _, group_name = user_info
            group_number = self.parser.find_group_number(group_name)
            if group_number:
                await bot.send_message(chat_id=chat_id,
                                       text=f"📅 Загружаю расписание для вашей группы {group_name}...")
                await self.generate_and_send_table(bot, chat_id, group_number)
                return

        # Если группы нет, запрашиваем ввод
        await self.handle_enter_group_name(bot, chat_id)

    async def handle_enter_group_name(self, bot, chat_id):
        """Запрашивает ввод названия группы"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        # Устанавливаем состояние ожидания ввода группы
        state_service.set_user_state(chat_id, 'awaiting_group_input')

        builder = InlineKeyboardBuilder()
        builder.row(get_back_to_student_menu_button())

        await bot.send_message(
            chat_id=chat_id,
            text="Введите название группы \n\nПримеры:\n• ИВТИИбд-32\n• ПИбд-31\n• ИСТбд-41\n\n💡 Подсказка: Используйте /groups для просмотра всех групп или /search для поиска по названию",
            attachments=[builder.as_markup()]
        )

    async def handle_search_group(self, bot, chat_id):
        """Обработка callback для поиска группы"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        builder = InlineKeyboardBuilder()
        builder.row(get_back_to_student_menu_button())

        await bot.send_message(
            chat_id=chat_id,
            text="🔍 *Поиск группы*\n\nИспользуйте команды:\n• `/groups` - список всех групп\n• `/search <название>` - поиск по названию\n\nПример:\n`/search ИВТ` - найдет все группы с 'ИВТ' в названии",
            attachments=[builder.as_markup()]
        )

    async def handle_group_input(self, bot, chat_id, text):
        """Обработка ввода названия группы"""
        from database import user_db

        # Сбрасываем состояние сразу
        state_service.clear_user_state(chat_id)

        if not text:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Вы не ввели название группы.\n\nПопробуйте снова или используйте:\n• `/groups` - список всех групп\n• `/search` - поиск по названию"
            )
            return

        # Проверяем, что пользователь студент
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Эта функция доступна только для студентов.\nПожалуйста, сначала выберите роль студента с помощью /start"
            )
            return

        # Ищем группу по введенному названию
        await bot.send_message(chat_id=chat_id, text=f"🔍 Ищу группу: {text}")

        group_number = self.parser.find_group_number(text)

        if group_number:
            found_group_name = self.parser.get_group_name(group_number)

            # СОХРАНЯЕМ ГРУППУ ПОЛЬЗОВАТЕЛЯ В БАЗУ ДАННЫХ
            user_db.update_user_group(chat_id, found_group_name)

            # Определяем часть расписания
            part_id, part_data = self.parser.get_schedule_part_for_group(group_number)
            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ Найдена группа: {found_group_name}\n"
                     f"📁 Часть расписания: {part_id}\n"
                     f"💾 Группа сохранена в вашем профиле!"
            )
            await self.generate_and_send_table(bot, chat_id, group_number)
        else:
            # Предлагаем похожие группы
            similar_groups = []
            text_upper = text.upper()

            for num, name in GROUPS_DICT.items():
                if text_upper in name.upper():
                    similar_groups.append((num, name))

            if similar_groups:
                groups_text = "❌ Группа не найдена, но есть похожие:\n\n"
                for num, name in similar_groups[:5]:
                    groups_text += f"• {name}\n"
                groups_text += f"\n💡 *Введите точное название группы из списка выше*"
                await bot.send_message(chat_id=chat_id, text=groups_text)
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Группа '{text}' не найдена.\n\n"
                         f"📋 *Что можно сделать:*\n"
                         f"• Используйте `/groups` для просмотра всех групп\n"
                         f"• Используйте `/search {text}` для поиска\n"
                         f"• Проверьте правильность написания"
                )

    async def handle_teacher_input(self, bot, chat_id, text):
        """Обработка ввода фамилии преподавателя"""
        from database import user_db

        if not text:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Вы не ввели фамилию преподавателя.\n\nПопробуйте снова или используйте кнопку 'Назад'"
            )
            return

        # Проверяем, что пользователь преподаватель
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "teacher":
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Эта функция доступна только для преподавателей.\nПожалуйста, сначала выберите роль преподавателя"
            )
            return

        # Ищем преподавателя по фамилии
        teacher_number = self.parser.find_teacher_number(text)

        if teacher_number:
            teacher_name = self.parser.get_teacher_name(teacher_number)
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔄 Загружаю расписание..."
            )

            try:
                # Получаем и отправляем расписание преподавателя
                teacher_url = self.parser.get_teacher_url(teacher_number)
                schedule_image = self.parser.get_teacher_schedule_image(teacher_url)

                # Сохраняем и отправляем изображение
                filename = f"schedule_teacher_{teacher_number}.png"
                file_path = os.path.join(SCHEDULE_DIR, filename)

                image_bytes_io = self.parser.image_generator.image_to_bytes(schedule_image)
                with open(file_path, "wb") as f:
                    f.write(image_bytes_io.getvalue())

                with open(file_path, "rb") as file:
                    image_data = file.read()

                input_media = InputMediaBuffer(
                    buffer=image_data,
                    filename=filename
                )

                builder = InlineKeyboardBuilder()
                builder.row(get_back_button())

                await bot.send_message(
                    chat_id=chat_id,
                    text=f"📅 Расписание преподавателя {teacher_name}",
                    attachments=[input_media, builder.as_markup()]
                )

                logging.info(f"✅ Расписание преподавателя отправлено: {teacher_name}")

            except Exception as e:
                logging.error(f"❌ Ошибка при получении расписания преподавателя: {e}")
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Ошибка при загрузке расписания преподавателя {teacher_name}\n"
                         f"Попробуйте позже или обратитесь к администратору"
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"❌ Преподаватель с фамилией '{text}' не найден.\n\n"
                     f"💡 *Советы:*\n"
                     f"• Проверьте правильность написания фамилии\n"
                     f"• Вводите только фамилию без инициалов\n"
                     f"• Попробуйте другую фамилию"
            )

    async def send_profkom_staff_info(self, bot, chat_id):
        """Отправляет информацию о составе профкома с картинкой"""
        try:
            staff_text = (
                "Ты готов попасть в нашу семью? Тогда пора знакомиться!\n\n"
                "✏ Профсоюзный комитет — выборный орган Первичной профсоюзной организации обучающихся. "
                "В состав профкома входят: председатель, заместители и 9 председателей профбюро факультетов.\n\n"
                "👩🏻 Председатель профкома обучающихся - Наталья Федотова\n"
                "🔷 Заместитель председатель профкома обучающихся - Ксения Морозова\n"
                "🔹 Заместитель председатель профкома обучающихся - Алексей Лопатин\n\n"
                "ПРЕДСЕДАТЕЛИ ПРОФСОЮЗНЫХ БЮРО ФАКУЛЬТЕТОВ:\n"
                "💚ИЭФ - Дмитрий Ульянов\n"
                "💜ГФ - Анастасия Павлычева\n"
                "🩵ИАТУ - Айнур Багаутдинов\n"
                "🧡ЭФ - Дарья Кирпичева\n"
                "🤍ИФМИ - Герман Филиппов\n"
                "💛СФ - Оля Лапушкина\n"
                "💙РТФ - Камилла Алексеева\n"
                "🖤МФ - Артём Лопатин\n"
                "❤ФИСТ - Тимур Исаков\n\n"
                "Тебе предстоит долгий и насыщенный путь, который ты пройдешь со своим профоргом рука об руку, поэтому не стесняйся, пиши ему по любому интересующему тебя вопросу!"
            )

            image_path = os.path.join("assets", "1.jpg")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(get_back_to_profkom_button())
                await bot.send_message(
                    chat_id=chat_id,
                    text=staff_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="profkom_staff.jpg"
            )

            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_profkom_button())

            await bot.send_message(
                chat_id=chat_id,
                text=staff_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке состава профкома: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_profkom_button())
            await bot.send_message(
                chat_id=chat_id,
                text=staff_text,
                attachments=[builder.as_markup()]
            )

    async def send_profkom_payments_info(self, bot, chat_id):
        """Отправляет информацию о выплатах профкома с картинкой"""
        try:
            payments_text = (
                "👩‍🎓«Информированный студент – успешный студент!»\n\n"
                "Профком обучающихся УлГТУ считает своим долгом предоставлять студентам всегда самую актуальную информацию!\n\n"
                "📌Для вашего удобства мы собрали самую важную информацию о выплатах в одном посте, чтобы вы могли легко ее найти.\n\n"
                "Подробности об условиях их получения и сроках подачи документов находятся ниже.\n\n"
                "🔹Государственная академическая стипендия\n"
                "https://vk.com/wall-22117146_4704\n\n"
                "🔹Повышенная государственная академическая стипендия\n"
                "https://vk.com/wall-22117146_4713\n\n"
                "🔹Государственная социальная стипендия\n"
                "https://vk.com/wall-22117146_4715\n\n"
                "🔹 Повышенная государственная социальная стипендия\n"
                "https://vk.com/wall-22117146_4717\n\n"
                "🔹 Именные стипендии\n"
                "https://vk.com/wall-22117146_4746\n\n"
                "🔹 Стипендии Президента и Правительства РФ\n"
                "https://vk.com/wall-22117146_4303\n\n"
                "🔹 Губернаторская стипендия «Семья»\n"
                "https://vk.com/wall-22117146_4400\n\n"
                "🔹 Стипендия губернатора Ульяновской области «Призывник»\n"
                "https://vk.com/wall-22117146_4708\n\n"
                "🔹 Материальная помощь из средств Профсоюза\n"
                "https://vk.com/wall-22117146_4721\n\n"
                "🔹 Материальная помощь из средств ВУЗа\n"
                "https://vk.com/wall-22117146_4720\n\n"
            )

            image_path = os.path.join("assets", "2.jpg")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(get_back_to_profkom_button())
                await bot.send_message(
                    chat_id=chat_id,
                    text=payments_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="profkom_payments.jpg"
            )

            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_profkom_button())

            await bot.send_message(
                chat_id=chat_id,
                text=payments_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о выплатах: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_profkom_button())
            await bot.send_message(
                chat_id=chat_id,
                text=payments_text,
                attachments=[builder.as_markup()]
            )

    async def send_profkom_contacts_info(self, bot, chat_id):
        """Отправляет контактную информацию профкома"""
        contacts_text = (
            "📞 Профком обучающихся УлГТУ\n\n"
            "Информационная группа Первичной профсоюзной организации обучающихся УлГТУ.\n\n"
            "Режим работы:\n"
            "Пн-Пт: 8.30-17.30\n\n"
            "Приём обучающихся:\n"
            "Пн-Чт: 9.00-16.00\n\n"
            "Обед:\n"
            "12.00-13.00\n\n"
            "📍 Местоположение:\n"
            "Аудитория профкома обучающихся (между аудиториями 4 и 4а 3 учебного корпуса)"
        )

        builder = InlineKeyboardBuilder()
        builder.row(get_back_to_profkom_button())

        await bot.send_message(
            chat_id=chat_id,
            text=contacts_text,
            attachments=[builder.as_markup()]
        )

    async def send_scholarship_info(self, bot, chat_id):
        """Отправляет информацию о стипендиальных выплатах"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        scholarship_text = (
            "💰 *Стипендиальные выплаты*\n\n"
            "Выберите категорию для получения информации о стипендиях:"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="👨‍🎓 Студенты", payload="scholarship_students"),
            CallbackButton(text="🎓 Магистрантам", payload="scholarship_masters"),
        )
        builder.row(
            CallbackButton(text="📚 Аспирантам", payload="scholarship_phd"),
            CallbackButton(text="🏫 Стипендия колледжей", payload="scholarship_college"),
        )
        builder.row(
            CallbackButton(text="⭐ Повышенная стипендия", payload="scholarship_increased"),
        )
        builder.row(
            get_back_to_student_menu_button(),
        )

        await bot.send_message(
            chat_id=chat_id,
            text=scholarship_text,
            attachments=[builder.as_markup()]
        )

    async def send_abiturient_info(self, bot, chat_id):
        """Отправляет информацию для поступления"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        info_text = (
            "Информация для поступления:\n"
            "По следующей ссылке находится вся необходимая информация, которая понадобится вам для поступления в Ульяновский Государственный Технический Университет:\n\n"
            "https://ulstu.ru/education_programs/index.php?SECTION_ID=536\n\n"
            "📍 Контакты и адреса:\n"
            "• Приемная комиссия УлГТУ расположена по адресу: г. Ульяновск, ул. Северный Венец, 32, 2 учебный корпус\n"
            "• Телефоны: +7 (8422) 43-05-05, +7 (909) 355-70-69\n"
            "• E-mail: pk@ulstu.ru\n\n"
            "Приёмная ректора:\n"
            "• Телефон: 8 (8422) 43-06-43\n"
            "• Факс: 8 (8422) 43-02-37\n"
            "• E-mail: rector@ulstu.ru\n\n"
            "🔗 Более подробная информация находится по ссылке:\n"
            "https://ulstu.ru/abitur/common/contacts/\n\n"
            "Для справки используйте команду /help"
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="🔙 Назад", payload="back_to_abiturient_menu"))

        await bot.send_message(
            chat_id=chat_id,
            text=info_text,
            attachments=[builder.as_markup()]
        )

    async def send_abiturient_chats(self, bot, chat_id):
        """Отправляет информацию о чатах факультетов"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        chats_text = (
            "💬 Чаты факультетов для абитуриентов:\n\n"
            "Здесь будут ссылки на чаты всех факультетов УлГТУ\n"
            "Вы можете задавать вопросы о подаче документов и деканы факультетов с радостью вам ответят\n\n"
            "📚 Факультеты:\n\n"
            "1. Факультет информационных систем и технологий - https://vk.me/join/AJQ1dyfBWykr3cy9beR_oyxR\n\n"
            "2. Строительный факультет - https://vk.me/join/AJQ1d9NGXyn4jOf/78xjXyQi\n\n"
            "3. Энергетический факультет - https://vk.me/join/AJQ1d2gnZymJfeXPSsdF/NlW\n\n"
            "4. Гуманитарный факультет - https://vk.me/join/AJQ1dwj_ZilWzfZOesDdgPNk\n\n"
            "5. Инженерно-экономический факультет - https://vk.me/join/AJQ1d2UzYik924RhKc5VMeZ/\n\n"
            "6. Радиотехнический факультет - https://vk.me/join/AJQ1dyfCTSk8o5ITrqemJS7g\n\n"
            "7. Машиностроительный факультет - https://vk.me/join/AJQ1dzMjWin5iByTPltOVTit\n\n"
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="🔙 Назад", payload="back_to_abiturient_menu"))

        await bot.send_message(
            chat_id=chat_id,
            text=chats_text,
            attachments=[builder.as_markup()]
        )

    async def send_dormitory_info(self, bot, chat_id):
        """Отправляет информацию об общежитиях с картинкой"""
        try:
            dormitory_text = (
                "🏠 *ИНФОРМАЦИЯ ДЛЯ НУЖДАЮЩИХСЯ В ОБЩЕЖИТИИ*\n\n"
                "Лицам, зарегистрированным вне г.Ульяновска и нуждающимся в общежитии, таковое может быть предоставлено.\n\n"
                "В г.Ульяновске УлГТУ располагает четырьмя общежития (№1, 2, 3 и 6) общей вместимостью свыше 1300 человек. Общежития расположены на территории кампуса УЛГТУ, на северной площадке (ул.Северный Венец, 32).\n\n"
                "Проживание в общежитии – это весьма бюджетно (стоимость - от 571,77 руб. для обучающихся на бюджетных местах и от 2004,16 руб. – для внебюджетных мест) и территориально выгодно в силу близости как к учебным корпусам УлГТУ, так и к объектам спортивной инфраструктуры (порядка 500 м в обоих случаях).\n\n"
                "Как правило, в общежитиях №1, №2 и №3 размещаются учащиеся и студенты УлГТУ, являющиеся гражданами РФ, а в общежитиях №3 и №6 – студенты, являющиеся гражданами иностранных государств, а также сотрудники УлГТУ.\n\n"
                "Учащиеся и студенты, являющиеся гражданами РФ, размещаются в общежитиях №1, №2 и №3 с соблюдением факультетского принципа размещения: так, в общежитии №1 размещаются учащиеся КЭИ, а также студенты ФИСТ, РТФ и самолётостроительного факультета в общежитии №2 – студенты гуманитарного, энергетического факультетов; в общежитии № 3 - машиностроительного и строительного факультетов."
            )

            image_path = os.path.join("assets", "10.jpg")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(
                    CallbackButton(text="📋 Предоставление мест", payload="dormitory_provision"),
                    CallbackButton(text="📞 Контакты", payload="dormitory_contacts"),
                )
                builder.row(get_back_to_student_menu_button())
                await bot.send_message(
                    chat_id=chat_id,
                    text=dormitory_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="dormitory_info.jpg"
            )

            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="📋 Предоставление мест", payload="dormitory_provision"),
                CallbackButton(text="📞 Контакты", payload="dormitory_contacts"),
            )
            builder.row(get_back_to_student_menu_button())

            await bot.send_message(
                chat_id=chat_id,
                text=dormitory_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации об общежитиях: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="📋 Предоставление мест", payload="dormitory_provision"),
                CallbackButton(text="📞 Контакты", payload="dormitory_contacts"),
            )
            builder.row(get_back_to_student_menu_button())
            await bot.send_message(
                chat_id=chat_id,
                text=dormitory_text,
                attachments=[builder.as_markup()]
            )

    async def send_dormitory_provision_info(self, bot, chat_id):
        """Отправляет информацию о предоставлении мест в общежитии"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        provision_text = (
            "📋 *Предоставление мест в общежитии*\n\n"
            "1. Получить в деканате справку о поступлении на обучение в УлГТУ (далее - Справка); получить Справку.\n\n"
            "2. В зависимости от факультета обратиться со Справкой и паспортом РФ (далее - Паспорт) к заведующей общежитием №1, №2 или №3 (распределение факультетов по общежитиям – см. текст выше данного алгоритма) для получения ордера на заселение (далее - Ордер); получить Ордер.\n\n"
            "3. Медицинская справка из медпункта УлГТУ (6 корпус каб. 410);\n\n"
            "4. Обратиться с Ордером, Паспортом и медсправкой в центр обслуживания студентов (главный учебный корпус (корпус 6), этаж 3, каб.301) для заключения договора на проживание (далее - Договор) и оформления временной регистрации; получить Договор и свидетельство о временной регистрации.\n\n"
            "5. Обратиться с Договором и Паспортом в бюро пропусков УлГТУ (каб.100Б, 1-й этаж 3-го учебного корпуса) для оформления биометрического пропуска в общежитие; оформить биометрический пропуск.\n\n"
            "6. Обратиться с Договором, Медсправкой и Паспортом к заведующей общежитием для собственно заселения в общежитие; заселиться в общежитие."
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="🔙 Назад", payload="student_dormitory"))

        await bot.send_message(
            chat_id=chat_id,
            text=provision_text,
            attachments=[builder.as_markup()]
        )

    async def send_dormitory_contacts_info(self, bot, chat_id):
        """Отправляет контактную информацию об общежитиях"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        contacts_text = (
            "📞 *Контакты общежитий УлГТУ*\n\n"
            "*Директор студенческого городка:*\n"
            "Головко Марина Николаевна\n"
            "тел.: +7 (8422) 778-516, +7 (8422) 778-459.\n\n"
            "*Центр обслуживания студентов:*\n"
            "+7 (8422) 778-465.\n\n"
            "*Заведующая общежитием №1:*\n"
            "Шевцова Наталья Евгеньевна\n"
            "тел.: +7 (8422) 778-278; +7 (8422) 778-514 (вахта общежития №1).\n\n"
            "*Заведующая общежитием №2:*\n"
            "Пигалёва Надежда Павловна\n"
            "тел.: +7 (8422) 778-268; +7 (8422) 778-515 (вахта общежития №2).\n\n"
            "*Заведующая общежитием №3:*\n"
            "Зайцева Лариса Владимировна\n"
            "тел.: +7 (8422) 778-269; +7 (8422) 778-507 (вахта общежития №3)."
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="🔙 Назад", payload="student_dormitory"))

        await bot.send_message(
            chat_id=chat_id,
            text=contacts_text,
            attachments=[builder.as_markup()]
        )

    async def send_career_center_info(self, bot, chat_id):
        """Отправляет информацию о центре карьеры с картинкой"""
        try:
            career_text = (
                "💼 *Центр Карьеры, УлГТУ*\n\n"
                "Подберем ключ к твоей карьере\n"
                "Поможем пройти практику, расскажем о вакансиях, сообщим о карьерных мероприятиях.\n\n"
                "Мы на Факультетусе: https://facultetus.ru/ulstu\n\n"
                "Наша группа в вк: https://vk.com/rabotaulstu"
            )

            image_path = os.path.join("assets", "15.jpg")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(get_back_to_student_menu_button())
                await bot.send_message(
                    chat_id=chat_id,
                    text=career_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="career_center.jpg"
            )

            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_student_menu_button())

            await bot.send_message(
                chat_id=chat_id,
                text=career_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о центре карьеры: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(get_back_to_student_menu_button())
            await bot.send_message(
                chat_id=chat_id,
                text=career_text,
                attachments=[builder.as_markup()]
            )

    async def send_student_life_info(self, bot, chat_id):
        """Отправляет меню студенческой жизни"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        try:
            life_text = (
                "🎓 *Студенческая жизнь УлГТУ*\n\n"
                "Выберите направление для получения подробной информации:"
            )

            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="📰 Студенческие медиа", payload="student_media"),
            )
            builder.row(
                CallbackButton(text="🤝 Добровольческий центр", payload="student_volunteer"),
            )
            builder.row(
                CallbackButton(text="👷 Студенческие отряды", payload="student_teams"),
            )
            builder.row(get_back_to_student_menu_button())

            await bot.send_message(
                chat_id=chat_id,
                text=life_text,
                attachments=[builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке меню студенческой жизни: {e}")
            await bot.send_message(chat_id=chat_id, text="❌ Ошибка при загрузке информации")

    async def send_scholarship_students_info(self, bot, chat_id):
        """Отправляет информацию о стипендиях для студентов с картинкой"""
        try:
            scholarship_text = (
                "👨‍Стипендиальные выплаты для студентов\n\n"
                "Здесь представлена информация о всех видах стипендий, доступных для студентов УлГТУ.\n\n"
                "📊 Основные виды стипендий:\n"
                "• Государственная академическая стипендия\n"
                "• Повышенная государственная академическая стипендия\n"
                "• Государственная социальная стипендия\n"
                "• Именные стипендии\n"
                "• Стипендии Президента и Правительства РФ\n\n"
                "💡 Для получения подробной информации обращайтесь в профком или деканат вашего факультета."
            )

            image_path = os.path.join("assets", "4.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=scholarship_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="scholarship_students.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))

            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о стипендиях для студентов: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[builder.as_markup()]
            )

    async def send_scholarship_masters_info(self, bot, chat_id):
        """Отправляет информацию о стипендиях для магистрантов с картинкой"""
        try:
            scholarship_text = (
                "🎓 *Стипендиальные выплаты для магистрантов*\n\n"
                "Информация о стипендиях и выплатах, доступных для студентов магистратуры УлГТУ.\n\n"
                "📊 *Виды стипендий для магистрантов:*\n"
                "• Государственная академическая стипендия\n"
                "• Повышенная государственная академическая стипендия\n"
                "• Стипендии для аспирантов и магистрантов\n"
                "• Именные стипендии\n"
                "• Стипендии за научные достижения\n\n"
                "💡 *Для получения подробной информации обращайтесь в профком или деканат вашего факультета.*"
            )

            image_path = os.path.join("assets", "5.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=scholarship_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="scholarship_masters.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))

            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о стипендиях для магистрантов: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[builder.as_markup()]
            )

    async def send_scholarship_phd_info(self, bot, chat_id):
        """Отправляет информацию о стипендиях для аспирантов с картинкой"""
        try:
            scholarship_text = (
                "📚 *Стипендиальные выплаты для аспирантов*\n\n"
                "Информация о стипендиях и выплатах, доступных для аспирантов УлГТУ.\n\n"
                "📊 *Виды стипендий для аспирантов:*\n"
                "• Государственная стипендия аспирантам\n"
                "• Повышенная стипендия за научные достижения\n"
                "• Именные стипендии для аспирантов\n"
                "• Стипендии Президента и Правительства РФ\n"
                "• Гранты и научные стипендии\n\n"
                "💡 *Для получения подробной информации обращайтесь в отдел аспирантуры или профком.*"
            )

            image_path = os.path.join("assets", "6.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=scholarship_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="scholarship_phd.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))

            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о стипендиях для аспирантов: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[builder.as_markup()]
            )

    async def send_scholarship_college_info(self, bot, chat_id):
        """Отправляет информацию о стипендиях для колледжей с картинкой"""
        try:
            scholarship_text = (
                "🏫 *Стипендиальные выплаты для колледжей*\n\n"
                "Информация о стипендиях и выплатах, доступных для студентов колледжей при УлГТУ.\n\n"
                "📊 *Виды стипендий для колледжей:*\n"
                "• Государственная академическая стипендия\n"
                "• Социальная стипендия\n"
                "• Повышенная стипендия за успехи в учебе\n"
                "• Стипендии за активную деятельность\n"
                "• Именные стипендии и гранты\n\n"
                "💡 *Для получения подробной информации обращайтесь в администрацию колледжа или профком.*"
            )

            image_path = os.path.join("assets", "7.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=scholarship_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="scholarship_college.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))

            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о стипендиях для колледжей: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[builder.as_markup()]
            )

    async def send_scholarship_increased_info(self, bot, chat_id):
        """Отправляет информацию о повышенной стипендии с картинкой"""
        try:
            scholarship_text = (
                "⭐ *Повышенная стипендия*\n\n"
                "Информация о повышенных стипендиях для студентов, магистрантов и аспирантов УлГТУ.\n\n"
                "📊 *Условия получения повышенной стипендии:*\n"
                "• Отличная успеваемость\n"
                "• Научные достижения и публикации\n"
                "• Участие в олимпиадах и конкурсах\n"
                "• Активная общественная деятельность\n"
                "• Спортивные достижения\n\n"
                "💡 *Для получения подробной информации о критериях и подаче заявления обращайтесь в профком или деканат.*"
            )

            image_path = os.path.join("assets", "8.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=scholarship_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="scholarship_increased.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))

            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о повышенной стипендии: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_scholarship"))
            await bot.send_message(
                chat_id=chat_id,
                text=scholarship_text,
                attachments=[builder.as_markup()]
            )

    async def send_events_info(self, bot, chat_id):
        """Отправляет информацию о мероприятиях"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        events_text = (
            "Все анонсы мероприятий можно узнать по следующей ссылке, в официальном канале УлГТУ в MAX - https://max.ru/ulstu73 \n\n "
            "Группы в ВК каждого нашего факультета:\n\n "
            "1. Факультет информационных систем и технологий - https://vk.com/fist_ulstu\n\n "
            "2. Строительный факультет - https://vk.com/sfulstu\n\n "
            "3. Энергетический факультет - https://vk.com/energoulstu\n\n "
            "4. Гуманитарный факультет - https://vk.com/gf_ulgtu\n\n "
            "5. Инженерно-экономический факультет - https://vk.com/ief_ulstu\n\n "
            "6. Радиотехнический факультет - https://vk.com/rtfpage\n\n "
            "7. Машиностроительный факультет - https://vk.com/ulstu_mf\n\n "
        )

        builder = InlineKeyboardBuilder()
        builder.row(get_back_to_student_menu_button())

        await bot.send_message(
            chat_id=chat_id,
            text=events_text,
            attachments=[builder.as_markup()]
        )

    async def send_certificate_info(self, bot, chat_id):
        """Отправляет информацию о заказе справок"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        certificate_text = (
            "Для того, чтобы заказать справку об обучении, выполните следующие действия:\n\n"
            "1. Напишите на почту: L.matveichuk@ulstu.ru c темой письма «Заказать справку»\n"
            "2. В тексте письма укажите ФИО, группу и количество справок, а также цифру 1-3, в зависимости от того, для чего вам нужна эта справка.\n\n"
            "1 - Пенсионный фонд\n"
            "2 - Профком\n"
            "3 - Родителям на работу\n\n"
            "Пример письма:\n\n"
            "Иванов Иван Иванович - группа ПИбд-11\n"
            "3 - Родителям на работу\n"
        )

        builder = InlineKeyboardBuilder()
        builder.row(get_back_to_student_menu_button())

        await bot.send_message(
            chat_id=chat_id,
            text=certificate_text,
            attachments=[builder.as_markup()]
        )

    async def send_profkom_info(self, bot, chat_id):
        """Отправляет информацию о профкоме"""
        from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
        from maxapi.types import CallbackButton

        profkom_text = (
            "🙌Мы — Первичная профсоюзная организация обучающихся УлГТУ.\n\n"
            "Мы знаем, чего хотят студенты, поэтому каждый день:\n\n"
            "– представляем интересы студенчества перед администрацией университета\n"
            "– отвечаем на все вопросы про стипендии и общежития\n"
            "– помогаем экономить деньги, предоставляя скидки и бонусы\n"
            "– развиваем навыки, которые ты не прокачиваешь на парах\n"
            "– организуем твоё свободное время\n"
            "– и просто решаем студенческие проблемы!\n\n"
            "И мы хотим, чтобы ты был частью нашей организации 💙\n\n"
            "📃Вступить в Профсоюз можно в профкоме обучающихся УлГТУ.\n\n"
            "Будем ждать тебя по будням в аудитории профкома обучающихся (между аудиториями 4 и 4а 3 учебного корпуса с 09:00 до 16:00 (обед с 12:00 до 13:00).\n\n"
            "Или ты можешь дождаться, когда председатель профбюро твоего факультета проведёт с твоей группой встречу, где расскажет о нас."
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="👥 Состав", payload="profkom_staff"),
            CallbackButton(text="💰 Выплаты", payload="profkom_payments"),
        )
        builder.row(
            CallbackButton(text="📞 Контакты", payload="profkom_contacts"),
        )
        builder.row(get_back_to_student_menu_button())

        await bot.send_message(
            chat_id=chat_id,
            text=profkom_text,
            attachments=[builder.as_markup()]
        )

    async def send_student_media_info(self, bot, chat_id):
        """Отправляет информацию о студенческих медиа с картинкой"""
        try:
            media_text = (
                "📰 *Студенческие медиа УлГТУ*\n\n"
                "Студенческие медиа УлГТУ – это площадка для самореализации тех, кому интересно быть в центре событий, кто любит Политех и хочет рассказать о нем другим!\n\n"
                "Студенческие медиа УлГТУ освещают события студенческой жизни вуза: научные, образовательные, культурные, спортивные, развлекательные и другие. Свой профессиональный уровень участники поднимают в рамках медиашкол УлГТУ, выездных мастер-классов и самообучения. Более 50% всего контента об УлГТУ - продукт студенческих медиа.\n\n"
                "Команда студенческих медиа регулярно участвуют в конкурсах и фестивалях, представляют УлГТУ и Ульяновскую область на Российской студенческой весне в номинации «Журналистика».\n\n"
                "Любой студент может стать участником студенческих медиацентров УлГТУ, где есть возможность заниматься фото- и видеосъемкой, монтажом роликов, моушн-дизайном, создавать собственные студенческие медиапроекты, становиться ведущими и сценаристами, создавать контент для социальных сетей УлГТУ и писать интересные статьи для разных площадок.\n\n"
                "В УлГТУ действуют 2 студенческих медиацентра:\n\n"
                "• студенческий медиацентр при Управлении по информационной политики и связям с общественностью УлГТУ - http://vk.com/mediaulstu\n\n"
                "• студенческий медиацентр «ОСОВЕТЬ» при Объединенном совете обучающихся УлГТУ - http://vk.com/osovet_media\n\n"
                "В своей дружной команде студенческие медиацентры рады видеть: фотографов, сценаристов и ведущих, операторов, журналистов, пиарщиков, SMM-щиков, дизайнеров."
            )

            image_path = os.path.join("assets", "12.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=media_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="student_media.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))

            await bot.send_message(
                chat_id=chat_id,
                text=media_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о студенческих медиа: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))
            await bot.send_message(
                chat_id=chat_id,
                text=media_text,
                attachments=[builder.as_markup()]
            )

    async def send_student_volunteer_info(self, bot, chat_id):
        """Отправляет информацию о добровольческом центре с картинкой"""
        try:
            volunteer_text = (
                "🤝 *Добровольческий центр УлГТУ*\n\n"
                "Добровольческий Центр является объединением обучающихся, осуществляющим деятельность по организации и развитию добровольческого движения в университете.\n\n"
                "Все добровольцы – герои нашего времени, которые всегда находят время и возможность помогать тем, кто в этом нуждается. Студенты работают как на вузовских, так и на региональных мероприятиях, участвуют в конференциях и форумах, в экологических, благотворительных, донорских акциях.\n\n"
                "Сейчас в Центре более 50 волонтеров, которые активно принимают участие в жизни нашего вуза и города. Они занимаются организацией многих масштабных мероприятий, донорством, облагораживанием территориы, пропагандой здорового образа жизни, экологическим просвещением, содействием в помощи пожилым людям, осуществлением посещений в приют для животных.\n\n"
                "Волонтеры УлГТУ являются участниками общероссийской акции взаимопомощи #МЫВМЕСТЕ. Активисты добровольческого центра оказывают адресную помощь нуждающимся жителям города. Волонтёры могут помочь в покупке продуктов и лекарств, решении бытовых проблем.\n\n"
                "Если ты хочешь стать частью Центра: помогать нуждающимся, организовывать благотворительные акции и мероприятия, а также участвовать в качестве волонтёра в масштабных проектах, пиши руководителю и присоединяйся к команде!"
            )

            image_path = os.path.join("assets", "13.png")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=volunteer_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="student_volunteer.png"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))

            await bot.send_message(
                chat_id=chat_id,
                text=volunteer_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о добровольческом центре: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))
            await bot.send_message(
                chat_id=chat_id,
                text=volunteer_text,
                attachments=[builder.as_markup()]
            )

    async def send_student_teams_info(self, bot, chat_id):
        """Отправляет информацию о студенческих отрядах с картинкой"""
        try:
            teams_text = (
                "👷 *Студенческие отряды УлГТУ*\n\n"
                "Штаб студенческих отрядов УлГТУ действует совместно с общественной организацией «Российские Студенческие Отряды». Главная цель - трудоустройство студентов в летнее и внеучебное время.\n\n"
                "Сейчас на базе университета работает 6 отрядов:\n\n"
                "• *Строительные отряды «Патриот», «Фобос» и «Селена».* Направление деятельности – участие во всероссийских стройках.\n\n"
                "• *Сервисные отряды «Лампа» и «Калейдоскоп».* Направление деятельности - работа на море (Семейный Отель 'Alean Family Dovile', г. Анапа) по направлениям клининг, бармен, официант, повар, спасатель, аниматор.\n\n"
                "• *Отряд снежного десанта «Эверест».* Направление деятельности - волонтерская помощь ветеранам ВОВ и СВО, проведение развлекательных программ для детей сел и деревень, Профориентационная работа со школьникам\n\n"
                "Группа Штаба студенческих отрядов УлГТУ - https://vk.com/rso_ulstu"
            )

            image_path = os.path.join("assets", "14.jpg")

            if not os.path.exists(image_path):
                logging.warning(f"❌ Файл {image_path} не найден")
                builder = InlineKeyboardBuilder()
                builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))
                await bot.send_message(
                    chat_id=chat_id,
                    text=teams_text,
                    attachments=[builder.as_markup()]
                )
                return

            with open(image_path, "rb") as file:
                image_data = file.read()

            input_media = InputMediaBuffer(
                buffer=image_data,
                filename="student_teams.jpg"
            )

            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))

            await bot.send_message(
                chat_id=chat_id,
                text=teams_text,
                attachments=[input_media, builder.as_markup()]
            )

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке информации о студенческих отрядах: {e}")
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🔙 Назад", payload="student_life"))
            await bot.send_message(
                chat_id=chat_id,
                text=teams_text,
                attachments=[builder.as_markup()]
            )
