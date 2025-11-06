from PIL import Image, ImageDraw, ImageFont
import io
import logging

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