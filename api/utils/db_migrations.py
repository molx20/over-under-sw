"""
Database Migration Helpers

Manages schema migrations for feature enhancements.
Safe to run multiple times (idempotent).

Uses migration version tracking to avoid redundant checks on every startup.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions.db')

# Import connection pool
try:
    from api.utils.connection_pool import get_db_pool
except ImportError:
    try:
        from connection_pool import get_db_pool
    except ImportError:
        # Fallback for standalone execution
        get_db_pool = None


def _get_connection():
    """Get database connection (pooled if available, direct otherwise)."""
    if get_db_pool:
        pool = get_db_pool('predictions')
        return pool.get_connection()
    else:
        # Fallback for standalone execution
        class DirectConnection:
            def __enter__(self):
                self.conn = sqlite3.connect(DB_PATH)
                self.conn.row_factory = sqlite3.Row
                return self.conn
            def __exit__(self, *args):
                self.conn.close()
        return DirectConnection()


def _ensure_migration_table():
    """Create migration tracking table if it doesn't exist."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        ''')
        conn.commit()


def _is_migration_applied(version: int) -> bool:
    """Check if a migration version has been applied."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT version FROM schema_migrations WHERE version = ?
        ''', (version,))
        return cursor.fetchone() is not None


def _mark_migration_applied(version: int, name: str):
    """Mark a migration as applied."""
    from datetime import datetime
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (?, ?, ?)
        ''', (version, name, datetime.utcnow().isoformat()))
        conn.commit()


def migrate_to_v3_features():
    """
    Migrate database to support feature-enhanced predictions

    Adds:
    - New columns to game_predictions for feature storage
    - team_game_history table for recent form tracking
    - matchup_profile_cache table for opponent bucket performance

    Safe to run multiple times - will skip existing columns/tables
    """
    version = 3
    name = 'feature_enhanced_predictions'

    # Check if already applied
    if _is_migration_applied(version):
        print(f'[db_migrations] Migration v{version} ({name}) already applied, skipping')
        return

    print(f'[db_migrations] Running migration v{version} ({name})...')

    with _get_connection() as conn:
        cursor = conn.cursor()

        # Part 1: Add columns to existing game_predictions table
        print('[db_migrations] Adding feature columns to game_predictions...')

        new_columns = [
            ('feature_vector', 'TEXT'),
            ('base_prediction', 'REAL'),
            ('feature_correction', 'REAL'),
            ('feature_metadata', 'TEXT')
        ]

        for col_name, col_type in new_columns:
            try:
                cursor.execute(f'ALTER TABLE game_predictions ADD COLUMN {col_name} {col_type}')
                print(f'[db_migrations] Added column: {col_name}')
            except sqlite3.OperationalError:
                print(f'[db_migrations] Column {col_name} already exists, skipping')

        # Part 2: Create team_game_history table
        print('[db_migrations] Creating team_game_history table...')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                team_tricode TEXT NOT NULL,
                opponent_id INTEGER NOT NULL,
                opponent_tricode TEXT,
                game_date TEXT NOT NULL,
                is_home INTEGER NOT NULL DEFAULT 1,

                -- Performance stats for this game
                points_scored REAL NOT NULL,
                points_allowed REAL NOT NULL,
                off_rtg REAL,
                def_rtg REAL,
                pace REAL,
                fg_pct REAL,
                three_pct REAL,

                -- Opponent strength classification at game time
                opp_off_bucket TEXT,  -- 'top', 'mid', 'bottom'
                opp_def_bucket TEXT,

                created_at TEXT NOT NULL
            )
        ''')

        # Create indexes for team_game_history
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_team_date
            ON team_game_history(team_id, game_date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_team_history
            ON team_game_history(team_tricode, game_date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_game_team
            ON team_game_history(game_id, team_tricode)
        ''')

        print('[db_migrations] team_game_history table ready')

        # Part 3: Create matchup_profile_cache table
        print('[db_migrations] Creating matchup_profile_cache table...')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matchup_profile_cache (
                team_tricode TEXT NOT NULL,
                vs_bucket_type TEXT NOT NULL,  -- 'vs_off_top', 'vs_off_mid', etc.
                games_count INTEGER DEFAULT 0,
                avg_total REAL,
                avg_points_scored REAL,
                avg_points_allowed REAL,
                last_updated TEXT,
                PRIMARY KEY (team_tricode, vs_bucket_type)
            )
        ''')

        print('[db_migrations] matchup_profile_cache table ready')

        conn.commit()

    # Mark migration as applied
    _mark_migration_applied(version, name)

    print(f'[db_migrations] Migration v{version} completed successfully')
    print('[db_migrations] Database is ready for feature-enhanced predictions')


def migrate_to_v4_opponent_ranks():
    """
    Migrate database to store opponent ranking data

    Adds opponent PPG, Pace, Off Rating, and Def Rating ranks to team_game_history
    so we can compute "last 5 opponents" features accurately.

    Safe to run multiple times - will skip existing columns
    """
    version = 4
    name = 'opponent_rankings'

    # Check if already applied
    if _is_migration_applied(version):
        print(f'[db_migrations] Migration v{version} ({name}) already applied, skipping')
        return

    print(f'[db_migrations] Running migration v{version} ({name})...')

    with _get_connection() as conn:
        cursor = conn.cursor()

        # Add opponent rank columns to team_game_history
        print('[db_migrations] Adding opponent rank columns to team_game_history...')

        rank_columns = [
            ('opp_ppg_rank', 'INTEGER'),          # Opponent's PPG rank (1-30)
            ('opp_pace_rank', 'INTEGER'),         # Opponent's Pace rank (1-30)
            ('opp_off_rtg_rank', 'INTEGER'),      # Opponent's Off Rating rank (1-30)
            ('opp_def_rtg_rank', 'INTEGER')       # Opponent's Def Rating rank (1-30)
        ]

        for col_name, col_type in rank_columns:
            try:
                cursor.execute(f'ALTER TABLE team_game_history ADD COLUMN {col_name} {col_type}')
                print(f'[db_migrations] Added column: {col_name}')
            except sqlite3.OperationalError:
                print(f'[db_migrations] Column {col_name} already exists, skipping')

        conn.commit()

    # Mark migration as applied
    _mark_migration_applied(version, name)

    print(f'[db_migrations] Migration v{version} completed successfully')
    print('[db_migrations] Database ready for opponent last-5 rank features')


def run_migrations():
    """
    Run all pending migrations.

    This is the main entry point called from init_db().
    Ensures migration tracking table exists and runs any pending migrations.
    """
    # Ensure migration tracking table exists
    _ensure_migration_table()

    # Run all migrations in order
    migrate_to_v3_features()
    migrate_to_v4_opponent_ranks()

    print('[db_migrations] All migrations completed')


def check_migration_status():
    """
    Check which migration features are present

    Returns:
        Dict with status of each migration component
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    status = {
        'game_predictions_enhanced': False,
        'team_game_history_exists': False,
        'matchup_profile_cache_exists': False
    }

    # Check for feature columns in game_predictions
    try:
        cursor.execute('SELECT feature_vector FROM game_predictions LIMIT 1')
        status['game_predictions_enhanced'] = True
    except sqlite3.OperationalError:
        pass

    # Check for team_game_history table
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='team_game_history'
    ''')
    if cursor.fetchone():
        status['team_game_history_exists'] = True

    # Check for matchup_profile_cache table
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='matchup_profile_cache'
    ''')
    if cursor.fetchone():
        status['matchup_profile_cache_exists'] = True

    conn.close()

    return status


if __name__ == '__main__':
    # Run migration when executed directly
    print('=== Database Migration Tool ===')
    print(f'Database: {DB_PATH}')
    print()

    print('Current status:')
    status = check_migration_status()
    for feature, enabled in status.items():
        print(f'  {feature}: {"✓" if enabled else "✗"}')
    print()

    if all(status.values()):
        print('All migrations already applied. Database is up to date.')
    else:
        print('Running migrations...')
        migrate_to_v3_features()
        print()
        print('New status:')
        status = check_migration_status()
        for feature, enabled in status.items():
            print(f'  {feature}: {"✓" if enabled else "✗"}')
