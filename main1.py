import asyncio
import logging
import re
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import io
import os

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

logging.basicConfig(level=logging.INFO)

bot = Bot('f9LHodD0cOKVavHDtNLZIJ5CIfFt2IRgT0emk0pQ1AFxZMero5F4Rbt8GNNJmxxRWzIw8qW7CcJ2G55Jalx4')
dp = Dispatcher()


class ScheduleImageGenerator:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 28)
            self.header_font = ImageFont.truetype("arial.ttf", 20)
            self.subheader_font = ImageFont.truetype("arial.ttf", 16)
            self.text_font = ImageFont.truetype("arial.ttf", 12)
            self.small_font = ImageFont.truetype("arial.ttf", 10)
            self.bold_font = ImageFont.truetype("arialbd.ttf", 12)
        except:
            self.title_font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()
            self.subheader_font = ImageFont.load_default()
            self.text_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
            self.bold_font = ImageFont.load_default()

    def create_schedule_image(self, group_name, week_number, schedules):
        """Создает изображение с расписанием"""
        if not schedules:
            return self._create_error_image("Расписание не найдено")

        # Группируем по дням
        days_schedule = {}
        for item in schedules:
            day = item['day']
            if day not in days_schedule:
                days_schedule[day] = []
            days_schedule[day].append(item)

        # Создаем изображение
        width = 1400
        margin = 20
        cell_height = 90
        time_column_width = 120
        day_column_width = (width - margin * 2 - time_column_width) // 6

        total_height = margin * 2
        total_height += 100  # заголовок
        total_height += 40  # дни недели
        total_height += 8 * cell_height  # 8 пар
        total_height += 30  # статистика

        img = Image.new('RGB', (width, total_height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)

        y_position = margin

        # Заголовок
        title = f"Расписание группы: {group_name}"
        draw.text((width // 2, y_position), title, fill='white', font=self.title_font, anchor="mm")
        y_position += 40

        bot_info = "@ulstutimebot"
        draw.text((width // 2, y_position), bot_info, fill='#cccccc', font=self.subheader_font, anchor="mm")
        y_position += 30

        week_info = f"Неделя: {week_number}"
        draw.text((width // 2, y_position), week_info, fill='#cccccc', font=self.subheader_font, anchor="mm")
        y_position += 40

        # Времена пар
        time_slots = {
            1: "08:30-09:50", 2: "10:00-11:20", 3: "11:30-12:50",
            4: "13:30-14:50", 5: "15:00-16:20", 6: "16:30-17:50",
            7: "18:00-19:20", 8: "19:30-20:50"
        }

        # Заголовок времен
        time_header_x = margin
        draw.rectangle([time_header_x, y_position, time_header_x + time_column_width, y_position + 40],
                       fill='#2d2d2d')
        draw.text((time_header_x + time_column_width // 2, y_position + 20), "Пара\nВремя",
                  fill='white', font=self.text_font, anchor="mm", align='center')

        # Дни недели
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
        for i, day in enumerate(days):
            day_x = margin + time_column_width + i * day_column_width
            draw.rectangle([day_x, y_position, day_x + day_column_width, y_position + 40],
                           fill='#2d2d2d')
            draw.text((day_x + day_column_width // 2, y_position + 20), day,
                      fill='white', font=self.bold_font, anchor="mm")

        y_position += 40

        # Сетка расписания
        for pair_num in range(1, 9):
            # Номер пары и время
            pair_x = margin
            draw.rectangle([pair_x, y_position, pair_x + time_column_width, y_position + cell_height],
                           fill='#2d2d2d')
            draw.text((pair_x + time_column_width // 2, y_position + 15), f"{pair_num}",
                      fill='white', font=self.bold_font, anchor="mm")
            draw.text((pair_x + time_column_width // 2, y_position + 35), time_slots[pair_num],
                      fill='#cccccc', font=self.small_font, anchor="mm")

            # Ячейки для дней
            for day_idx, day_name in enumerate(days):
                day_x = margin + time_column_width + day_idx * day_column_width

                # Ищем занятие
                lesson = None
                if day_name in days_schedule:
                    for les in days_schedule[day_name]:
                        if les['pair'] == pair_num:
                            lesson = les
                            break

                # Рисуем ячейку
                cell_color = '#1a1a1a' if not lesson else '#2d2d2d'
                draw.rectangle([day_x, y_position, day_x + day_column_width, y_position + cell_height],
                               fill=cell_color, outline='#444444')

                if lesson:
                    # Форматируем текст
                    subject = self._wrap_text(lesson['subject'], 25)
                    lesson_type = self._truncate_text(lesson['type'], 20)
                    teacher = self._truncate_text(lesson['teacher'], 22)
                    classroom = self._truncate_text(lesson['classroom'], 20)

                    # Рисуем текст
                    text_y = y_position + 5

                    # Предмет (может быть в несколько строк)
                    subject_lines = subject.split('\n')
                    for line in subject_lines[:2]:  # Максимум 2 строки
                        draw.text((day_x + 5, text_y), line, fill='white', font=self.small_font)
                        text_y += 12

                    text_y += 2
                    draw.text((day_x + 5, text_y), lesson_type, fill='#ff6b6b', font=self.small_font)
                    text_y += 12
                    draw.text((day_x + 5, text_y), teacher, fill='#4ecdc4', font=self.small_font)
                    text_y += 12
                    draw.text((day_x + 5, text_y), classroom, fill='#ffe66d', font=self.small_font)

            y_position += cell_height

        # Статистика
        total_lessons = len(schedules)
        stats_text = f"Всего занятий: {total_lessons}"
        draw.text((width // 2, y_position + 15), stats_text, fill='#cccccc', font=self.text_font, anchor="mm")

        return img

    def _truncate_text(self, text, max_length):
        """Обрезает текст"""
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text

    def _wrap_text(self, text, max_length):
        """Переносит текст на новую строку"""
        if len(text) <= max_length:
            return text

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= max_length:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                if len(current_line) > max_length:
                    current_line = current_line[:max_length - 3] + "..."

        if current_line:
            lines.append(current_line)

        return '\n'.join(lines[:2])  # Максимум 2 строки

    def _create_error_image(self, error_message):
        """Создает изображение с ошибкой"""
        img = Image.new('RGB', (800, 400), color='#1a1a1a')
        draw = ImageDraw.Draw(img)
        draw.text((400, 150), "Ошибка", fill='#ff6b6b', font=self.title_font, anchor="mm")
        draw.text((400, 200), error_message, fill='white', font=self.text_font, anchor="mm")
        return img

    def image_to_bytes(self, image):
        """Конвертирует изображение в bytes"""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr


class UlstuParser:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://lk.ulstu.ru"
        self.logged_in = False
        self.image_generator = ScheduleImageGenerator()

    def login(self, username, password):
        """Авторизация на портале УлГТУ"""
        try:
            login_url = f"{self.base_url}/?q=auth/login"
            login_data = {
                'login': username,
                'password': password
            }

            response = self.session.post(login_url, data=login_data)

            if response.status_code == 200:
                if "Неверный логин или пароль" in response.text:
                    logging.error("❌ Ошибка авторизации: неверный логин или пароль")
                    return False
                else:
                    logging.info("✅ Авторизация успешна!")
                    self.logged_in = True
                    return True
            else:
                logging.error(f"❌ Ошибка при авторизации: {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"❌ Ошибка при авторизации: {e}")
            return False

    def parse_group_schedule(self, group_url):
        """Парсит расписание группы УлГТУ - УЛУЧШЕННАЯ ВЕРСИЯ"""
        if not self.logged_in:
            return None, "1", []

        try:
            logging.info(f"🔍 Загружаю расписание...")
            response = self.session.get(group_url)
            response.encoding = 'cp1251'

            if response.status_code != 200:
                return None, "1", []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Сохраняем HTML для отладки
            with open("debug_page.html", "w", encoding='utf-8') as f:
                f.write(soup.prettify())
            logging.info("✅ HTML сохранен в debug_page.html")

            # Ищем информацию о группе
            group_name = "ИВТИИбд-32"  # Значение по умолчанию
            week_number = "1"

            # Ищем заголовок с группой
            headers = soup.find_all(['b', 'h1', 'h2', 'h3', 'font'])
            for header in headers:
                text = header.get_text(strip=True)
                if 'Группа:' in text:
                    group_match = re.search(r'Группа:\s*([^\n]+)', text)
                    if group_match:
                        group_name = group_match.group(1).strip()
                        break

            # Ищем все таблицы
            tables = soup.find_all("table", {"border": "1"})
            if not tables:
                tables = soup.find_all("table")

            logging.info(f"🔍 Найдено таблиц: {len(tables)}")

            schedules = []
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

            if tables:
                # Берем первую таблицу (первая неделя)
                table = tables[0]
                rows = table.find_all("tr")
                logging.info(f"🔍 Найдено строк в таблице: {len(rows)}")

                # Пропускаем заголовки (первые 2 строки)
                for row_idx in range(2, min(len(rows), 8)):
                    row = rows[row_idx]
                    cells = row.find_all(["td", "th"])

                    if len(cells) < 2:
                        continue

                    # Определяем день недели
                    day_name = day_names[row_idx - 2] if (row_idx - 2) < len(day_names) else f"День{row_idx - 1}"

                    # Обрабатываем ячейки с парами (начиная со второй ячейки)
                    for cell_idx in range(1, min(len(cells), 9)):
                        cell = cells[cell_idx]
                        pair_number = cell_idx

                        # Получаем текст ячейки
                        cell_text = cell.get_text(separator='\n', strip=True)

                        if cell_text and cell_text not in ['', '-', ' ']:
                            # Парсим содержимое ячейки
                            lesson_data = self._parse_cell_content(cell_text)
                            if lesson_data:
                                schedule_item = {
                                    'week': 1,
                                    'day': day_name,
                                    'pair': pair_number,
                                    'subject': lesson_data['subject'],
                                    'type': lesson_data['type'],
                                    'teacher': lesson_data['teacher'],
                                    'classroom': lesson_data['classroom']
                                }
                                schedules.append(schedule_item)
                                logging.info(f"✅ Добавлено: {day_name} {pair_number} пара - {lesson_data['subject']}")

            # Если не нашли занятий, создаем тестовые данные
            if not schedules:
                logging.warning("⚠️ Занятий не найдено, создаю тестовые данные")
                schedules = self._create_test_schedule()

            logging.info(f"📊 Итог: {len(schedules)} занятий")
            return group_name, week_number, schedules

        except Exception as e:
            logging.error(f"❌ Ошибка парсинга: {e}")
            # Возвращаем тестовые данные при ошибке
            return "ИВТИИбд-32", "1", self._create_test_schedule()

    def _parse_cell_content(self, cell_text):
        """Парсит содержимое ячейки с занятием"""
        try:
            lines = [line.strip() for line in cell_text.split('\n') if line.strip()]

            if not lines:
                return None

            # Первая строка - предмет и тип
            first_line = lines[0].lower()

            # Определяем тип занятия
            lesson_type = "Лекция"
            if 'пр.' in first_line or 'практ' in first_line:
                lesson_type = "Практика"
            elif 'лаб.' in first_line or 'лабор' in first_line:
                lesson_type = "Лабораторная"
            elif 'сем.' in first_line:
                lesson_type = "Семинар"
            elif 'зач.' in first_line:
                lesson_type = "Зачёт"
            elif 'экз.' in first_line:
                lesson_type = "Экзамен"

            # Извлекаем название предмета (убираем сокращения типа)
            subject = lines[0]
            for abbrev in ['лек.', 'пр.', 'лаб.', 'сем.', 'зач.', 'экз.']:
                if abbrev in subject.lower():
                    subject = subject.lower().replace(abbrev, '').strip().capitalize()
                    break

            # Преподаватель и аудитория
            teacher = "Не указан"
            classroom = "Не указана"

            if len(lines) > 1:
                teacher_line = lines[1]
                # Ищем аудиторию
                classroom_match = re.search(r'ауд\.?\s*([^\s,\n]+)', teacher_line, re.IGNORECASE)
                if classroom_match:
                    classroom = f"ауд. {classroom_match.group(1)}"
                    teacher = re.sub(r'ауд\.?\s*[^\s,\n]+', '', teacher_line, flags=re.IGNORECASE).strip()
                else:
                    teacher = teacher_line

            if len(lines) > 2:
                # Третья строка может быть аудиторией или продолжением
                third_line = lines[2]
                if 'ауд.' in third_line.lower() and classroom == "Не указана":
                    classroom = third_line

            return {
                'subject': subject if subject else "Не указано",
                'type': lesson_type,
                'teacher': teacher if teacher else "Не указан",
                'classroom': classroom
            }

        except Exception as e:
            logging.error(f"❌ Ошибка парсинга ячейки: {e}")
            return None

    def _create_test_schedule(self):
        """Создает тестовое расписание для демонстрации"""
        test_schedule = [
            {
                'week': 1,
                'day': 'Пн',
                'pair': 1,
                'subject': 'Математика',
                'type': 'Лекция',
                'teacher': 'Иванов И.И.',
                'classroom': 'ауд. 101'
            },
            {
                'week': 1,
                'day': 'Пн',
                'pair': 3,
                'subject': 'Программирование',
                'type': 'Практика',
                'teacher': 'Петров П.П.',
                'classroom': 'ауд. 205'
            },
            {
                'week': 1,
                'day': 'Вт',
                'pair': 2,
                'subject': 'Физика',
                'type': 'Лекция',
                'teacher': 'Сидоров С.С.',
                'classroom': 'ауд. 301'
            },
            {
                'week': 1,
                'day': 'Ср',
                'pair': 4,
                'subject': 'Базы данных',
                'type': 'Лабораторная',
                'teacher': 'Кузнецов К.К.',
                'classroom': 'ауд. 410'
            },
            {
                'week': 1,
                'day': 'Чт',
                'pair': 1,
                'subject': 'Веб-разработка',
                'type': 'Практика',
                'teacher': 'Смирнов С.С.',
                'classroom': 'ауд. 315'
            },
            {
                'week': 1,
                'day': 'Пт',
                'pair': 5,
                'subject': 'Алгоритмы',
                'type': 'Лекция',
                'teacher': 'Васильев В.В.',
                'classroom': 'ауд. 201'
            }
        ]
        return test_schedule

    def get_schedule_image(self, group_url):
        """Получает расписание и создает изображение"""
        group_name, week_number, schedules = self.parse_group_schedule(group_url)
        return self.image_generator.create_schedule_image(group_name, week_number, schedules)


# Создаем парсер
parser = UlstuParser()
SCHEDULE_URL = "https://lk.ulstu.ru/timetable/shared/schedule/Часть%202%20–%20ФИСТ,%20ГФ/61.html"


async def send_schedule_image(chat_id, image):
    """Отправляет изображение с расписанием"""
    try:
        # Сохраняем изображение локально
        image_bytes_io = parser.image_generator.image_to_bytes(image)
        with open("schedule.png", "wb") as f:
            f.write(image_bytes_io.getvalue())

        logging.info("✅ Изображение сохранено как schedule.png")

        await bot.send_message(
            chat_id=chat_id,
            text="📅 *Расписание готово!*\nФайл сохранен как 'schedule.png'"
        )

    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        await bot.send_message(chat_id=chat_id, text="❌ Ошибка при создании расписания")


# Обработчики команд
@dp.bot_started()
async def bot_started(event: BotStarted):
    try:
        await bot.send_message(chat_id=event.chat_id, text="🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)
        await send_schedule_image(event.chat_id, schedule_image)
    except Exception as e:
        await bot.send_message(chat_id=event.chat_id, text="❌ Ошибка при запуске")


@dp.message_created(Command('start'))
async def hello(event: MessageCreated):
    try:
        await event.message.answer("🔄 Загружаю расписание...")
        schedule_image = parser.get_schedule_image(SCHEDULE_URL)

        image_bytes_io = parser.image_generator.image_to_bytes(schedule_image)
        with open("schedule.png", "wb") as f:
            f.write(image_bytes_io.getvalue())

        await event.message.answer("📅 *Расписание готово!*\nФайл сохранен как 'schedule.png'")

    except Exception as e:
        await event.message.answer("❌ Ошибка при получении расписания")


@dp.message_created(Command('debug'))
async def debug_info(event: MessageCreated):
    """Показывает отладочную информацию"""
    try:
        group_name, week_number, schedules = parser.parse_group_schedule(SCHEDULE_URL)

        debug_text = f"""
🔍 *Отладочная информация:*

📊 Группа: {group_name}
📅 Неделя: {week_number}
📚 Занятий: {len(schedules)}

📋 *Расписание:*
"""

        if schedules:
            for lesson in schedules[:10]:  # Показываем первые 10 занятий
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


@dp.message_created(Command('help'))
async def help_command(event: MessageCreated):
    await event.message.answer(
        "ℹ️ *Команды:*\n"
        "/start - Получить расписание\n"
        "/debug - Отладочная информация\n"
        "/help - Справка"
    )


@dp.message_created()
async def handle_message(event: MessageCreated):
    try:
        text = event.message.content.text.strip()
        if text and not text.startswith('/'):
            await event.message.answer("🤔 Используйте /start для расписания")
    except Exception as e:
        logging.error(f"Ошибка: {e}")


async def main():
    try:
        logging.info("🔐 Авторизация...")
        if parser.login("a.gajfullin", "zxcasdqwe123"):
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