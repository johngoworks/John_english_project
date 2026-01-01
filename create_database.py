"""
Database initialization script
Creates SQLite database and populates it with data from JSON files
"""
import json
import sqlite3
from pathlib import Path


def create_database():
    """Create database and tables"""
    db_path = "english_learning.db"

    # Remove existing database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"Removed existing database: {db_path}")

    # Create connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create grammar table
    cursor.execute("""
    CREATE TABLE grammar (
        id TEXT PRIMARY KEY,
        super_category TEXT,
        sub_category TEXT,
        level TEXT NOT NULL,
        lexical_range TEXT,
        guideword TEXT,
        can_do_statement TEXT,
        example TEXT
    )
    """)
    print("Created grammar table")

    # Create dictionary table
    cursor.execute("""
    CREATE TABLE dictionary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        class TEXT,
        level TEXT NOT NULL
    )
    """)
    print("Created dictionary table")

    # Create indexes
    cursor.execute("CREATE INDEX idx_grammar_level ON grammar(level)")
    cursor.execute("CREATE INDEX idx_grammar_category ON grammar(super_category)")
    cursor.execute("CREATE INDEX idx_dictionary_level ON dictionary(level)")
    cursor.execute("CREATE INDEX idx_dictionary_word ON dictionary(word)")
    cursor.execute("CREATE INDEX idx_dictionary_class ON dictionary(class)")
    print("Created indexes")

    conn.commit()
    return conn


def load_grammar_data(conn):
    """Load grammar data from JSON"""
    json_path = "json_to_backup/grammar.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()
    inserted = 0

    for item in data:
        try:
            cursor.execute("""
            INSERT INTO grammar (
                id, super_category, sub_category, level,
                lexical_range, guideword, can_do_statement, example
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get('id'),
                item.get('SuperCategory'),
                item.get('SubCategory'),
                item.get('Level'),
                item.get('LexicalRange'),
                item.get('Guideword'),
                item.get('Can-do statement'),
                item.get('Example')
            ))
            inserted += 1
        except Exception as e:
            print(f"Error inserting grammar item {item.get('id')}: {e}")

    conn.commit()
    print(f"Inserted {inserted} grammar rules")


def load_dictionary_data(conn):
    """Load dictionary data from JSON"""
    json_path = "json_to_backup/dictionary.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()
    inserted = 0

    for item in data:
        try:
            cursor.execute("""
            INSERT INTO dictionary (word, class, level)
            VALUES (?, ?, ?)
            """, (
                item.get('word'),
                item.get('class'),
                item.get('level')
            ))
            inserted += 1
        except Exception as e:
            print(f"Error inserting word {item.get('word')}: {e}")

    conn.commit()
    print(f"Inserted {inserted} words")


def verify_database(conn):
    """Verify database contents"""
    cursor = conn.cursor()

    # Count grammar rules
    cursor.execute("SELECT COUNT(*) FROM grammar")
    grammar_count = cursor.fetchone()[0]
    print(f"\nVerification:")
    print(f"  Grammar rules: {grammar_count}")

    # Count by level
    cursor.execute("SELECT level, COUNT(*) FROM grammar GROUP BY level ORDER BY level")
    print("  Grammar by level:")
    for level, count in cursor.fetchall():
        print(f"    {level}: {count}")

    # Count words
    cursor.execute("SELECT COUNT(*) FROM dictionary")
    words_count = cursor.fetchone()[0]
    print(f"\n  Words: {words_count}")

    # Count by level
    cursor.execute("SELECT level, COUNT(*) FROM dictionary GROUP BY level ORDER BY level")
    print("  Words by level:")
    for level, count in cursor.fetchall():
        print(f"    {level}: {count}")


def main():
    """Main execution"""
    print("English Learning Database Initialization")
    print("=" * 50)

    # Create database and tables
    conn = create_database()

    # Load data
    print("\nLoading data from JSON files...")
    load_grammar_data(conn)
    load_dictionary_data(conn)

    # Verify
    verify_database(conn)

    # Close connection
    conn.close()

    print("\n" + "=" * 50)
    print("[OK] Database created successfully!")
    print(f"Database file: english_learning.db")


if __name__ == "__main__":
    main()
