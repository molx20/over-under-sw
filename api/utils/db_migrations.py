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


def _get_connection_nba_data():
    """Get database connection to nba_data.db"""
    try:
        from api.utils.db_config import get_db_path
    except ImportError:
        from db_config import get_db_path

    class NBADataConnection:
        def __enter__(self):
            self.conn = sqlite3.connect(get_db_path('nba_data.db'), timeout=30.0)
            self.conn.row_factory = sqlite3.Row
            return self.conn
        def __exit__(self, *args):
            if self.conn:
                self.conn.close()
    return NBADataConnection()


def migrate_to_v10_enhance_sync_log():
    """
    Migrate data_sync_log table to include enhanced tracking fields

    Adds:
    - run_id: UUID for tracking async jobs
    - target_date_mt: The MT date being synced
    - cdn_games_found: How many games NBA CDN returned
    - inserted_count: New games added
    - updated_count: Existing games updated
    - skipped_count: Games skipped (wrong season, etc)
    - retry_attempt: Retry counter for failed syncs
    - nba_cdn_url: URL used to fetch games
    - game_ids_sample: JSON array of first 5 gameIds for diagnostics

    Safe to run multiple times - will skip existing columns
    """
    print('[db_migrations] Running NBA data migration v10 (enhance_sync_log)...')

    with _get_connection_nba_data() as conn:
        cursor = conn.cursor()

        # Add new columns for enhanced tracking
        new_columns = [
            ('run_id', 'TEXT'),
            ('target_date_mt', 'TEXT'),
            ('cdn_games_found', 'INTEGER', 0),
            ('inserted_count', 'INTEGER', 0),
            ('updated_count', 'INTEGER', 0),
            ('skipped_count', 'INTEGER', 0),
            ('retry_attempt', 'INTEGER', 0),
            ('nba_cdn_url', 'TEXT'),
            ('game_ids_sample', 'TEXT')  # JSON array
        ]

        for col_info in new_columns:
            col_name = col_info[0]
            col_type = col_info[1]
            default_val = col_info[2] if len(col_info) > 2 else None

            try:
                if default_val is not None:
                    cursor.execute(f'ALTER TABLE data_sync_log ADD COLUMN {col_name} {col_type} DEFAULT {default_val}')
                else:
                    cursor.execute(f'ALTER TABLE data_sync_log ADD COLUMN {col_name} {col_type}')
                print(f'[db_migrations] Added column: {col_name}')
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f'[db_migrations] Column {col_name} already exists, skipping')
                else:
                    raise

        # Add indexes for efficient queries
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_log_run_id
                ON data_sync_log(run_id)
            """)
            print('[db_migrations] Created index: idx_sync_log_run_id')
        except sqlite3.OperationalError:
            print('[db_migrations] Index idx_sync_log_run_id already exists')

        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_log_target_date
                ON data_sync_log(target_date_mt DESC, started_at DESC)
            """)
            print('[db_migrations] Created index: idx_sync_log_target_date')
        except sqlite3.OperationalError:
            print('[db_migrations] Index idx_sync_log_target_date already exists')

        conn.commit()

    print('[db_migrations] Migration v10 completed successfully')
    print('[db_migrations] data_sync_log table now has enhanced tracking capabilities')


def migrate_to_v11_ai_game_writeups():
    """
    Migrate nba_data.db to support AI-generated game writeups

    Adds:
    - ai_game_writeups table for storing AI-generated game analysis
    - game_id (PRIMARY KEY): Unique game identifier
    - writeup_text: Full AI-generated writeup (3 sections)
    - data_hash: MD5 hash of source data for cache invalidation
    - engine_version: AI prompt version for regeneration tracking
    - created_at/updated_at: Timestamps

    Safe to run multiple times - will skip if table exists
    """
    print('[db_migrations] Running NBA data migration v11 (ai_game_writeups)...')

    with _get_connection_nba_data() as conn:
        cursor = conn.cursor()

        # Create ai_game_writeups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_game_writeups (
                game_id TEXT PRIMARY KEY,
                writeup_text TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                engine_version TEXT NOT NULL DEFAULT 'v1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print('[db_migrations] ai_game_writeups table created')

        # Create index on game_id for fast lookups
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_writeups_game_id
                ON ai_game_writeups(game_id)
            """)
            print('[db_migrations] Created index: idx_ai_writeups_game_id')
        except sqlite3.OperationalError:
            print('[db_migrations] Index idx_ai_writeups_game_id already exists')

        # Create index on data_hash for cache validation
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_writeups_hash
                ON ai_game_writeups(data_hash)
            """)
            print('[db_migrations] Created index: idx_ai_writeups_hash')
        except sqlite3.OperationalError:
            print('[db_migrations] Index idx_ai_writeups_hash already exists')

        conn.commit()

    print('[db_migrations] Migration v11 completed successfully')
    print('[db_migrations] AI game writeups table ready for use')


if __name__ == '__main__':
    # Run migration when executed directly
    print('=== Database Migration Tool ===')
    print(f'Predictions DB: {DB_PATH}')
    print()

    print('Current status:')
    status = check_migration_status()
    for feature, enabled in status.items():
        print(f'  {feature}: {"✓" if enabled else "✗"}')
    print()

    if all(status.values()):
        print('All predictions.db migrations already applied.')
    else:
        print('Running predictions.db migrations...')
        migrate_to_v3_features()
        migrate_to_v4_opponent_ranks()
        print()
        print('New status:')
        status = check_migration_status()
        for feature, enabled in status.items():
            print(f'  {feature}: {"✓" if enabled else "✗"}')

    print()
    print('Running nba_data.db migrations...')
    migrate_to_v10_enhance_sync_log()
    migrate_to_v11_ai_game_writeups()
    print()
    print('All migrations complete!')
