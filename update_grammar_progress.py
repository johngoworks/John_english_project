"""
Скрипт для добавления поля is_read в таблицу user_grammar_progress
"""

import sqlite3

def main():
    # Подключение к БД
    conn = sqlite3.connect('english_learning.db')
    cursor = conn.cursor()

    try:
        # Проверяем, есть ли уже поле is_read
        cursor.execute("PRAGMA table_info(user_grammar_progress)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'is_read' not in columns:
            print("Добавляю поле is_read в таблицу user_grammar_progress...")
            cursor.execute("""
                ALTER TABLE user_grammar_progress
                ADD COLUMN is_read BOOLEAN DEFAULT 0
            """)
            conn.commit()
            print("✓ Поле is_read успешно добавлено!")
        else:
            print("✓ Поле is_read уже существует в таблице")

    except Exception as e:
        print(f"Ошибка при обновлении базы данных: {e}")
        conn.rollback()
    finally:
        conn.close()

    print("\n✓ База данных обновлена!")

if __name__ == "__main__":
    main()
