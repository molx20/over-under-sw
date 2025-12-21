"""
Home Court Statistics Calculator

Calculates home/road win percentages and recent home performance
for dynamic home court advantage calculation.
"""

import sqlite3
from typing import Optional, Dict

try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_home_court_stats(home_team_id: int, away_team_id: int, season: str = '2025-26') -> Dict:
    """
    Calculate home court advantage statistics for both teams.

    Args:
        home_team_id: Home team's NBA ID
        away_team_id: Away team's NBA ID
        season: Season string (default '2025-26')

    Returns:
        Dict with:
            home_win_pct: Home team's win% at home (0.0 to 1.0)
            road_win_pct: Away team's win% on road (0.0 to 1.0)
            last3_home_wins: Number of wins in home team's last 3 home games (0-3)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Calculate home team's home win percentage
    cursor.execute('''
        SELECT
            COUNT(*) as total_home_games,
            SUM(CASE WHEN win_loss = 'W' THEN 1 ELSE 0 END) as home_wins
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
          AND is_home = 1
    ''', (home_team_id, season))

    home_row = cursor.fetchone()
    total_home_games = home_row['total_home_games'] if home_row else 0
    home_wins = home_row['home_wins'] if home_row else 0

    # Calculate home win percentage (default to 0.500 if no games)
    home_win_pct = (home_wins / total_home_games) if total_home_games > 0 else 0.500

    # Calculate away team's road win percentage
    cursor.execute('''
        SELECT
            COUNT(*) as total_road_games,
            SUM(CASE WHEN win_loss = 'W' THEN 1 ELSE 0 END) as road_wins
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
          AND is_home = 0
    ''', (away_team_id, season))

    road_row = cursor.fetchone()
    total_road_games = road_row['total_road_games'] if road_row else 0
    road_wins = road_row['road_wins'] if road_row else 0

    # Calculate road win percentage (default to 0.500 if no games)
    road_win_pct = (road_wins / total_road_games) if total_road_games > 0 else 0.500

    # Get home team's last 3 home games and count wins
    cursor.execute('''
        SELECT win_loss
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
          AND is_home = 1
        ORDER BY game_date DESC
        LIMIT 3
    ''', (home_team_id, season))

    recent_home_games = cursor.fetchall()
    last3_home_wins = sum(1 for game in recent_home_games if game['win_loss'] == 'W')

    conn.close()

    return {
        'home_win_pct': home_win_pct,
        'road_win_pct': road_win_pct,
        'last3_home_wins': last3_home_wins,
        'home_record': f"{home_wins}-{total_home_games - home_wins}" if total_home_games > 0 else "0-0",
        'road_record': f"{road_wins}-{total_road_games - road_wins}" if total_road_games > 0 else "0-0"
    }
