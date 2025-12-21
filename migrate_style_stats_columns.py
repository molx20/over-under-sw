"""
Migration Script: Add style stats columns to game_reviews table

Adds two new TEXT columns:
- expected_style_stats_json
- actual_style_stats_json

These columns will store per-team detailed statistics for AI Model Coach analysis.
"""

import sqlite3
from api.utils.db_config import get_db_path

GAME_REVIEWS_DB_PATH = get_db_path('game_reviews.db')

def migrate_style_stats_columns():
    """Add style stats columns to game_reviews table"""
    conn = sqlite3.connect(GAME_REVIEWS_DB_PATH)
    cursor = conn.cursor()

    print(f"[Migration] Connected to: {GAME_REVIEWS_DB_PATH}")

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(game_reviews)")
    columns = [row[1] for row in cursor.fetchall()]

    print(f"[Migration] Existing columns: {len(columns)}")

    # Add expected_style_stats_json if it doesn't exist
    if 'expected_style_stats_json' not in columns:
        print("[Migration] Adding column: expected_style_stats_json")
        cursor.execute('''
            ALTER TABLE game_reviews
            ADD COLUMN expected_style_stats_json TEXT
        ''')
        print("[Migration] ✓ expected_style_stats_json added")
    else:
        print("[Migration] ⊘ expected_style_stats_json already exists")

    # Add actual_style_stats_json if it doesn't exist
    if 'actual_style_stats_json' not in columns:
        print("[Migration] Adding column: actual_style_stats_json")
        cursor.execute('''
            ALTER TABLE game_reviews
            ADD COLUMN actual_style_stats_json TEXT
        ''')
        print("[Migration] ✓ actual_style_stats_json added")
    else:
        print("[Migration] ⊘ actual_style_stats_json already exists")

    conn.commit()
    conn.close()

    print("[Migration] ✅ Migration complete!")

if __name__ == '__main__':
    migrate_style_stats_columns()
