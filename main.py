import asyncio
import logging
import os
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated, InputMediaBuffer, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton
from UlstuParser import UlstuParser
from groups_dict import GROUPS_DICT
from config import *
from database import user_db

logging.basicConfig(level=logging.INFO)

SCHEDULE_DIR = "schedule"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Создаем парсер
parser = UlstuParser()

# Хранилище для временных состояний
awaiting_group_input = {}

# Создаем папку для расписаний если её нет
if not os.path.exists(SCHEDULE_DIR):
    os.makedirs(SCHEDULE_DIR)


async def send_table_image(chat_id):
    """Отправляет существующий PNG файл с расписанием в чат"""
    logging.info("🔍 Начало send_table_image")
    try:
        # Проверяем файл в папке schedule
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

        logging.info("✅ Файл прочитан в память")

        input_media = InputMediaBuffer(
            buffer=image_data,
            filename="schedule.png"
        )

        logging.info("✅ InputMediaBuffer создан")

        # Отправляем сообщение
        await bot.send_message(
            chat_id=chat_id,
            text="📅 Ваше расписание",
            attachments=[input_media]
        )

        logging.info("✅ Изображение отправлено в чат")

    except Exception as e:
        logging.error(f"❌ Ошибка в send_table_image: {e}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при отправке расписания")


async def generate_and_send_table(chat_id, group_number=None):
    """Генерирует расписание и отправляет его в чат"""
    try:
        if group_number:
            group_name = parser.get_group_name(group_number)
            await bot.send_message(chat_id=chat_id, text=f"🔄 Генерирую расписание для группы {group_name}...")

            # Получаем информацию о части расписания
            part_id, part_data = parser.get_schedule_part_for_group(group_number)
            group_url = parser.get_group_url(group_number)

            # Проверяем доступность URL
            await bot.send_message(chat_id=chat_id, text=f"📁 Часть расписания: {part_id}")
            await bot.send_message(chat_id=chat_id, text=f"🔗 Проверяю доступность расписания...")

            schedule_image = parser.get_schedule_image_by_number(group_number)
            filename = f"schedule_group_{group_number}.png"
        else:
            await bot.send_message(chat_id=chat_id, text="🔄 Генерирую расписание...")
            # Используем группу ИВТИИбд-31 (номер 175) как рабочую по умолчанию
            schedule_image = parser.get_schedule_image_by_number(175)
            filename = "schedule.png"

        # Полный путь к файлу в папке schedule
        file_path = os.path.join(SCHEDULE_DIR, filename)

        # Конвертируем в bytes и сохраняем в папке schedule
        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open(file_path, "wb") as f:
            f.write(image_bytes_io.getvalue())

        # Отправляем изображение
        with open(file_path, "rb") as file:
            image_data = file.read()

        input_media = InputMediaBuffer(
            buffer=image_data,
            filename=filename
        )

        group_display_name = parser.get_group_name(group_number) if group_number else "ИВТИИбд-31"

        # Создаем клавиатуру с кнопкой "Назад"
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="🔙 Назад", payload="back_to_student_menu"),
        )

        await bot.send_message(
            chat_id=chat_id,
            text=f"📅 Расписание группы {group_display_name}",
            attachments=[input_media, builder.as_markup()]
        )

        logging.info(f"✅ Расписание сгенерировано и сохранено в {file_path}")

    except Exception as e:
        logging.error(f"❌ Ошибка при генерации расписания: {e}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при генерации расписания")


async def send_welcome_message(chat_id):
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


async def process_role_selection(chat_id, role):
    """Обрабатывает выбор роли пользователем и сохраняет в БД"""
    try:
        # Получаем текущую информацию о пользователе
        current_user_info = user_db.get_user(chat_id)

        if current_user_info:
            current_role = current_user_info[1]
            current_group = current_user_info[2]

            # Если пользователь меняет роль со студента на другую, сбрасываем группу
            if current_role == "student" and role != "student":
                user_db.add_or_update_user(chat_id, role, None)  # Сбрасываем группу
                logging.info(f"🔄 Пользователь {chat_id} сменил роль с '{current_role}' на '{role}', группа сброшена")
            else:
                user_db.add_or_update_user(chat_id, role, current_group)  # Сохраняем текущую группу
                logging.info(f"🔄 Пользователь {chat_id} сменил роль с '{current_role}' на '{role}'")
        else:
            # Новый пользователь
            user_db.add_or_update_user(chat_id, role)
            logging.info(f"👤 Новый пользователь {chat_id} с ролью '{role}'")

        # Удаляем из временного хранилища
        if chat_id in awaiting_group_input:
            del awaiting_group_input[chat_id]

        # Отправляем соответствующее меню
        if role == "student":
            await send_student_menu(chat_id)
        elif role == "abiturient":
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="📚 Информация для поступления", payload="abiturient_info"),
            )
            builder.row(
                CallbackButton(text="💬 Чаты факультетов", payload="abiturient_chats"),
            )
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_main"),
            )
            await bot.send_message(
                chat_id=chat_id,
                text="Вы выбрали роль: Абитуриент\n\nВыберите нужный раздел:",
                attachments=[builder.as_markup()]
            )
        elif role == "teacher":
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_main"),
            )
            await bot.send_message(
                chat_id=chat_id,
                text="Вы выбрали роль: Преподаватель\n\nЗдесь вы можете получить информацию о:\n\n• Расписании занятий\n• Учебном процессе\n• Методических материалах\n\nДля справки используйте команду /help",
                attachments=[builder.as_markup()]
            )

        # Показываем сообщение об успешной смене роли
        if current_user_info and current_user_info[1] != role:
            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ Роль успешно изменена с '{current_user_info[1]}' на '{role}'"
            )

    except Exception as e:
        logging.error(f"❌ Ошибка при обработке выбора роли: {e}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при выборе роли")


@dp.message_callback()
async def handle_callback(event: MessageCallback):
    """Обработка нажатий на callback-кнопки"""
    try:
        chat_id = event.message.recipient.chat_id
        payload = event.callback.payload

        logging.info(f"🔍 Callback получен: chat_id={chat_id}, payload={payload}")

        if payload and payload.startswith("role_"):
            role = payload.split("_")[1]
            await process_role_selection(chat_id, role)
        elif payload == "student_menu":
            await send_student_menu(chat_id)
        elif payload == "student_schedule":
            # Получаем информацию о пользователе из БД
            user_info = user_db.get_user(chat_id)

            if user_info and user_info[2]:  # Если у пользователя уже есть сохраненная группа
                _, _, group_name = user_info
                group_number = parser.find_group_number(group_name)
                if group_number:
                    await bot.send_message(chat_id=chat_id,
                                           text=f"📅 Загружаю расписание для вашей группы {group_name}...")
                    await generate_and_send_table(chat_id, group_number)
                    return

            # Если группы нет, запрашиваем ввод
            awaiting_group_input[chat_id] = True
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_student_menu"),
            )
            await bot.send_message(
                chat_id=chat_id,
                text="Введите название группы \n\nПримеры:\n• ИВТИИбд-32\n• ПИбд-31\n• ИСТбд-41\n\n💡 Подсказка: Используйте /groups для просмотра всех групп или /search для поиска по названию",
                attachments=[builder.as_markup()]
            )
        elif payload == "profkom_staff":
            await send_profkom_staff_info(chat_id)
        elif payload == "profkom_payments":
            await send_profkom_payments_info(chat_id)
        elif payload == "profkom_contacts":
            await send_profkom_contacts_info(chat_id)
        elif payload == "enter_group_name":
            awaiting_group_input[chat_id] = True
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_group_selection"),
            )
            await bot.send_message(
                chat_id=chat_id,
                text="Введите название группы \n\nПримеры:\n• ИВТИИбд-32\n• ПИбд-31\n• ИСТбд-41\n\n💡 Подсказка: Используйте /groups для просмотра всех групп или /search для поиска по названию",
                attachments=[builder.as_markup()]
            )
        elif payload == "search_group":
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_group_selection"),
            )
            await bot.send_message(
                chat_id=chat_id,
                text="🔍 *Поиск группы*\n\nИспользуйте команды:\n• `/groups` - список всех групп\n• `/search <название>` - поиск по названию\n\nПример:\n`/search ИВТ` - найдет все группы с 'ИВТ' в названии",
                attachments=[builder.as_markup()]
            )
        elif payload == "abiturient_info":
            await send_abiturient_info(chat_id)
        elif payload == "abiturient_chats":
            await send_abiturient_chats(chat_id)
        elif payload == "back_to_abiturient_menu":
            await process_role_selection(chat_id, "abiturient")
        elif payload == "student_events":
            await send_events_info(chat_id)
        elif payload == "student_certificate":
            await send_certificate_info(chat_id)
        elif payload == "student_profkom":
            await send_profkom_info(chat_id)
        elif payload == "back_to_profkom":
            await send_profkom_info(chat_id)
        elif payload == "back_to_main":
            if chat_id in awaiting_group_input:
                del awaiting_group_input[chat_id]
            await send_welcome_message(chat_id)
        elif payload == "back_to_student_menu":
            if chat_id in awaiting_group_input:
                del awaiting_group_input[chat_id]
            await send_student_menu(chat_id)
        else:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Неизвестный callback"
            )

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике callback: {e}")
        try:
            await bot.send_message(
                chat_id=event.message.recipient.chat_id,
                text="❌ Ошибка при обработке выбора"
            )
        except:
            pass


async def send_abiturient_info(chat_id):
    """Отправляет информацию для поступления"""
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
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_abiturient_menu"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=info_text,
        attachments=[builder.as_markup()]
    )


async def send_abiturient_chats(chat_id):
    """Отправляет информацию о чатах факультетов"""
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
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_abiturient_menu"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=chats_text,
        attachments=[builder.as_markup()]
    )


async def send_student_menu(chat_id):
    """Отправляет меню для студентов с четырьмя кнопками"""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="📅 Получить расписание", payload="student_schedule"),
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


async def send_events_info(chat_id):
    """Отправляет информацию о мероприятиях"""
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
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_student_menu"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=events_text,
        attachments=[builder.as_markup()]
    )


async def send_profkom_info(chat_id):
    """Отправляет информацию о профкоме"""
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
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_student_menu"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=profkom_text,
        attachments=[builder.as_markup()]
    )


async def send_certificate_info(chat_id):
    """Отправляет информацию о заказе справок"""
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
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_student_menu"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=certificate_text,
        attachments=[builder.as_markup()]
    )


async def send_profkom_staff_info(chat_id):
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
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
            )
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
        builder.row(
            CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
        )

        await bot.send_message(
            chat_id=chat_id,
            text=staff_text,
            attachments=[input_media, builder.as_markup()]
        )

    except Exception as e:
        logging.error(f"❌ Ошибка при отправке состава профкома: {e}")
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
        )
        await bot.send_message(
            chat_id=chat_id,
            text=staff_text,
            attachments=[builder.as_markup()]
        )


async def send_profkom_contacts_info(chat_id):
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
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
    )

    await bot.send_message(
        chat_id=chat_id,
        text=contacts_text,
        attachments=[builder.as_markup()]
    )


async def send_profkom_payments_info(chat_id):
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
            builder.row(
                CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
            )
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
        builder.row(
            CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
        )

        await bot.send_message(
            chat_id=chat_id,
            text=payments_text,
            attachments=[input_media, builder.as_markup()]
        )

    except Exception as e:
        logging.error(f"❌ Ошибка при отправке информации о выплатах: {e}")
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="🔙 Назад", payload="back_to_profkom"),
        )
        await bot.send_message(
            chat_id=chat_id,
            text=payments_text,
            attachments=[builder.as_markup()]
        )


# Обработчики команд ролей
@dp.message_created(Command('student'))
async def student_command(event: MessageCreated):
    """Обработчик команды /student - активация роли студента"""
    try:
        chat_id = event.message.recipient.chat_id
        user_db.add_or_update_user(chat_id, "student")

        if chat_id in awaiting_group_input:
            del awaiting_group_input[chat_id]

        await send_student_menu(chat_id)

        info_text = (
            "👨‍🎓 *Роль студента активирована!*\n\n"
            "*📚 Как получить расписание:*\n"
            "1. Нажмите кнопку '📅 Расписание'\n"
            "2. Введите название группы\n"
            "3. Получите расписание!\n\n"
            "*💡 Примеры названий групп:*\n"
            "• ИВТИИбд-32\n"
            "• ПИбд-31\n"
            "• ИСТбд-41\n\n"
            "Используйте кнопки выше для быстрого доступа к функциям!"
        )
        await event.message.answer(info_text)

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /student: {e}")
        await event.message.answer("❌ Ошибка при выборе роли")


@dp.message_created(Command('abiturient'))
async def abiturient_command(event: MessageCreated):
    """Обработчик команды /abiturient - активация роли абитуриента"""
    try:
        chat_id = event.message.recipient.chat_id
        await process_role_selection(chat_id, "abiturient")
    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /abiturient: {e}")
        await event.message.answer("❌ Ошибка при выборе роли")


@dp.message_created(Command('teacher'))
async def teacher_command(event: MessageCreated):
    """Обработчик команды /teacher - активация роли преподавателя"""
    try:
        chat_id = event.message.recipient.chat_id
        await process_role_selection(chat_id, "teacher")
    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /teacher: {e}")
        await event.message.answer("❌ Ошибка при выборе роли")


@dp.bot_started()
async def bot_started(event: BotStarted):
    try:
        await send_welcome_message(event.chat_id)
    except Exception as e:
        await bot.send_message(chat_id=event.chat_id, text="❌ Ошибка при запуске")


@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    try:
        chat_id = event.message.recipient.chat_id

        if chat_id in awaiting_group_input:
            del awaiting_group_input[chat_id]

        await send_welcome_message(chat_id)
    except Exception as e:
        await event.message.answer("❌ Ошибка при запуске")


@dp.message_created(Command('table'))
async def send_table_command(event: MessageCreated):
    """Обработчик команды /table - генерирует и отправляет расписание"""
    logging.info("🔄 Обработчик /table вызван")
    try:
        chat_id = event.message.recipient.chat_id

        # Проверяем роль пользователя из БД
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await event.message.answer(
                "❌ Эта команда доступна только для студентов.\n"
                "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        logging.info(f"🔄 Генерирую расписание для chat_id: {chat_id}")
        await generate_and_send_table(chat_id)
        logging.info("✅ generate_and_send_table завершен")

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /table: {e}")
        import traceback
        logging.error(f"❌ Трассировка: {traceback.format_exc()}")
        await event.message.answer("❌ Ошибка при генерации расписания")


@dp.message_created(Command('group'))
async def group_command(event: MessageCreated):
    """Обработчик команды /group <название> - расписание конкретной группы"""
    try:
        chat_id = event.message.recipient.chat_id

        # Проверяем роль пользователя из БД
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await event.message.answer(
                "❌ Эта команда доступна только для студентов.\n"
                "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        # Получаем текст команды из event
        command_text = event.message.body.text.strip()
        parts = command_text.split()

        if len(parts) < 2:
            await event.message.answer(
                "❌ Укажите название группы\n"
                f"Пример: `/group ИВТИИбд-32`\n\n"
                f"📋 *Доступные группы:*\n"
                f"• Используйте `/groups` для просмотра всех групп\n"
                f"• Используйте `/search <часть названия>` для поиска"
            )
            return

        group_name = ' '.join(parts[1:]).strip()

        if not group_name:
            await event.message.answer(
                "❌ Укажите название группы\n"
                f"Пример: `/group ИВТИИбд-32`"
            )
            return

        await event.message.answer(f"🔍 Ищу группу: {group_name}")

        # Ищем группу по названию
        group_number = parser.find_group_number(group_name)

        if group_number:
            found_group_name = parser.get_group_name(group_number)

            # СОХРАНЯЕМ ГРУППУ В БАЗУ ДАННЫХ
            user_db.update_user_group(chat_id, found_group_name)

            await event.message.answer(f"✅ Найдена группа: {found_group_name}\n💾 Группа сохранена в вашем профиле!")
            await generate_and_send_table(chat_id, group_number)
        else:
            # Предлагаем похожие группы
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
                await event.message.answer(groups_text)
            else:
                await event.message.answer(
                    f"❌ Группа '{group_name}' не найдена.\n\n"
                    f"📋 *Что можно сделать:*\n"
                    f"• Используйте `/groups` для просмотра всех групп\n"
                    f"• Используйте `/search {group_name}` для поиска по части названия\n"
                    f"• Проверьте правильность написания названия группы"
                )

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /group: {e}")
        await event.message.answer("❌ Ошибка при поиске группы")


@dp.message_created(Command('groups'))
async def groups_command(event: MessageCreated):
    """Обработчик команды /groups - информация о доступных группах"""
    try:
        chat_id = event.message.recipient.chat_id

        # Проверяем роль пользователя из БД
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await event.message.answer(
                "❌ Эта команда доступна только для студентов.\n"
                "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        groups_info = (
            f"📚 *Доступные группы:*\n\n"
            f"• Всего групп: {len(GROUPS_DICT)}\n"
            f"• Части расписания: {len(SCHEDULE_PARTS)}\n"
            f"• Формат: Факультет-Курс (например: ИВТИИбд-32)\n\n"
            f"*Команды:*\n"
            f"`/group <название>` - расписание конкретной группы\n"
            f"`/table` - расписание группы по умолчанию\n"
            f"`/search <часть названия>` - поиск группы\n\n"
            f"*Примеры:*\n"
            f"`/group ИВТИИбд-32`\n"
            f"`/group ПИбд-31`\n"
            f"`/group Рбд-11`\n\n"
            f"📋 *Популярные группы:*\n"
            f"• ИВТИИбд-31, ИВТИИбд-32\n"
            f"• ПИбд-31, ПИбд-32, ПИбд-33\n"
            f"• ИСТбд-31, ИСТбд-32\n"
            f"• Рбд-11, РТбд-21\n"
            f"• Эбд-31, ЭАбд-41"
        )

        await event.message.answer(groups_info)

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /groups: {e}")
        await event.message.answer("❌ Ошибка при получении информации о группах")


@dp.message_created(Command('search'))
async def search_command(event: MessageCreated):
    """Обработчик команды /search - поиск группы по названию"""
    try:
        chat_id = event.message.recipient.chat_id

        # Проверяем роль пользователя из БД
        user_info = user_db.get_user(chat_id)
        if not user_info or user_info[1] != "student":
            await event.message.answer(
                "❌ Эта команда доступна только для студентов.\n"
                "Пожалуйста, сначала выберите роль студента с помощью команды /start"
            )
            return

        # Получаем текст команды из event
        command_text = event.message.body.text.strip()
        parts = command_text.split()

        if len(parts) < 2:
            await event.message.answer(
                "❌ Укажите часть названия группы для поиска\n"
                "Пример: `/search ИВТ` или `/search ПИ`"
            )
            return

        search_query = ' '.join(parts[1:]).upper()
        await event.message.answer(f"🔍 Ищу группы содержащие: '{search_query}'")

        # Ищем группы по названию в словаре
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

            await event.message.answer(groups_text)
        else:
            await event.message.answer(
                f"❌ Группы содержащие '{search_query}' не найдены.\n\n"
                f"💡 *Советы:*\n"
                f"• Используйте `/groups` для просмотра всех групп\n"
                f"• Попробуйте сокращенное название (ИВТ, ПИ, ИСТ и т.д.)\n"
                f"• Проверьте правильность написания"
            )

    except Exception as e:
        logging.error(f"❌ Ошибка в обработчике /search: {e}")
        await event.message.answer("❌ Ошибка при поиске групп")


@dp.message_created(Command('debug'))
async def debug_info(event: MessageCreated):
    """Показывает отладочную информацию"""
    try:
        group_name, week_number, schedules = parser.parse_group_schedule(parser.get_group_url(61))

        debug_text = f"""
🔍 *Отладочная информация:*

📊 Группа: {group_name}
📅 Неделя: {week_number}
📚 Занятий: {len(schedules)}

📋 *Расписание:*
"""

        if schedules:
            for lesson in schedules[:10]:
                debug_text += f"""
{lesson['day']} {lesson['pair']} пара: {lesson['subject']}
   Тип: {lesson['type']}
   Преп: {lesson['teacher']}
   Ауд: {lesson['classroom']}
"""
        else:
            debug_text += "\n❌ Занятия не найдены"

        await event.message.answer(debug_text)

    except Exception as e:
        await event.message.answer(f"❌ Ошибка отладки: {e}")


@dp.message_created(Command('profile'))
async def profile_command(event: MessageCreated):
    """Показывает профиль пользователя"""
    try:
        chat_id = event.message.recipient.chat_id

        # Получаем информацию о пользователе из БД
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

        await event.message.answer(profile_text)

    except Exception as e:
        logging.error(f"❌ Ошибка в команде /profile: {e}")
        await event.message.answer("❌ Ошибка при получении профиля")


@dp.message_created(Command('help'))
async def help_command(event: MessageCreated):
    chat_id = event.message.recipient.chat_id

    # Получаем информацию о пользователе из БД
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
        help_text += "/table - Расписание группы по умолчанию\n"
        help_text += "/group <название> - Расписание конкретной группы\n"
        help_text += "/groups - Список доступных групп\n"
        help_text += "/search <часть названия> - Поиск группы по названию\n"
        help_text += "/debug - Отладочная информация\n\n"
        help_text += "*💡 Примеры использования:*\n"
        help_text += "`/group ИВТИИбд-32` - расписание группы ИВТИИбд-32\n"
        help_text += "`/search ИВТ` - поиск всех групп с 'ИВТ' в названии\n"
        help_text += "`/groups` - просмотр всех доступных групп"

        if group_name:
            help_text += f"\n\n*🎯 Ваша сохраненная группа:* {group_name}"
            help_text += f"\nИспользуйте кнопку '📅 Расписание' для быстрого доступа"
    elif status == "abiturient":
        help_text += "*🎓 Команды для абитуриентов:*\n"
        help_text += "Информация о поступлении...\n"
    elif status == "teacher":
        help_text += "*👨‍🏫 Команды для преподавателей:*\n"
        help_text += "Информация для преподавателей...\n"
    else:
        help_text += "Выберите роль с помощью /start чтобы получить доступ к командам"

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="🔙 Назад", payload="back_to_main"),
    )

    await event.message.answer(
        text=help_text,
        attachments=[builder.as_markup()]
    )


@dp.message_created()
async def handle_message(event: MessageCreated):
    try:
        chat_id = event.message.recipient.chat_id
        text = event.message.body.text.strip()

        # Проверяем, ожидаем ли мы ввод названия группы от этого пользователя
        if chat_id in awaiting_group_input and awaiting_group_input[chat_id]:
            # Сбрасываем состояние ожидания
            del awaiting_group_input[chat_id]

            if not text:
                await event.message.answer(
                    "❌ Вы не ввели название группы.\n\nПопробуйте снова или используйте:\n• `/groups` - список всех групп\n• `/search` - поиск по названию"
                )
                return

            # Проверяем, что пользователь студент
            user_info = user_db.get_user(chat_id)
            if not user_info or user_info[1] != "student":
                await event.message.answer(
                    "❌ Эта функция доступна только для студентов.\nПожалуйста, сначала выберите роль студента с помощью /start"
                )
                return

            # Ищем группу по введенному названию
            await event.message.answer(f"🔍 Ищу группу: {text}")

            group_number = parser.find_group_number(text)

            if group_number:
                found_group_name = parser.get_group_name(group_number)

                # СОХРАНЯЕМ ГРУППУ ПОЛЬЗОВАТЕЛЯ В БАЗУ ДАННЫХ
                user_db.update_user_group(chat_id, found_group_name)

                # Определяем часть расписания
                part_id, part_data = parser.get_schedule_part_for_group(group_number)
                await event.message.answer(
                    f"✅ Найдена группа: {found_group_name}\n"
                    f"📁 Часть расписания: {part_id}\n"
                    f"💾 Группа сохранена в вашем профиле!"
                )
                await generate_and_send_table(chat_id, group_number)
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
                    await event.message.answer(groups_text)
                else:
                    await event.message.answer(
                        f"❌ Группа '{text}' не найдена.\n\n"
                        f"📋 *Что можно сделать:*\n"
                        f"• Используйте `/groups` для просмотра всех групп\n"
                        f"• Используйте `/search {text}` для поиска\n"
                        f"• Проверьте правильность написания"
                    )

        elif text and not text.startswith('/'):
            # Обычное сообщение без команды
            await event.message.answer(
                "🤔 Используйте /start для выбора роли или /help для справки\n\n"
                "*📚 Для студентов:*\n"
                "• Нажмите кнопку '📅 Расписание' для получения расписания\n"
                "• `/groups` - список всех групп\n"
                "• `/search` - поиск по названию"
            )

    except Exception as e:
        logging.error(f"Ошибка в обработчике сообщений: {e}")


async def main():
    try:
        # Проверяем базу данных перед запуском
        logging.info("🔍 Проверяем базу данных...")
        if not user_db.check_database_health():
            logging.error("❌ Проблемы с базой данных, пытаемся восстановить...")
            user_db.force_recreate_database()

        logging.info("🔐 Авторизация...")
        if parser.login(ULSTU_USERNAME, ULSTU_PASSWORD):
            logging.info("✅ Бот запущен!")
        else:
            logging.error("❌ Ошибка авторизации!")

        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
    finally:
        if parser.session:
            parser.session.close()


if __name__ == '__main__':
    asyncio.run(main())