from image_generator import ScheduleImageGenerator
import re
import requests
from bs4 import BeautifulSoup
import logging
from config import SCHEDULE_BASE_URL, MIN_GROUP_NUMBER, MAX_GROUP_NUMBER
from groups_dict import GROUPS_DICT, GROUPS_REVERSE_DICT  # Добавляем импорт обратного словаря


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

    def get_group_url(self, group_number):
        """Генерирует URL для указанного номера группы"""
        if group_number < MIN_GROUP_NUMBER or group_number > MAX_GROUP_NUMBER:
            raise ValueError(f"Номер группы должен быть от {MIN_GROUP_NUMBER} до {MAX_GROUP_NUMBER}")

        return f"{SCHEDULE_BASE_URL}/{group_number}.html"

    def get_group_name(self, group_number):
        """Получает реальное название группы из словаря"""
        if group_number in GROUPS_DICT:
            return GROUPS_DICT[group_number]
        else:
            return f"Группа_{group_number}"  # Значение по умолчанию

    def find_group_number(self, group_name):
        """Находит номер группы по названию"""
        # Прямой поиск по точному совпадению
        if group_name in GROUPS_REVERSE_DICT:
            return GROUPS_REVERSE_DICT[group_name]

        # Поиск по частичному совпадению (без учета регистра)
        group_name_upper = group_name.upper()
        for name, number in GROUPS_REVERSE_DICT.items():
            if group_name_upper in name.upper():
                return number

        return None

    def parse_all_groups(self):
        """Парсит расписание всех групп от 1 до 119"""
        if not self.logged_in:
            logging.error("❌ Не авторизован для парсинга")
            return {}

        all_groups_data = {}

        for group_number in range(MIN_GROUP_NUMBER, MAX_GROUP_NUMBER + 1):
            try:
                group_url = self.get_group_url(group_number)
                group_name = self.get_group_name(group_number)  # Используем реальное название
                logging.info(f"🔍 Парсим группу {group_number} ({group_name})...")

                parsed_group_name, week_number, schedules = self.parse_group_schedule(group_url)

                # Используем реальное название из словаря вместо распарсенного
                if group_name and schedules:
                    all_groups_data[group_number] = {
                        'name': group_name,  # Используем название из словаря
                        'week': week_number,
                        'schedule': schedules,
                        'url': group_url
                    }
                    logging.info(f"✅ Группа {group_number} ({group_name}): {len(schedules)} занятий")
                else:
                    logging.warning(f"⚠️ Группа {group_number} ({group_name}): расписание не найдено")

                # Небольшая задержка чтобы не перегружать сервер
                import time
                time.sleep(0.5)

            except Exception as e:
                logging.error(f"❌ Ошибка парсинга группы {group_number}: {e}")
                continue

        return all_groups_data

    def parse_group_schedule(self, group_url):
        """Парсит расписание группы УлГТУ - ПОЛНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.logged_in:
            # Получаем номер группы из URL и используем реальное название
            group_number = int(group_url.split('/')[-1].replace('.html', ''))
            group_name = self.get_group_name(group_number)
            return group_name, "1", []

        try:
            logging.info(f"🔍 Загружаю расписание: {group_url}")
            response = self.session.get(group_url)
            response.encoding = 'cp1251'

            if response.status_code != 200:
                logging.warning(f"⚠️ Не удалось загрузить страницу: {response.status_code}")
                # Получаем номер группы из URL и используем реальное название
                group_number = int(group_url.split('/')[-1].replace('.html', ''))
                group_name = self.get_group_name(group_number)
                return group_name, "1", []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Получаем номер группы из URL и используем реальное название
            group_number = int(group_url.split('/')[-1].replace('.html', ''))
            group_name = self.get_group_name(group_number)
            week_number = "1"  # значение по умолчанию

            # ИЩЕМ НОМЕР НЕДЕЛИ В ЗАГОЛОВКЕ
            # Ищем заголовок с неделей
            week_elements = soup.find_all('font', {'color': '#ff00ff', 'face': 'Times New Roman', 'size': '6'})
            for element in week_elements:
                text = element.get_text(strip=True)
                if 'Неделя:' in text:
                    # Извлекаем номер недели (например: "10-я", "11-я")
                    week_match = re.search(r'Неделя:\s*(\d+)-я', text)
                    if week_match:
                        week_number = week_match.group(1)
                        logging.info(f"📅 Найдена неделя: {week_number}")
                    break

            # Если не нашли через элементы, ищем по тексту
            if week_number == "1":
                week_texts = soup.find_all(text=re.compile(r'Неделя:'))
                for text in week_texts:
                    week_match = re.search(r'Неделя:\s*(\d+)-я', str(text))
                    if week_match:
                        week_number = week_match.group(1)
                        logging.info(f"📅 Найдена неделя через текстовый поиск: {week_number}")
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
                        cell_text = cell.get_text()

                        if cell_text and cell_text not in ['', '-', ' ']:
                            # Парсим содержимое ячейки
                            lesson_data = self._parse_cell_content(cell_text)
                            if lesson_data:
                                schedule_item = {
                                    'week': int(week_number),
                                    'day': day_name,
                                    'pair': pair_number,
                                    'subject': lesson_data['subject'],
                                    'type': lesson_data['type'],
                                    'teacher': lesson_data['teacher'],
                                    'classroom': lesson_data['classroom']
                                }
                                schedules.append(schedule_item)
                                logging.info(f"✅ Добавлено: {day_name} {pair_number} пара - {lesson_data['subject']}")

            logging.info(f"📊 Итог: {len(schedules)} занятий для группы {group_name}, неделя {week_number}")
            return group_name, week_number, schedules


        except Exception as e:
            logging.error(f"❌ Ошибка парсинга: {e}")
            # Получаем номер группы из URL и используем реальное название
            group_number = int(group_url.split('/')[-1].replace('.html', ''))
            group_name = self.get_group_name(group_number)
            return group_name, "1", []

    def _parse_cell_content(self, cell_text):
        """Парсит содержимое ячейки с занятием - УЛУЧШЕННАЯ ВЕРСИЯ"""
        try:
            lines = [line.strip() for line in cell_text.split('\n') if line.strip()]

            if not lines:
                return None

            # Первая строка - предмет и тип
            first_line = lines[0]

            # Определяем тип занятия
            lesson_type = "Лекция"
            type_indicators = {
                'пр.': "Практика",
                'практ': "Практика",
                'лаб.': "Лабораторная",
                'лабор': "Лабораторная",
                'сем.': "Семинар",
                'зач.': "Зачёт",
                'экз.': "Экзамен",
                'лек.': "Лекция"
            }

            for indicator, lesson_type_name in type_indicators.items():
                if indicator in first_line.lower():
                    lesson_type = lesson_type_name
                    # Убираем сокращение типа из названия предмета
                    first_line = first_line.lower().replace(indicator, '').strip()
                    if first_line:  # Capitalize только если строка не пустая
                        first_line = first_line.capitalize()
                    break

            # Если не нашли сокращение, но есть русские обозначения
            if lesson_type == "Лекция":
                russian_indicators = {
                    'практика': "Практика",
                    'лабораторная': "Лабораторная",
                    'семинар': "Семинар",
                    'зачёт': "Зачёт",
                    'экзамен': "Экзамен",
                    'лекция': "Лекция"
                }

                for indicator, lesson_type_name in russian_indicators.items():
                    if indicator in first_line.lower():
                        lesson_type = lesson_type_name
                        break

            subject = first_line if first_line else "Не указано"

            # Преподаватель и аудитория
            teacher = "Не указан"
            classroom = "Не указана"

            # ОБНОВЛЕННЫЙ ПАРСИНГ: ищем формат "Фамилия И О номер_аудитории"
            if len(lines) > 1:
                teacher_line = lines[1]

                # Паттерн для поиска формата "Фамилия И О номер_аудитории"
                # Пример: "Лапшов Ю А 3-312", "Щукарев И А 3-314"
                classroom_pattern = r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)*)\s+([А-ЯЁ]\s+[А-ЯЁ])\s+([\d\-_]+)$'
                classroom_match = re.search(classroom_pattern, teacher_line)

                if classroom_match:
                    # Нашли формат с аудиторией в конце
                    teacher_name = classroom_match.group(1)  # Фамилия
                    initials = classroom_match.group(2)  # Инициалы
                    room_number = classroom_match.group(3)  # Номер аудитории

                    teacher = f"{teacher_name} {initials}"
                    classroom = f"ауд. {room_number}"
                    logging.info(f"🎯 Найдена аудитория в формате ФИО+аудитория: {teacher} -> {classroom}")

                else:
                    # Старый метод поиска аудитории
                    old_classroom_match = re.search(r'ауд\.?\s*([^\s,\n]+)', teacher_line, re.IGNORECASE)
                    if old_classroom_match:
                        classroom = f"ауд. {old_classroom_match.group(1)}"
                        teacher = re.sub(r'ауд\.?\s*[^\s,\n]+', '', teacher_line, flags=re.IGNORECASE).strip()
                    else:
                        teacher = teacher_line

            # Дополнительная проверка в третьей строке
            if len(lines) > 2 and classroom == "Не указана":
                third_line = lines[2]
                # Проверяем формат "Фамилия И О номер_аудитории" в третьей строке
                classroom_pattern = r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)*)\s+([А-ЯЁ]\s+[А-ЯЁ])\s+([\d\-_]+)$'
                classroom_match = re.search(classroom_pattern, third_line)

                if classroom_match:
                    teacher_name = classroom_match.group(1)
                    initials = classroom_match.group(2)
                    room_number = classroom_match.group(3)

                    teacher = f"{teacher_name} {initials}"
                    classroom = f"ауд. {room_number}"
                    logging.info(f"🎯 Найдена аудитория в 3-й строке: {teacher} -> {classroom}")
                elif 'ауд.' in third_line.lower():
                    classroom = third_line

            return {
                'subject': subject,
                'type': lesson_type,
                'teacher': teacher if teacher else "Не указан",
                'classroom': classroom
            }

        except Exception as e:
            logging.error(f"❌ Ошибка парсинга ячейки: {e}")
            return None

    def get_schedule_image(self, group_url):
        """Получает расписание и создает изображение"""
        group_name, week_number, schedules = self.parse_group_schedule(group_url)
        return self.image_generator.create_schedule_image(group_name, week_number, schedules)

    def get_schedule_image_by_number(self, group_number):
        """Получает расписание по номеру группы и создает изображение"""
        group_url = self.get_group_url(group_number)
        return self.get_schedule_image(group_url)

    def get_schedule_image_by_name(self, group_name):
        """Получает расписание по названию группы и создает изображение"""
        group_number = self.find_group_number(group_name)
        if group_number:
            return self.get_schedule_image_by_number(group_number)
        else:
            raise ValueError(f"Группа с названием '{group_name}' не найдена")
