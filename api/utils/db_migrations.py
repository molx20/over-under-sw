"""
Database Migration Helpers

Manages schema migrations for feature enhancements.
Safe to run multiple times (idempotent).
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions.db')


def migrate_to_v3_features():
    """
    Migrate database to support feature-enhanced predictions

    Adds:
    - New columns to game_predictions for feature storage
    - team_game_history table for recent form tracking
    - matchup_profile_cache table for opponent bucket performance

    Safe to run multiple times - will skip existing columns/tables
    """
    print('[db_migrations] Running migration to v3 (feature-enhanced predictions)...')

    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

    print('[db_migrations] Migration to v3 completed successfully')
    print('[db_migrations] Database is ready for feature-enhanced predictions')


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
