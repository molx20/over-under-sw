#!/usr/bin/env python3
"""
Database migration: Add matchup_summaries table for caching AI-generated game narratives.

This table stores structured matchup breakdown summaries to avoid re-generating
them with LLM calls for the same game.
"""

import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'api', 'data', 'nba_data.db')

def migrate():
    """Create the matchup_summaries table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating matchup_summaries table...")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matchup_summaries (
            game_id TEXT PRIMARY KEY,
            summary_json TEXT NOT NULL,
            engine_version TEXT NOT NULL DEFAULT 'v1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create index on engine_version for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_matchup_summaries_version
        ON matchup_summaries(engine_version)
    ''')

    conn.commit()

    # Verify table was created
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='matchup_summaries'
    ''')

    if cursor.fetchone():
        print("✅ matchup_summaries table created successfully")

        # Show table schema
        cursor.execute('PRAGMA table_info(matchup_summaries)')
        columns = cursor.fetchall()
        print("\nTable schema:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print("❌ Failed to create matchup_summaries table")

    conn.close()

if __name__ == '__main__':
    migrate()
