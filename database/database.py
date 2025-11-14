import sqlite3
import logging
import os
from typing import Optional, Tuple


class UserDatabase:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.check_and_update_schema()  # Сначала проверяем схему
        self.init_database()  # Затем инициализируем

    def init_database(self):
        """Инициализация базы данных и создание таблицы"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # УБИРАЕМ УДАЛЕНИЕ ТАБЛИЦЫ - сохраняем данные между перезапусками
                # cursor.execute('DROP TABLE IF EXISTS users')

                # Создаем таблицу только если она не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        role TEXT NOT NULL DEFAULT 'student',
                        group_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Проверяем структуру таблицы
                cursor.execute("PRAGMA table_info(users)")
                columns = cursor.fetchall()
                logging.info(f"📊 Структура таблицы users: {columns}")

                conn.commit()
                logging.info("✅ База данных инициализирована успешно")

        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
            # Пытаемся создать заново при ошибке
            self.force_recreate_database()

    def force_recreate_database(self):
        """Принудительно пересоздает базу данных только при критических ошибках"""
        try:
            # Проверяем, существует ли таблица и имеет ли правильную структуру
            if not self.check_database_health():
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                    logging.info("🗑️ Старая база данных удалена из-за ошибок")

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        CREATE TABLE users (
                            user_id INTEGER PRIMARY KEY,
                            role TEXT NOT NULL DEFAULT 'student',
                            group_name TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    conn.commit()
                    logging.info("✅ База данных пересоздана успешно")
            else:
                logging.info("✅ База данных в норме, пересоздание не требуется")
        except Exception as e:
            logging.error(f"❌ Критическая ошибка при создании БД: {e}")

    def add_or_update_user(self, user_id: int, role: str, group_name: Optional[str] = None):
        """Добавляет или обновляет пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Проверяем существование пользователя
                cursor.execute('SELECT user_id, role, group_name FROM users WHERE user_id = ?', (user_id,))
                existing_user = cursor.fetchone()

                if existing_user:
                    # Обновляем существующего пользователя
                    cursor.execute('''
                        UPDATE users 
                        SET role = ?, group_name = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (role, group_name, user_id))
                    logging.info(f"✅ Пользователь {user_id} обновлен: роль={role}, группа={group_name}")
                else:
                    # Добавляем нового пользователя
                    cursor.execute('''
                        INSERT INTO users (user_id, role, group_name)
                        VALUES (?, ?, ?)
                    ''', (user_id, role, group_name))
                    logging.info(f"✅ Пользователь {user_id} добавлен: роль={role}, группа={group_name}")

                conn.commit()
                return True

        except Exception as e:
            logging.error(f"❌ Ошибка добавления/обновления пользователя {user_id}: {e}")
            # Пытаемся восстановить базу данных при ошибке
            self.force_recreate_database()
            return False

    def check_and_update_schema(self):
        """Проверяет и обновляет схему базы данных при необходимости"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Проверяем существующие колонки
                cursor.execute("PRAGMA table_info(users)")
                existing_columns = {column[1] for column in cursor.fetchall()}

                required_columns = {'user_id', 'role', 'group_name', 'created_at', 'updated_at'}

                # Если есть отсутствующие колонки, пересоздаем таблицу
                if not required_columns.issubset(existing_columns):
                    logging.warning("🔄 Обнаружены изменения в схеме, пересоздаем таблицу...")
                    self.force_recreate_database()

        except Exception as e:
            logging.error(f"❌ Ошибка проверки схемы: {e}")

    def get_user(self, user_id: int) -> Optional[Tuple]:
        """Получает информацию о пользователе"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, role, group_name 
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                return result
        except Exception as e:
            logging.error(f"❌ Ошибка получения пользователя {user_id}: {e}")
            # Пытаемся восстановить базу данных при ошибке
            self.force_recreate_database()
            return None

    def update_user_role(self, user_id: int, role: str):
        """Обновляет роль пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET role = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (role, user_id))
                conn.commit()
                logging.info(f"✅ Роль пользователя {user_id} обновлена: {role}")
                return True
        except Exception as e:
            logging.error(f"❌ Ошибка обновления роли пользователя {user_id}: {e}")
            return False

    def update_user_group(self, user_id: int, group_name: str):
        """Обновляет группу пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET group_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (group_name, user_id))
                conn.commit()
                logging.info(f"✅ Группа пользователя {user_id} обновлена: {group_name}")
                return True
        except Exception as e:
            logging.error(f"❌ Ошибка обновления группы пользователя {user_id}: {e}")
            return False

    def delete_user(self, user_id: int):
        """Удаляет пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()
                logging.info(f"✅ Пользователь {user_id} удален")
                return True
        except Exception as e:
            logging.error(f"❌ Ошибка удаления пользователя {user_id}: {e}")
            return False

    def get_all_users(self):
        """Получает всех пользователей (для админки)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, role, group_name FROM users ORDER BY created_at DESC')
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"❌ Ошибка получения всех пользователей: {e}")
            return []

    def check_database_health(self):
        """Проверяет здоровье базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                table_exists = cursor.fetchone()

                if table_exists:
                    cursor.execute("PRAGMA table_info(users)")
                    columns = cursor.fetchall()
                    logging.info(f"🔍 Проверка БД: таблица существует, колонки: {columns}")
                    return True
                else:
                    logging.error("❌ Таблица 'users' не существует")
                    return False
        except Exception as e:
            logging.error(f"❌ Ошибка проверки здоровья БД: {e}")
            return False


# Создаем глобальный экземпляр базы данных
user_db = UserDatabase()

# Проверяем здоровье БД при импорте
user_db.check_database_health()
