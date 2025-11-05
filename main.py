import asyncio
import logging
import re
import requests
from bs4 import BeautifulSoup

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

logging.basicConfig(level=logging.INFO)

bot = Bot('f9LHodD0cOKVavHDtNLZIJ5CIfFt2IRgT0emk0pQ1AFxZMero5F4Rbt8GNNJmxxRWzIw8qW7CcJ2G55Jalx4')
dp = Dispatcher()


class UlstuParser:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://lk.ulstu.ru"
        self.logged_in = False

    def login(self, username, password):
        """
        Авторизация на портале УлГТУ
        """
        try:
            # URL для авторизации
            login_url = f"{self.base_url}/?q=auth/login"

            # Данные для авторизации
            login_data = {
                'login': username,
                'password': password
            }

            # Выполняем вход
            response = self.session.post(login_url, data=login_data)

            if response.status_code == 200:
                # Проверяем, успешна ли авторизация
                if "Неверный логин или пароль" in response.text:
                    logging.error("❌ Ошибка авторизации: неверный логин или пароль")
                    return False
                else:
                    logging.info("✅ Авторизация успешна!")
                    self.logged_in = True
                    return True
            else:
                logging.error(f"❌ Ошибка при авторизации: код {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"❌ Ошибка при авторизации: {e}")
            return False

    def parse_group_schedule(self, group_url):
        """
        Парсит расписание группы УлГТУ после авторизации
        """
        if not self.logged_in:
            return ["❌ Сначала выполните авторизацию!"]

        try:
            # Загружаем страницу расписания
            response = self.session.get(group_url)
            response.encoding = 'cp1251'

            if response.status_code != 200:
                return [f"❌ Ошибка загрузки страницы: код {response.status_code}"]

            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем информацию о группе и неделе
            group_name = "Неизвестно"
            week_number = "Неизвестно"

            # Ищем заголовки
            headers = soup.find_all(['font', 'b', 'h1', 'h2', 'h3'])
            for header in headers:
                text = header.get_text(strip=True)
                if 'Группа:' in text:
                    group_match = re.search(r'Группа:\s*([^\n]+)', text)
                    if group_match:
                        group_name = group_match.group(1).strip()
                if 'Неделя:' in text:
                    week_match = re.search(r'Неделя:\s*(\d+)', text)
                    if week_match:
                        week_number = week_match.group(1)

            # Ищем таблицы с расписанием
            tables = soup.find_all("table")
            schedules = []

            for table_index, table in enumerate(tables):
                current_week = int(week_number) + table_index if week_number.isdigit() else table_index + 1
                week_type = "Чётная" if current_week % 2 == 0 else "Нечётная"

                # Получаем все строки таблицы
                rows = table.find_all("tr")

                # Пропускаем заголовки (первые 2 строки)
                for row_index in range(2, min(len(rows), 8)):  # Максимум 6 дней
                    day_row = rows[row_index]
                    columns = day_row.find_all("td")

                    if not columns or len(columns) < 2:
                        continue

                    # Название дня недели
                    day_name = columns[0].get_text(strip=True)
                    if not day_name:
                        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
                        day_index = row_index - 2
                        if day_index < len(day_names):
                            day_name = day_names[day_index]

                    # Обрабатываем пары (столбцы 1-8)
                    for col_index in range(1, min(len(columns), 9)):
                        pair_number = col_index
                        cell = columns[col_index]

                        # Извлекаем содержимое ячейки
                        content = cell.get_text(separator='\n', strip=True)

                        if content and content not in ['-', ' ', '_', '']:
                            lesson_details = self.parse_lesson_content(content)
                            if lesson_details:
                                schedule_item = {
                                    'week': current_week,
                                    'day': day_name,
                                    'pair': pair_number,
                                    'subject': lesson_details['subject'],
                                    'type': lesson_details['type'],
                                    'teacher': lesson_details['teacher'],
                                    'classroom': lesson_details['classroom']
                                }
                                schedules.append(schedule_item)

            return self.format_schedule_parts(group_name, week_number, schedules)

        except Exception as e:
            logging.error(f"❌ Ошибка при парсинге: {e}")
            return [f"❌ Ошибка при получении расписания: {str(e)}"]

    def parse_lesson_content(self, content):
        """
        Парсит содержимое ячейки с занятием
        """
        try:
            lines = [line.strip() for line in content.split('\n') if line.strip()]

            if not lines:
                return None

            # Первая строка - предмет и тип
            subject_line = lines[0]

            # Определяем тип занятия
            lesson_type = "Не указан"
            subject_name = subject_line

            type_patterns = {
                'лек': 'Лекция', 'пр': 'Практика', 'лаб': 'Лабораторная',
                'сем': 'Семинар', 'конс': 'Консультация', 'зач': 'Зачёт',
                'экз': 'Экзамен'
            }

            for pattern, full_type in type_patterns.items():
                if subject_line.lower().startswith(pattern):
                    lesson_type = full_type
                    subject_name = subject_line[len(pattern):].strip()
                    subject_name = re.sub(r'^[\.:\-\s]+', '', subject_name)
                    break

            # Преподаватель и аудитория
            teacher = "Не указан"
            classroom = "Не указана"

            if len(lines) > 1:
                teacher_line = lines[1]

                # Ищем аудиторию
                classroom_match = re.search(r'ауд\.?\s*([^\s,]+)', teacher_line, re.IGNORECASE)
                if classroom_match:
                    classroom = f"ауд. {classroom_match.group(1)}"
                    teacher = re.sub(r'ауд\.?\s*[^\s,]+', '', teacher_line, flags=re.IGNORECASE).strip()
                else:
                    teacher = teacher_line

            if len(lines) > 2 and classroom == "Не указана":
                classroom = lines[2]

            # Капитализируем название предмета
            if subject_name:
                subject_name = subject_name.capitalize()

            return {
                'subject': subject_name,
                'type': lesson_type,
                'teacher': teacher,
                'classroom': classroom
            }

        except Exception as e:
            logging.error(f"Ошибка парсинга занятия: {e}")
            return None

    def format_schedule_parts(self, group_name, week_number, schedules):
        """
        Форматирует расписание в читаемый вид для бота и разбивает на части
        """
        if not schedules:
            return [f"📅 Расписание для группы *{group_name}* не найдено"]

        # Группируем по неделям и дням
        weeks = {}
        for item in schedules:
            week = item['week']
            day = item['day']
            if week not in weeks:
                weeks[week] = {}
            if day not in weeks[week]:
                weeks[week][day] = []
            weeks[week][day].append(item)

        parts = []
        current_part = []

        # Заголовок
        header = f"📅 *Расписание для группы {group_name}*\n📆 Текущая неделя: *{week_number}*\n"
        current_part.append(header)

        # Форматируем вывод по неделям
        for week, days in sorted(weeks.items()):
            week_type = "чётная" if week % 2 == 0 else "нечётная"
            week_header = f"\n*{'=' * 40}*\n*Неделя {week} ({week_type})*\n*{'=' * 40}*\n"

            # Проверяем, не превысит ли добавление недели лимит
            if len('\n'.join(current_part) + week_header) > 3500:
                parts.append('\n'.join(current_part))
                current_part = [header]  # Начинаем новую часть с заголовка

            current_part.append(week_header)

            # Добавляем дни недели
            for day, lessons in days.items():
                day_section = f"*📅 {day}:*\n"

                if not lessons:
                    day_section += "   🎉 Выходной!\n\n"
                else:
                    # Сортируем по номеру пары
                    lessons.sort(key=lambda x: x['pair'])

                    for lesson in lessons:
                        time_slots = {
                            1: "08:30-09:50", 2: "10:00-11:20", 3: "11:30-12:50",
                            4: "13:30-14:50", 5: "15:00-16:20", 6: "16:30-17:50",
                            7: "18:00-19:20", 8: "19:30-20:50"
                        }

                        time_slot = time_slots.get(lesson['pair'], "")
                        lesson_text = (
                            f"   🕒 *{lesson['pair']} пара* ({time_slot}):\n"
                            f"      📚 {lesson['subject']}\n"
                            f"      🎯 {lesson['type']}\n"
                            f"      👨‍🏫 {lesson['teacher']}\n"
                            f"      🏫 {lesson['classroom']}\n\n"
                        )

                        # Проверяем, не превысит ли добавление урока лимит
                        if len('\n'.join(current_part) + day_section + lesson_text) > 3500:
                            parts.append('\n'.join(current_part))
                            current_part = [header, week_header, day_section]
                        else:
                            day_section += lesson_text

                current_part.append(day_section)

        # Добавляем последнюю часть
        if current_part:
            # Добавляем статистику в последнюю часть
            stats = f"\n📊 *Всего занятий: {len(schedules)}*"
            if len('\n'.join(current_part) + stats) <= 4000:
                current_part.append(stats)
            parts.append('\n'.join(current_part))

        return parts


# Создаем парсер и авторизуемся
parser = UlstuParser()

# URL расписания для группы (замените на нужную)
SCHEDULE_URL = "https://lk.ulstu.ru/timetable/shared/schedule/Часть%202%20–%20ФИСТ,%20ГФ/61.html"


async def send_schedule_parts(chat_id, schedule_parts):
    """Отправляет расписание частями"""
    if not schedule_parts:
        await bot.send_message(chat_id=chat_id, text="❌ Не удалось получить расписание")
        return

    for i, part in enumerate(schedule_parts):
        # Добавляем номер части если расписание разбито на несколько сообщений
        if len(schedule_parts) > 1:
            part = f"*Часть {i + 1}/{len(schedule_parts)}*\n\n{part}"

        await bot.send_message(chat_id=chat_id, text=part)
        # Небольшая задержка между сообщениями
        await asyncio.sleep(0.5)


# Ответ бота при нажатии на кнопку "Начать"
@dp.bot_started()
async def bot_started(event: BotStarted):
    # Сразу отправляем расписание без сообщения о загрузке
    schedule_parts = parser.parse_group_schedule(SCHEDULE_URL)
    await send_schedule_parts(event.chat_id, schedule_parts)


# Ответ бота на команду /start
@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    # Сразу отправляем расписание без сообщения о загрузке
    schedule_parts = parser.parse_group_schedule(SCHEDULE_URL)

    # Отправляем расписание частями
    for i, part in enumerate(schedule_parts):
        if len(schedule_parts) > 1:
            part = f"*Часть {i + 1}/{len(schedule_parts)}*\n\n{part}"
        await event.message.answer(part)
        await asyncio.sleep(0.5)


# Команда помощи
@dp.message_created(Command('help'))
async def help_command(event: MessageCreated):
    await event.message.answer(
        "ℹ️ *Помощь по использованию бота*\n\n"
        "Просто отправьте /start чтобы получить расписание\n\n"
        "Бот автоматически загружает актуальное расписание\n"
        "с портала УлГТУ"
    )


# Команда для обновления расписания
@dp.message_created(Command('schedule'))
async def get_schedule(event: MessageCreated):
    # Сразу отправляем расписание без сообщения о загрузке
    schedule_parts = parser.parse_group_schedule(SCHEDULE_URL)

    # Отправляем расписание частями
    for i, part in enumerate(schedule_parts):
        if len(schedule_parts) > 1:
            part = f"*Часть {i + 1}/{len(schedule_parts)}*\n\n{part}"
        await event.message.answer(part)
        await asyncio.sleep(0.5)


# Обработка текстовых сообщений
@dp.message_created()
async def handle_message(event: MessageCreated):
    try:
        text = event.message.content.text.strip()

        if text and not text.startswith('/'):
            await event.message.answer(
                "🤔 *Не понял ваше сообщение*\n\n"
                "Отправьте /start чтобы получить расписание\n"
                "Используйте /help для справки"
            )
    except Exception as e:
        logging.error(f"Ошибка в обработке сообщения: {e}")


async def main():
    try:
        # Авторизуемся при запуске бота
        logging.info("🔐 Выполняю авторизацию на портале УлГТУ...")
        if parser.login("a.gajfullin", "zxcasdqwe123"):
            logging.info("✅ Авторизация успешна! Бот запущен и готов к работе!")
        else:
            logging.error("❌ Ошибка авторизации! Проверьте логин и пароль.")

        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Закрываем сессию при завершении
        if parser.session:
            parser.session.close()


if __name__ == '__main__':
    asyncio.run(main())