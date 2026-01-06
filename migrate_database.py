"""
Скрипт миграции базы данных
Добавляет недостающие поля в таблицы user_grammar_progress и user_tense_progress
"""

import sqlite3
import sys

def migrate_database():
    """Выполняет все необходимые миграции"""
    conn = sqlite3.connect('english_learning.db')
    cursor = conn.cursor()

    migrations_applied = 0

    try:
        # Миграция 1: Добавление is_read в user_grammar_progress
        cursor.execute("PRAGMA table_info(user_grammar_progress)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'is_read' not in columns:
            print("Применяю миграцию: добавление is_read в user_grammar_progress...")
            cursor.execute("""
                ALTER TABLE user_grammar_progress
                ADD COLUMN is_read BOOLEAN DEFAULT 0
            """)
            conn.commit()
            migrations_applied += 1
            print("✓ Миграция применена!")
        else:
            print("✓ is_read уже существует в user_grammar_progress")

        # Миграция 2: Добавление is_read в user_tense_progress
        cursor.execute("PRAGMA table_info(user_tense_progress)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'is_read' not in columns:
            print("Применяю миграцию: добавление is_read в user_tense_progress...")
            cursor.execute("""
                ALTER TABLE user_tense_progress
                ADD COLUMN is_read BOOLEAN DEFAULT 0
            """)
            conn.commit()
            migrations_applied += 1
            print("✓ Миграция применена!")
        else:
            print("✓ is_read уже существует в user_tense_progress")

        print(f"\n{'='*50}")
        if migrations_applied > 0:
            print(f"✓ Применено миграций: {migrations_applied}")
        else:
            print("✓ Все миграции уже применены, база данных актуальна!")
        print(f"{'='*50}\n")

    except Exception as e:
        print(f"\n✗ Ошибка при миграции: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("МИГРАЦИЯ БАЗЫ ДАННЫХ")
    print("="*50 + "\n")
    migrate_database()
