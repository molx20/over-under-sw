"""
Migration script to create the games table for storing game-level data.

This table stores one record per game (not per team) with final scores and game pace.
The team_game_logs table continues to store per-team stats for each game.
"""

import sqlite3
import os

DB_PATH = 'api/data/nba_data.db'

def migrate():
    """Create the games table."""

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("=" * 70)
        print("GAMES TABLE MIGRATION")
        print("=" * 70)

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='games'
        """)

        if cursor.fetchone():
            print("\n⏭️  Table 'games' already exists, skipping creation")
            conn.close()
            return True

        # Create games table
        print("\n➕ Creating 'games' table...")
        cursor.execute('''
            CREATE TABLE games (
                id TEXT PRIMARY KEY,
                season TEXT NOT NULL,
                game_date TEXT NOT NULL,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                total_points INTEGER,
                game_pace REAL,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (home_team_id) REFERENCES nba_teams(team_id),
                FOREIGN KEY (away_team_id) REFERENCES nba_teams(team_id)
            )
        ''')

        # Create indexes for common queries
        print("➕ Creating indexes...")
        cursor.execute('''
            CREATE INDEX idx_games_date ON games(game_date)
        ''')
        cursor.execute('''
            CREATE INDEX idx_games_season ON games(season)
        ''')
        cursor.execute('''
            CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id)
        ''')

        conn.commit()

        print("\n" + "=" * 70)
        print("✅ Migration complete!")
        print("   Table created: games")
        print("   Indexes created: 3")
        print("=" * 70)

        # Show schema
        cursor.execute("PRAGMA table_info(games)")
        columns = cursor.fetchall()

        print("\n📋 Games table schema:")
        print("   Column Name              Type       Not Null  Default")
        print("   " + "-" * 60)
        for col in columns:
            print(f"   {col[1]:24} {col[2]:10} {col[3]:9} {col[4] if col[4] else ''}")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
