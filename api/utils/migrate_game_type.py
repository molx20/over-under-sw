"""
Database Migration: Add game_type Column

Adds a 'game_type' column to todays_games and team_game_logs tables
to support filtering of non-regular-season games.

This migration is:
- Idempotent (safe to run multiple times)
- Non-destructive (doesn't delete any data)
- Backward compatible (column is nullable)
"""
import sqlite3
import os
import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from api.utils.game_classifier import classify_game, get_game_type_label

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_path():
    """Get path to nba_data.db"""
    return os.path.join(os.path.dirname(__file__), '../data/nba_data.db')


def migrate_add_game_type():
    """
    Add game_type column to todays_games and team_game_logs tables.

    Column will store: 'Regular Season', 'NBA Cup', 'Preseason', 'Playoffs',
    'Summer League', 'All-Star', 'Unknown'
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check if column already exists in todays_games
        cursor.execute("PRAGMA table_info(todays_games)")
        columns = [row['name'] for row in cursor.fetchall()]

        if 'game_type' not in columns:
            logger.info("Adding game_type column to todays_games...")
            cursor.execute('''
                ALTER TABLE todays_games
                ADD COLUMN game_type TEXT DEFAULT NULL
            ''')
            logger.info("✓ Added game_type to todays_games")
        else:
            logger.info("✓ game_type column already exists in todays_games")

        # Check if column already exists in team_game_logs
        cursor.execute("PRAGMA table_info(team_game_logs)")
        columns = [row['name'] for row in cursor.fetchall()]

        if 'game_type' not in columns:
            logger.info("Adding game_type column to team_game_logs...")
            cursor.execute('''
                ALTER TABLE team_game_logs
                ADD COLUMN game_type TEXT DEFAULT NULL
            ''')
            logger.info("✓ Added game_type to team_game_logs")
        else:
            logger.info("✓ game_type column already exists in team_game_logs")

        conn.commit()
        logger.info("Migration completed successfully")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def backfill_game_types():
    """
    Backfill game_type values for existing records.

    This uses the game_classifier to determine game types based on game_id.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Backfill todays_games
        logger.info("Backfilling game_type for todays_games...")
        cursor.execute("SELECT game_id, game_date FROM todays_games WHERE game_type IS NULL")
        rows = cursor.fetchall()

        backfilled = 0
        for row in rows:
            game_type_label = get_game_type_label(row['game_id'], row['game_date'])
            cursor.execute('''
                UPDATE todays_games
                SET game_type = ?
                WHERE game_id = ?
            ''', (game_type_label, row['game_id']))
            backfilled += 1

        logger.info(f"✓ Backfilled {backfilled} records in todays_games")

        # Backfill team_game_logs
        logger.info("Backfilling game_type for team_game_logs...")
        cursor.execute("SELECT DISTINCT game_id, game_date FROM team_game_logs WHERE game_type IS NULL")
        rows = cursor.fetchall()

        backfilled = 0
        for row in rows:
            game_type_label = get_game_type_label(row['game_id'], row['game_date'])
            cursor.execute('''
                UPDATE team_game_logs
                SET game_type = ?
                WHERE game_id = ?
            ''', (game_type_label, row['game_id']))
            backfilled += 1

        logger.info(f"✓ Backfilled {backfilled} unique games in team_game_logs")

        conn.commit()
        logger.info("Backfill completed successfully")

        # Show stats
        cursor.execute('''
            SELECT game_type, COUNT(*) as count
            FROM todays_games
            GROUP BY game_type
        ''')
        logger.info("\ntodays_games breakdown:")
        for row in cursor.fetchall():
            logger.info(f"  {row['game_type']}: {row['count']}")

        cursor.execute('''
            SELECT game_type, COUNT(*) as count
            FROM team_game_logs
            GROUP BY game_type
        ''')
        logger.info("\nteam_game_logs breakdown:")
        for row in cursor.fetchall():
            logger.info(f"  {row['game_type']}: {row['count']}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Backfill failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Database Migration: Add game_type Column")
    logger.info("=" * 60)

    migrate_add_game_type()
    backfill_game_types()

    logger.info("\n" + "=" * 60)
    logger.info("Migration Complete!")
    logger.info("=" * 60)
