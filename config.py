# Конфигурационные параметры бота
BOT_TOKEN = 'f9LHodD0cOKVavHDtNLZIJ5CIfFt2IRgT0emk0pQ1AFxZMero5F4Rbt8GNNJmxxRWzIw8qW7CcJ2G55Jalx4'

# Базовые URL для разных частей расписания
SCHEDULE_PARTS = {
    1: {
        'name': 'Часть 1 - МФ, РТФ, ЭФ, ИФМИ',
        'url_template': 'https://lk.ulstu.ru/timetable/shared/schedule/Часть%201%20-%20МФ,%20РТФ,%20ЭФ%20(очная,%20очно-заочная%20формы%20обучения),%20ИФМИ,%20группы%20исскуственного%20интелекта%20(магистр)/{}.html',
        'min_group': 1,
        'max_group': 115
    },
    2: {
        'name': 'Часть 2 - ФИСТ, ФДП',
        'url_template': 'https://lk.ulstu.ru/timetable/shared/schedule/Часть%202%20–%20ФИСТ,%20ГФ/{}.html',
        'min_group': 116,
        'max_group': 234
    }
}
MIN_GROUP_NUMBER = 1
MAX_GROUP_NUMBER = 234

# Данные для авторизации на портале УлГТУ
ULSTU_USERNAME = "a.gajfullin"
ULSTU_PASSWORD = "zxcasdqwe123"

# Настройки логирования
LOG_LEVEL = "INFO"

# Настройки изображения
IMAGE_SETTINGS = {
    'width': 1400,
    'margin': 20,
    'cell_height': 90,
    'time_column_width': 120
}
SCHEDULE_BASE_URL = "https://lk.ulstu.ru/timetable/shared/schedule/Часть%202%20–%20ФИСТ,%20ГФ/61.html"