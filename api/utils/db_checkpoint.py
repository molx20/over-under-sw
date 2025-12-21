"""
Database Checkpoint Utility

This module ensures that SQLite WAL (Write-Ahead Log) files are properly
checkpointed (committed to the main database file) on server startup.

This prevents data loss when processes are killed with SIGKILL (-9).
"""

import sqlite3
import os
import logging

try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

logger = logging.getLogger(__name__)


def checkpoint_database(db_filename: str):
    """
    Checkpoint a SQLite database to commit all WAL data to the main file.

    Args:
        db_filename: Name of the database file (e.g., 'nba_data.db')
    """
    db_path = get_db_path(db_filename)

    if not os.path.exists(db_path):
        logger.warning(f"[DB Checkpoint] Database not found: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE);')
        conn.close()
        logger.info(f"[DB Checkpoint] Checkpointed {db_filename}")
    except Exception as e:
        logger.error(f"[DB Checkpoint] Error checkpointing {db_filename}: {e}")


def checkpoint_all_databases():
    """
    Checkpoint all known databases on server startup.

    This ensures data integrity after server restarts, especially when
    processes were killed with SIGKILL (-9).
    """
    databases = [
        'nba_data.db',
        'predictions.db',
        'team_rankings.db',
        'game_reviews.db'
    ]

    logger.info("[DB Checkpoint] Starting database checkpoint...")

    for db in databases:
        checkpoint_database(db)

    logger.info("[DB Checkpoint] All databases checkpointed")


if __name__ == '__main__':
    # For testing
    logging.basicConfig(level=logging.INFO)
    checkpoint_all_databases()
