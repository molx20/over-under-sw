"""
NBA Data Database Schema

This module defines the schema for the centralized NBA data store.
Stores all NBA stats, game logs, and sync metadata.

Tables:
- nba_teams: Static team reference data
- team_season_stats: Season averages with splits and rankings
- team_game_logs: Recent game logs (last N games)
- todays_games: Daily game schedule
- data_sync_log: Sync operation tracking
- league_averages: Fallback values for missing data

Usage:
    from api.utils.db_schema_nba_data import init_nba_data_db
    init_nba_data_db()
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

# Database file location
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


@contextmanager
def get_connection():
    """Get a connection to the NBA data database"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_nba_data_db():
    """
    Initialize the NBA data database schema.
    Creates all tables and indexes if they don't exist.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # ====================================================================
        # TEAMS TABLE (Static team data)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nba_teams (
                team_id INTEGER PRIMARY KEY,
                team_abbreviation TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                city TEXT,
                state TEXT,
                year_founded INTEGER,
                last_updated TEXT NOT NULL,
                season TEXT NOT NULL DEFAULT '2025-26'
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_teams_abbr
            ON nba_teams(team_abbreviation)
        ''')

        # ====================================================================
        # TEAM SEASON STATS (Season averages with splits and rankings)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_season_stats (
                team_id INTEGER NOT NULL,
                season TEXT NOT NULL,
                split_type TEXT NOT NULL,  -- 'overall', 'home', 'away'

                -- Traditional stats (per game)
                games_played INTEGER,
                wins INTEGER,
                losses INTEGER,
                ppg REAL,
                opp_ppg REAL,
                fg_pct REAL,
                fg3_pct REAL,
                ft_pct REAL,
                rebounds REAL,
                assists REAL,
                steals REAL,
                blocks REAL,
                turnovers REAL,

                -- Advanced stats
                off_rtg REAL,
                def_rtg REAL,
                net_rtg REAL,
                pace REAL,
                true_shooting_pct REAL,
                efg_pct REAL,

                -- Rankings (1 = best, computed at sync time)
                ppg_rank INTEGER,
                opp_ppg_rank INTEGER,
                fg_pct_rank INTEGER,
                fg3_pct_rank INTEGER,
                ft_pct_rank INTEGER,
                off_rtg_rank INTEGER,
                def_rtg_rank INTEGER,
                net_rtg_rank INTEGER,
                pace_rank INTEGER,

                -- Metadata
                synced_at TEXT NOT NULL,

                PRIMARY KEY (team_id, season, split_type),
                FOREIGN KEY (team_id) REFERENCES nba_teams(team_id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_team_season_stats
            ON team_season_stats(team_id, season)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_season_split
            ON team_season_stats(season, split_type)
        ''')

        # ====================================================================
        # TEAM GAME LOGS (Recent games)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_game_logs (
                game_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                game_date TEXT NOT NULL,
                season TEXT NOT NULL,

                -- Game context
                matchup TEXT,  -- "BOS vs. LAL" or "BOS @ LAL"
                is_home INTEGER NOT NULL,  -- 1 = home, 0 = away
                opponent_team_id INTEGER,
                opponent_abbr TEXT,

                -- Game stats
                team_pts INTEGER,
                opp_pts INTEGER,
                win_loss TEXT,  -- 'W' or 'L'

                -- Per-game advanced stats
                off_rating REAL,
                def_rating REAL,
                pace REAL,
                fg_pct REAL,
                fg3_pct REAL,
                ft_pct REAL,
                rebounds INTEGER,
                assists INTEGER,
                turnovers INTEGER,

                -- Metadata
                synced_at TEXT NOT NULL,

                PRIMARY KEY (game_id, team_id),
                FOREIGN KEY (team_id) REFERENCES nba_teams(team_id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_team_game_date
            ON team_game_logs(team_id, game_date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_game_logs_season
            ON team_game_logs(season, game_date DESC)
        ''')

        # ====================================================================
        # TODAY'S GAMES (Scoreboard data)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todays_games (
                game_id TEXT PRIMARY KEY,
                game_date TEXT NOT NULL,
                season TEXT NOT NULL,

                -- Teams
                home_team_id INTEGER NOT NULL,
                home_team_name TEXT NOT NULL,
                home_team_score INTEGER DEFAULT 0,
                away_team_id INTEGER NOT NULL,
                away_team_name TEXT NOT NULL,
                away_team_score INTEGER DEFAULT 0,

                -- Game status
                game_status_text TEXT,  -- "7:30 PM ET" or "Final" or "Q2 3:45"
                game_status_code INTEGER,  -- 1=scheduled, 2=live, 3=final
                game_time_utc TEXT,

                -- Metadata
                synced_at TEXT NOT NULL,

                FOREIGN KEY (home_team_id) REFERENCES nba_teams(team_id),
                FOREIGN KEY (away_team_id) REFERENCES nba_teams(team_id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_todays_games_date
            ON todays_games(game_date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_todays_games_season
            ON todays_games(season)
        ''')

        # ====================================================================
        # DATA SYNC LOG (Track sync operations)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,  -- 'teams', 'season_stats', 'game_logs', 'todays_games', 'full'
                season TEXT,
                status TEXT NOT NULL,  -- 'started', 'success', 'failed'
                records_synced INTEGER,
                error_message TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_seconds REAL,
                triggered_by TEXT  -- 'cron', 'manual', 'startup'
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sync_log_type
            ON data_sync_log(sync_type, started_at DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sync_log_status
            ON data_sync_log(status, started_at DESC)
        ''')

        # ====================================================================
        # LEAGUE AVERAGES (Fallback values)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS league_averages (
                season TEXT PRIMARY KEY,
                ppg REAL NOT NULL,
                pace REAL NOT NULL,
                off_rtg REAL NOT NULL,
                def_rtg REAL NOT NULL,
                fg_pct REAL NOT NULL,
                fg3_pct REAL NOT NULL,
                ft_pct REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # Insert default 2025-26 season averages (based on typical NBA stats)
        cursor.execute('''
            INSERT OR IGNORE INTO league_averages
            (season, ppg, pace, off_rtg, def_rtg, fg_pct, fg3_pct, ft_pct, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            '2025-26',
            115.0,  # PPG
            100.0,  # Pace
            115.0,  # Off Rating
            115.0,  # Def Rating
            46.5,   # FG%
            36.0,   # 3PT%
            78.0,   # FT%
            datetime.now().isoformat()
        ))

        conn.commit()

        print(f"NBA data database initialized at {NBA_DATA_DB_PATH}")
        print("Tables created:")
        print("  - nba_teams")
        print("  - team_season_stats")
        print("  - team_game_logs")
        print("  - todays_games")
        print("  - data_sync_log")
        print("  - league_averages")


if __name__ == '__main__':
    # Initialize database when run directly
    init_nba_data_db()
    print("\nDatabase initialization complete!")
