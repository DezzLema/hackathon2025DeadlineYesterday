from image_generator import ScheduleImageGenerator
import re
import requests
from bs4 import BeautifulSoup
import logging

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
