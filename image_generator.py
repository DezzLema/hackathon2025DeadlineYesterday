from PIL import Image, ImageDraw, ImageFont
import io
import logging


class ScheduleImageGenerator:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 24)
            self.header_font = ImageFont.truetype("arial.ttf", 18)
            self.subheader_font = ImageFont.truetype("arial.ttf", 14)
            self.text_font = ImageFont.truetype("arial.ttf", 11)
            self.small_font = ImageFont.truetype("arial.ttf", 10)
            self.bold_font = ImageFont.truetype("arialbd.ttf", 11)
            self.bob_font = ImageFont.truetype("arialbd.ttf", 12)
            # Увеличенные шрифты для номеров пар и времени
            self.pair_number_font = ImageFont.truetype("arialbd.ttf", 16)  # Увеличен с ~10 до 16
            self.time_font = ImageFont.truetype("arial.ttf", 12)  # Увеличен с ~8 до 12
        except:
            self.title_font = ImageFont.load_default()
            self.header_font = ImageFont.load_default()
            self.subheader_font = ImageFont.load_default()
            self.text_font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
            self.bold_font = ImageFont.load_default()
            self.bob_font = ImageFont.load_default()
            # Запасные варианты для увеличенных шрифтов
            self.pair_number_font = ImageFont.load_default()
            self.time_font = ImageFont.load_default()

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

        # Создаем изображение с разрешением 1280x720
        width = 1280
        height = 720
        margin = 15
        day_column_height = 93  # Высота колонки дня
        pair_column_width = 149  # Ширина колонки пары
        time_row_height = 50  # Увеличена высота строки с временем с 40 до 50

        # УЗКАЯ КОЛОНКА ДЛЯ ДНЕЙ НЕДЕЛИ
        day_column_width = 60  # Уменьшили ширину колонки дней

        img = Image.new('RGB', (width, height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)

        y_position = margin

        # Заголовок
        title = f"Расписание группы: {group_name}"
        draw.text((width // 2, y_position), title, fill='white', font=self.title_font, anchor="mm")
        y_position += 35

        week_info = f"Неделя: {week_number}"
        draw.text((width // 2, y_position), week_info, fill='#cccccc', font=self.subheader_font, anchor="mm")
        y_position += 40

        # Времена пар (теперь по горизонтали)
        time_slots = {
            1: "8:30-9:50", 2: "10:00-11:20", 3: "11:30-12:50",
            4: "13:30-14:50", 5: "15:00-16:20", 6: "16:30-17:50",
            7: "18:00-19:20", 8: "19:30-20:50"
        }

        # Дни недели (теперь по вертикали слева)
        days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]

        # Заголовок дней
        day_header_y = y_position
        draw.rectangle([margin, day_header_y, margin + day_column_width, day_header_y + time_row_height],
                       fill='#2d2d2d')
        draw.text((margin + day_column_width // 2, day_header_y + time_row_height // 2), "День",
                  fill='white', font=self.bob_font, anchor="mm")

        # Заголовки пар (номера и время) - УВЕЛИЧЕНЫ И ЦЕНТРИРОВАНЫ
        for pair_num in range(1, 9):
            pair_x = margin + day_column_width + (pair_num - 1) * pair_column_width

            # Заголовок пары
            draw.rectangle([pair_x, day_header_y, pair_x + pair_column_width, day_header_y + time_row_height],
                           fill='#2d2d2d')

            # Центр колонки по горизонтали и вертикали
            center_x = pair_x + pair_column_width // 2
            center_y = day_header_y + time_row_height // 2

            # Номер пары - УВЕЛИЧЕН, ВЫДЕЛЕН И СМЕЩЕН ВНИЗ
            number_y = center_y - 8  # Смещаем номер пары вверх от центра
            draw.text((center_x, number_y), str(pair_num),
                      fill='white', font=self.pair_number_font, anchor="mm")

            # Время пары - УВЕЛИЧЕНО И СМЕЩЕНО ВНИЗ
            time_y = center_y + 12  # Смещаем время вниз от центра
            draw.text((center_x, time_y), time_slots[pair_num],
                      fill='#cccccc', font=self.time_font, anchor="mm")

        y_position += time_row_height

        # Сетка расписания (дни по вертикали, пары по горизонтали)
        for day_idx, day_name in enumerate(days):
            day_y = y_position + day_idx * day_column_height

            # Ячейка дня (УЗКАЯ)
            draw.rectangle([margin, day_y, margin + day_column_width, day_y + day_column_height],
                           fill='#2d2d2d')

            # Название дня (вертикально) - используем сокращенные названия
            short_day = day_name  # Уже короткие: ПН, ВТ, СР и т.д.
            draw.text((margin + day_column_width // 2, day_y + day_column_height // 2), short_day,
                      fill='white', font=self.bob_font, anchor="mm")

            # Ячейки для пар в этот день
            for pair_num in range(1, 9):
                pair_x = margin + day_column_width + (pair_num - 1) * pair_column_width

                # Ищем занятие
                lesson = None
                short_day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][day_idx]
                if short_day_name in days_schedule:
                    for les in days_schedule[short_day_name]:
                        if les['pair'] == pair_num:
                            lesson = les
                            break

                # Рисуем ячейку
                cell_color = '#1a1a1a' if not lesson else '#2d2d2d'
                draw.rectangle([pair_x, day_y, pair_x + pair_column_width, day_y + day_column_height],
                               fill=cell_color, outline='#444444')

                if lesson:
                    # Форматируем текст
                    subject = self._wrap_text(lesson['subject'], 25)
                    lesson_type = self._truncate_text(lesson['type'], 20)
                    teacher = self._truncate_text(lesson['teacher'], 22)
                    classroom = self._truncate_text(lesson['classroom'], 20)

                    # Рисуем текст
                    text_y = day_y + 5

                    # Предмет (может быть в несколько строк)
                    subject_lines = subject.split('\n')
                    for line in subject_lines[:2]:  # Максимум 2 строки
                        draw.text((pair_x + 5, text_y), line, fill='white', font=self.small_font)
                        text_y += 10

                    text_y += 2
                    draw.text((pair_x + 5, text_y), lesson_type, fill='#ff6b6b', font=self.small_font)
                    text_y += 10
                    draw.text((pair_x + 5, text_y), teacher, fill='#4ecdc4', font=self.small_font)
                    text_y += 10
                    draw.text((pair_x + 5, text_y), classroom, fill='#ffe66d', font=self.small_font)

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

    def create_teacher_schedule_image(self, teacher_name, week_number, schedules):
        """Создает изображение с расписанием преподавателя"""
        if not schedules:
            return self._create_error_image("Расписание не найдено")

        # Группируем по дням
        days_schedule = {}
        for item in schedules:
            day = item['day']
            if day not in days_schedule:
                days_schedule[day] = []
            days_schedule[day].append(item)

        # Создаем изображение с разрешением 1280x720
        width = 1280
        height = 720
        margin = 15
        day_column_height = 93  # Высота колонки дня
        pair_column_width = 149  # Ширина колонки пары
        time_row_height = 50  # Высота строки с временем

        # Узкая колонка для дней недели
        day_column_width = 60

        img = Image.new('RGB', (width, height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)

        y_position = margin

        # Заголовок
        title = f"Расписание преподавателя: {teacher_name}"
        draw.text((width // 2, y_position), title, fill='white', font=self.title_font, anchor="mm")
        y_position += 35

        week_info = f"Неделя: {week_number}"
        draw.text((width // 2, y_position), week_info, fill='#cccccc', font=self.subheader_font, anchor="mm")
        y_position += 40

        # Времена пар
        time_slots = {
            1: "8:30-9:50", 2: "10:00-11:20", 3: "11:30-12:50",
            4: "13:30-14:50", 5: "15:00-16:20", 6: "16:30-17:50",
            7: "18:00-19:20", 8: "19:30-20:50"
        }

        # Дни недели
        days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]

        # Заголовок дней
        day_header_y = y_position
        draw.rectangle([margin, day_header_y, margin + day_column_width, day_header_y + time_row_height],
                       fill='#2d2d2d')
        draw.text((margin + day_column_width // 2, day_header_y + time_row_height // 2), "День",
                  fill='white', font=self.bob_font, anchor="mm")

        # Заголовки пар (номера и время)
        for pair_num in range(1, 9):
            pair_x = margin + day_column_width + (pair_num - 1) * pair_column_width

            # Заголовок пары
            draw.rectangle([pair_x, day_header_y, pair_x + pair_column_width, day_header_y + time_row_height],
                           fill='#2d2d2d')

            # Центр колонки по горизонтали и вертикали
            center_x = pair_x + pair_column_width // 2
            center_y = day_header_y + time_row_height // 2

            # Номер пары
            number_y = center_y - 8
            draw.text((center_x, number_y), str(pair_num),
                      fill='white', font=self.pair_number_font, anchor="mm")

            # Время пары
            time_y = center_y + 12
            draw.text((center_x, time_y), time_slots[pair_num],
                      fill='#cccccc', font=self.time_font, anchor="mm")

        y_position += time_row_height

        # Сетка расписания
        for day_idx, day_name in enumerate(days):
            day_y = y_position + day_idx * day_column_height

            # Ячейка дня
            draw.rectangle([margin, day_y, margin + day_column_width, day_y + day_column_height],
                           fill='#2d2d2d')
            draw.text((margin + day_column_width // 2, day_y + day_column_height // 2), day_name,
                      fill='white', font=self.bob_font, anchor="mm")

            # Ячейки для пар в этот день
            for pair_num in range(1, 9):
                pair_x = margin + day_column_width + (pair_num - 1) * pair_column_width

                # Ищем занятие
                lesson = None
                short_day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][day_idx]
                if short_day_name in days_schedule:
                    for les in days_schedule[short_day_name]:
                        if les['pair'] == pair_num:
                            lesson = les
                            break

                # Рисуем ячейку
                cell_color = '#1a1a1a' if not lesson else '#2d2d2d'
                draw.rectangle([pair_x, day_y, pair_x + pair_column_width, day_y + day_column_height],
                               fill=cell_color, outline='#444444')

                if lesson:
                    # Форматируем текст для преподавателя
                    subject = self._wrap_text(lesson['subject'], 25)
                    lesson_type = self._truncate_text(lesson['type'], 20)
                    group = self._truncate_text(lesson['group'], 22)  # Вместо teacher теперь group
                    classroom = self._truncate_text(lesson['classroom'], 20)

                    # Рисуем текст
                    text_y = day_y + 5

                    # Предмет (может быть в несколько строк)
                    subject_lines = subject.split('\n')
                    for line in subject_lines[:2]:  # Максимум 2 строки
                        draw.text((pair_x + 5, text_y), line, fill='white', font=self.small_font)
                        text_y += 10

                    text_y += 2
                    draw.text((pair_x + 5, text_y), lesson_type, fill='#ff6b6b', font=self.small_font)
                    text_y += 10
                    draw.text((pair_x + 5, text_y), group, fill='#4ecdc4',
                              font=self.small_font)  # Группа вместо преподавателя
                    text_y += 10
                    draw.text((pair_x + 5, text_y), classroom, fill='#ffe66d', font=self.small_font)

        return img