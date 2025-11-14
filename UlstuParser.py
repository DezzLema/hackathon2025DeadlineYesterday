from image_generator import ScheduleImageGenerator
import re
import requests
from bs4 import BeautifulSoup
import logging
from config import SCHEDULE_BASE_URL, MIN_GROUP_NUMBER, MAX_GROUP_NUMBER, SCHEDULE_PARTS
from groups_dict import GROUPS_DICT, GROUPS_REVERSE_DICT  # Добавляем импорт обратного словаря
from teachers_dict import TEACHERS_DICT, TEACHERS_REVERSE_DICT


class UlstuParser:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://lk.ulstu.ru"
        self.logged_in = False
        self.image_generator = ScheduleImageGenerator()
        self.image_generator = ScheduleImageGenerator()

    def get_schedule_part_for_group(self, group_number):
        """Определяет к какой части расписания принадлежит группа"""
        for part_id, part_data in SCHEDULE_PARTS.items():
            if part_data['min_group'] <= group_number <= part_data['max_group']:
                return part_id, part_data
        # Если группа не найдена в частях, используем часть 2 по умолчанию
        return 2, SCHEDULE_PARTS[2]

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

                    # Проверяем реальную авторизацию, делая тестовый запрос
                    test_url = "https://lk.ulstu.ru/timetable/shared/schedule/Часть%202%20–%20ФИСТ,%20ГФ/60.html"
                    test_response = self.session.get(test_url)
                    if test_response.status_code == 200 and "расписание" in test_response.text.lower():
                        logging.info("✅ Авторизация подтверждена, доступ к расписанию есть")
                    else:
                        logging.warning("⚠️ Авторизация есть, но доступ к расписанию ограничен")
                    return True
            else:
                logging.error(f"❌ Ошибка при авторизации: {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"❌ Ошибка при авторизации: {e}")
            return False

    def get_group_url(self, group_number):
        """Генерирует URL для указанного номера группы с учетом части расписания"""
        if group_number < MIN_GROUP_NUMBER or group_number > MAX_GROUP_NUMBER:
            raise ValueError(f"Номер группы должен быть от {MIN_GROUP_NUMBER} до {MAX_GROUP_NUMBER}")

        part_id, part_data = self.get_schedule_part_for_group(group_number)

        # Преобразуем номер группы для URL
        if part_id == 1:
            url_group_number = group_number  # 1-115
        elif part_id == 2:
            url_group_number = group_number - 115  # 116-234 → 1-119
        elif part_id == 3:
            url_group_number = group_number - 234  # 235-464 → 1-230
        elif part_id == 4:
            url_group_number = group_number - 464  # 465-562 → 1-98
        else:  # part_id == 5
            url_group_number = group_number - 562  # 563-595 → 1-33

        url = part_data['url_template'].format(url_group_number)
        logging.info(f"🔗 Формирую URL для группы {group_number}: {url}")
        return url

    def get_group_name(self, group_number):
        """Получает реальное название группы из словаря"""
        if group_number in GROUPS_DICT:
            return GROUPS_DICT[group_number]
        else:
            return f"Группа_{group_number}"

    def find_group_number(self, group_name):
        """Находит номер группы по названию"""
        if group_name in GROUPS_REVERSE_DICT:
            return GROUPS_REVERSE_DICT[group_name]

        group_name_upper = group_name.upper()
        for name, number in GROUPS_REVERSE_DICT.items():
            if group_name_upper in name.upper():
                return number

        return None

    def parse_all_groups(self):
        """Парсит расписание всех групп"""
        if not self.logged_in:
            logging.error("❌ Не авторизован для парсинга")
            return {}

        all_groups_data = {}

        for group_number in range(MIN_GROUP_NUMBER, MAX_GROUP_NUMBER + 1):
            try:
                group_url = self.get_group_url(group_number)
                group_name = self.get_group_name(group_number)
                logging.info(f"🔍 Парсим группу {group_number} ({group_name})...")

                parsed_group_name, week_number, schedules = self.parse_group_schedule(group_url)

                if group_name and schedules:
                    all_groups_data[group_number] = {
                        'name': group_name,
                        'week': week_number,
                        'schedule': schedules,
                        'url': group_url
                    }
                    logging.info(f"✅ Группа {group_number} ({group_name}): {len(schedules)} занятий")
                else:
                    logging.warning(f"⚠️ Группа {group_number} ({group_name}): расписание не найдено")

                import time
                time.sleep(0.5)

            except Exception as e:
                logging.error(f"❌ Ошибка парсинга группы {group_number}: {e}")
                continue

        return all_groups_data

    def parse_group_schedule(self, group_url):
        """Парсит расписание группы УлГТУ"""
        try:
            logging.info(f"🔍 Загружаю расписание: {group_url}")
            response = self.session.get(group_url)
            response.encoding = 'cp1251'

            if response.status_code != 200:
                logging.warning(f"⚠️ Не удалось загрузить страницу: {response.status_code}")
                # Пытаемся извлечь номер группы из URL
                try:
                    group_number_match = re.search(r'/(\d+)\.html', group_url)
                    if group_number_match:
                        url_group_number = int(group_number_match.group(1))

                        # Определяем часть по URL
                        if 'Часть%201' in group_url or 'Часть 1' in group_url:
                            actual_group_number = url_group_number
                        elif 'Часть%202' in group_url or 'Часть 2' in group_url:
                            actual_group_number = url_group_number + 115
                        elif 'Часть%203' in group_url or 'Часть 3' in group_url:
                            actual_group_number = url_group_number + 234
                        elif 'Часть%204' in group_url or 'Часть 4' in group_url:
                            actual_group_number = url_group_number + 464
                        elif 'Часть%205' in group_url or 'Часть 5' in group_url:
                            actual_group_number = url_group_number + 562
                        else:
                            actual_group_number = url_group_number

                        group_name = self.get_group_name(actual_group_number)
                    else:
                        group_name = "Неизвестная группа"
                except:
                    group_name = "Неизвестная группа"
                return group_name, "1", []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Извлекаем номер группы из URL для определения реального номера
            group_number_match = re.search(r'/(\d+)\.html', group_url)
            if group_number_match:
                url_group_number = int(group_number_match.group(1))

                # Определяем часть по URL
                if 'Часть%201' in group_url or 'Часть 1' in group_url:
                    actual_group_number = url_group_number
                elif 'Часть%202' in group_url or 'Часть 2' in group_url:
                    actual_group_number = url_group_number + 115
                elif 'Часть%203' in group_url or 'Часть 3' in group_url:
                    actual_group_number = url_group_number + 234
                elif 'Часть%204' in group_url or 'Часть 4' in group_url:
                    actual_group_number = url_group_number + 464
                elif 'Часть%205' in group_url or 'Часть 5' in group_url:
                    actual_group_number = url_group_number + 562
                else:
                    actual_group_number = url_group_number

                group_name = self.get_group_name(actual_group_number)
            else:
                group_name = "Неизвестная группа"

            week_number = "1"

            # Поиск номера недели
            week_elements = soup.find_all('font', {'color': '#ff00ff', 'face': 'Times New Roman', 'size': '6'})
            for element in week_elements:
                text = element.get_text(strip=True)
                if 'Неделя:' in text:
                    week_match = re.search(r'Неделя:\s*(\d+)-я', text)
                    if week_match:
                        week_number = week_match.group(1)
                        logging.info(f"📅 Найдена неделя: {week_number}")
                    break

            if week_number == "1":
                week_texts = soup.find_all(text=re.compile(r'Неделя:'))
                for text in week_texts:
                    week_match = re.search(r'Неделя:\s*(\d+)-я', str(text))
                    if week_match:
                        week_number = week_match.group(1)
                        logging.info(f"📅 Найдена неделя через текст: {week_number}")
                        break

            # Поиск таблиц
            tables = soup.find_all("table", {"border": "1"})
            if not tables:
                tables = soup.find_all("table", {"class": re.compile(r'table|schedule', re.I)})
            if not tables:
                tables = soup.find_all("table")

            if not tables:
                schedule_tables = []
                all_tables = soup.find_all("table")
                for table in all_tables:
                    table_text = table.get_text().lower()
                    if any(word in table_text for word in
                           ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'пара', 'понедельник', 'вторник']):
                        schedule_tables.append(table)
                tables = schedule_tables

            logging.info(f"🔍 Найдено таблиц: {len(tables)}")

            schedules = []
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

            if tables:
                for table_idx, table in enumerate(tables):
                    logging.info(f"🔍 Анализирую таблицу {table_idx + 1}")
                    rows = table.find_all("tr")
                    logging.info(f"🔍 Найдено строк в таблице: {len(rows)}")

                    for row_idx in range(2, min(len(rows), 8)):
                        row = rows[row_idx]
                        cells = row.find_all(["td", "th"])

                        if len(cells) < 2:
                            continue

                        day_name = day_names[row_idx - 2] if (row_idx - 2) < len(day_names) else f"День{row_idx - 1}"

                        for cell_idx in range(1, min(len(cells), 9)):
                            cell = cells[cell_idx]
                            pair_number = cell_idx
                            cell_text = cell.get_text(separator='\n', strip=True)

                            if cell_text and cell_text not in ['', '-', ' ']:
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
                                    logging.info(f"✅ {day_name} {pair_number} пара - {lesson_data['subject']}")

                    if schedules:
                        break

            logging.info(f"📊 Итог: {len(schedules)} занятий для {group_name}, неделя {week_number}")
            return group_name, week_number, schedules

        except Exception as e:
            logging.error(f"❌ Ошибка парсинга: {e}")
            import traceback
            logging.error(f"❌ Трассировка: {traceback.format_exc()}")
            try:
                group_number_match = re.search(r'/(\d+)\.html', group_url)
                if group_number_match:
                    url_group_number = int(group_number_match.group(1))

                    if 'Часть%201' in group_url or 'Часть 1' in group_url:
                        actual_group_number = url_group_number
                    elif 'Часть%202' in group_url or 'Часть 2' in group_url:
                        actual_group_number = url_group_number + 115
                    elif 'Часть%203' in group_url or 'Часть 3' in group_url:
                        actual_group_number = url_group_number + 234
                    elif 'Часть%204' in group_url or 'Часть 4' in group_url:
                        actual_group_number = url_group_number + 464
                    elif 'Часть%205' in group_url or 'Часть 5' in group_url:
                        actual_group_number = url_group_number + 562
                    else:
                        actual_group_number = url_group_number

                    group_name = self.get_group_name(actual_group_number)
                else:
                    group_name = "Неизвестная группа"
            except:
                group_name = "Неизвестная группа"
            return group_name, "1", []

    def _parse_cell_content(self, cell_text):
        """Парсит содержимое ячейки с занятием — с поддержкой аудиторий 3_2, 3-312, 3-ДОТ"""
        try:
            lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
            if not lines:
                return None

            first_line = lines[0].lower()

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

            subject = lines[0]
            for abbrev in ['лек.', 'пр.', 'лаб.', 'сем.', 'зач.', 'экз.']:
                if abbrev in subject.lower():
                    subject = subject.lower().replace(abbrev, '').strip().capitalize()
                    break

            teacher = "Не указан"
            classroom = "Не указана"

            # Поддерживаем все форматы: 3_2, 3-312, 3-ДОТ, ауд. 3_1 и т.д.
            if len(lines) > 1:
                teacher_line = lines[1]

                classroom_pattern = (
                    r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)*)\s+'  # Фамилия Имя
                    r'([А-ЯЁ]\s*[А-ЯЁ])\s+'  # Инициалы
                    r'((?:\d+[\-_][\dА-ЯA-Zа-яa-z]+)|(?:\d+\s*-\s*ДОТ)|(?:\d+_ДОТ)|(?:\d+\s*ДОТ))$'  # Поддержка 6-НБ8
                )
                classroom_match = re.search(classroom_pattern, teacher_line, re.IGNORECASE)

                if classroom_match:
                    teacher_name = classroom_match.group(1)
                    initials = classroom_match.group(2)
                    room_number = classroom_match.group(3).replace(' ', '')

                    teacher = f"{teacher_name} {initials}"
                    classroom = f"ауд. {room_number.upper()}"

                    logging.info(f"🎯 Найдена аудитория: {teacher} -> {classroom}")
                else:
                    # Проверяем просто "ауд. ..." без ФИО
                    old_classroom_match = re.search(r'ауд\.?\s*([^\s,\n]+)', teacher_line, re.IGNORECASE)
                    if old_classroom_match:
                        classroom = f"ауд. {old_classroom_match.group(1)}"
                        teacher = re.sub(r'ауд\.?\s*[^\s,\n]+', '', teacher_line, flags=re.IGNORECASE).strip()
                    else:
                        teacher = teacher_line

            if len(lines) > 2 and classroom == "Не указана":
                third_line = lines[2]
                classroom_match = re.search(classroom_pattern, third_line, re.IGNORECASE)
                if classroom_match:
                    teacher_name = classroom_match.group(1)
                    initials = classroom_match.group(2)
                    room_number = classroom_match.group(3).replace(' ', '')
                    teacher = f"{teacher_name} {initials}"
                    classroom = f"ауд. {room_number.upper()}"
                    logging.info(f"🎯 Найдена аудитория в 3-й строке: {teacher} -> {classroom}")
                elif 'ауд.' in third_line.lower():
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

    def get_schedule_image(self, group_url):
        group_name, week_number, schedules = self.parse_group_schedule(group_url)
        return self.image_generator.create_schedule_image(group_name, week_number, schedules)

    def get_schedule_image_by_number(self, group_number):
        group_url = self.get_group_url(group_number)
        return self.get_schedule_image(group_url)

    def get_schedule_image_by_name(self, group_name):
        group_number = self.find_group_number(group_name)
        if group_number:
            return self.get_schedule_image_by_number(group_number)
        else:
            raise ValueError(f"Группа с названием '{group_name}' не найдена")

    def get_teacher_url(self, teacher_number):
        """Генерирует URL для указанного номера преподавателя"""
        return f"https://lk.ulstu.ru/timetable/shared/teachers/m{teacher_number}.html"

    def get_teacher_name(self, teacher_number):
        """Получает имя преподавателя по номеру"""
        if teacher_number in TEACHERS_DICT:
            return TEACHERS_DICT[teacher_number]
        else:
            return f"Преподаватель_{teacher_number}"

    def find_teacher_number(self, teacher_name):
        """Находит номер преподавателя по фамилии (без инициалов)"""
        teacher_name_lower = teacher_name.lower().strip()

        # Ищем точное совпадение по фамилии
        for name, number in TEACHERS_REVERSE_DICT.items():
            # Извлекаем фамилию из полного имени (первое слово)
            surname = name.split()[0].lower()
            if teacher_name_lower == surname:
                return number

        # Если точного совпадения нет, ищем частичное
        for name, number in TEACHERS_REVERSE_DICT.items():
            if teacher_name_lower in name.lower():
                return number

        return None

    def parse_teacher_schedule(self, teacher_url):
        """Парсит расписание преподавателя"""
        try:
            logging.info(f"🔍 Загружаю расписание преподавателя: {teacher_url}")
            response = self.session.get(teacher_url)
            response.encoding = 'cp1251'

            if response.status_code != 200:
                logging.warning(f"⚠️ Не удалось загрузить страницу преподавателя: {response.status_code}")
                return "Неизвестный преподаватель", "1", []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Извлекаем имя преподавателя из заголовка
            teacher_name = "Неизвестный преподаватель"
            title_elements = soup.find_all('font', {'size': '6'})
            for element in title_elements:
                text = element.get_text(strip=True)
                if text and "расписание" in text.lower():
                    # Извлекаем имя из заголовка
                    name_match = re.search(r'расписание\s+преподавателя\s+(.+)', text, re.IGNORECASE)
                    if name_match:
                        teacher_name = name_match.group(1).strip()
                    break

            week_number = "1"

            # Поиск номера недели (аналогично групповому расписанию)
            week_elements = soup.find_all('font', {'color': '#ff00ff', 'face': 'Times New Roman', 'size': '6'})
            for element in week_elements:
                text = element.get_text(strip=True)
                if 'Неделя:' in text:
                    week_match = re.search(r'Неделя:\s*(\d+)-я', text)
                    if week_match:
                        week_number = week_match.group(1)
                        logging.info(f"📅 Найдена неделя преподавателя: {week_number}")
                    break

            # Поиск таблиц расписания
            tables = soup.find_all("table", {"border": "1"})
            if not tables:
                tables = soup.find_all("table", {"class": re.compile(r'table|schedule', re.I)})
            if not tables:
                tables = soup.find_all("table")

            if not tables:
                schedule_tables = []
                all_tables = soup.find_all("table")
                for table in all_tables:
                    table_text = table.get_text().lower()
                    if any(word in table_text for word in
                           ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'пара', 'понедельник', 'вторник']):
                        schedule_tables.append(table)
                tables = schedule_tables

            logging.info(f"🔍 Найдено таблиц преподавателя: {len(tables)}")

            schedules = []
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

            if tables:
                for table_idx, table in enumerate(tables):
                    logging.info(f"🔍 Анализирую таблицу преподавателя {table_idx + 1}")
                    rows = table.find_all("tr")
                    logging.info(f"🔍 Найдено строк в таблице преподавателя: {len(rows)}")

                    for row_idx in range(2, min(len(rows), 8)):
                        row = rows[row_idx]
                        cells = row.find_all(["td", "th"])

                        if len(cells) < 2:
                            continue

                        day_name = day_names[row_idx - 2] if (row_idx - 2) < len(day_names) else f"День{row_idx - 1}"

                        for cell_idx in range(1, min(len(cells), 9)):
                            cell = cells[cell_idx]
                            pair_number = cell_idx
                            cell_text = cell.get_text(separator='\n', strip=True)

                            if cell_text and cell_text not in ['', '-', ' ']:
                                lesson_data = self._parse_teacher_cell_content(cell_text)
                                if lesson_data:
                                    schedule_item = {
                                        'week': int(week_number),
                                        'day': day_name,
                                        'pair': pair_number,
                                        'subject': lesson_data['subject'],
                                        'type': lesson_data['type'],
                                        'group': lesson_data['group'],  # Вместо teacher теперь group
                                        'classroom': lesson_data['classroom']
                                    }
                                    schedules.append(schedule_item)
                                    logging.info(
                                        f"✅ {day_name} {pair_number} пара - {lesson_data['subject']} для {lesson_data['group']}")

                    if schedules:
                        break

            logging.info(f"📊 Итог преподавателя: {len(schedules)} занятий для {teacher_name}, неделя {week_number}")
            return teacher_name, week_number, schedules

        except Exception as e:
            logging.error(f"❌ Ошибка парсинга расписания преподавателя: {e}")
            import traceback
            logging.error(f"❌ Трассировка преподавателя: {traceback.format_exc()}")
            return "Неизвестный преподаватель", "1", []

    def _parse_teacher_cell_content(self, cell_text):
        """Парсит содержимое ячейки с занятием преподавателя"""
        try:
            lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
            if not lines:
                return None

            first_line = lines[0].lower()

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

            subject = lines[0]
            for abbrev in ['лек.', 'пр.', 'лаб.', 'сем.', 'зач.', 'экз.']:
                if abbrev in subject.lower():
                    subject = subject.lower().replace(abbrev, '').strip().capitalize()
                    break

            group = "Не указана"
            classroom = "Не указана"

            # Для преподавателя ищем группу во второй строке
            if len(lines) > 1:
                group_line = lines[1]

                # Пытаемся найти название группы (формат: АБВ-11, ИВТИИбд-32 и т.д.)
                group_match = re.search(r'([А-ЯЁ]{2,}[-–]\d+[а-я]*)', group_line)
                if group_match:
                    group = group_match.group(1)
                    # Остаток строки - возможно, аудитория
                    remaining_text = group_line.replace(group, '').strip()
                    if remaining_text:
                        classroom_match = re.search(r'(\d+[\-_][\dА-ЯA-Z]+|\d+\s*-\s*ДОТ|\d+_ДОТ|\d+\s*ДОТ)',
                                                    remaining_text)
                        if classroom_match:
                            classroom = f"ауд. {classroom_match.group(1)}"
                        elif 'ауд.' in remaining_text.lower():
                            classroom = remaining_text
                else:
                    # Если группы нет, возможно это аудитория
                    classroom_match = re.search(r'ауд\.?\s*([^\s,\n]+)', group_line, re.IGNORECASE)
                    if classroom_match:
                        classroom = f"ауд. {classroom_match.group(1)}"
                    else:
                        group = group_line  # Если не нашли группу и аудиторию, используем всю строку как группу

            if len(lines) > 2 and classroom == "Не указана":
                third_line = lines[2]
                classroom_match = re.search(r'ауд\.?\s*([^\s,\n]+)', third_line, re.IGNORECASE)
                if classroom_match:
                    classroom = f"ауд. {classroom_match.group(1)}"

            return {
                'subject': subject if subject else "Не указано",
                'type': lesson_type,
                'group': group if group else "Не указана",
                'classroom': classroom
            }

        except Exception as e:
            logging.error(f"❌ Ошибка парсинга ячейки преподавателя: {e}")
            return None

    def get_teacher_schedule_image(self, teacher_url):
        """Получает изображение расписания преподавателя"""
        teacher_name, week_number, schedules = self.parse_teacher_schedule(teacher_url)
        return self.image_generator.create_teacher_schedule_image(teacher_name, week_number, schedules)

    def get_teacher_schedule_image_by_number(self, teacher_number):
        """Получает изображение расписания преподавателя по номеру"""
        teacher_url = self.get_teacher_url(teacher_number)
        return self.get_teacher_schedule_image(teacher_url)

    def get_teacher_schedule_image_by_name(self, teacher_name):
        """Получает изображение расписания преподавателя по имени"""
        teacher_number = self.find_teacher_number(teacher_name)
        if teacher_number:
            return self.get_teacher_schedule_image_by_number(teacher_number)
        else:
            raise ValueError(f"Преподаватель с фамилией '{teacher_name}' не найден")
