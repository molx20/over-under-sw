"""
3-Point Shootout Statistics Queries

Gathers all statistics needed for dynamic shootout adjustment:
- Team season 3PT%
- Opponent 3PT% allowed
- Recent 3PT% (last 5 games)
- League average 3PT%
- Rest days and back-to-back status
"""

import sqlite3
from typing import Optional, Dict
from datetime import datetime, timedelta

try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')

# League average 3PT% for 2025-26 season (updated based on actual league stats)
LEAGUE_AVG_3P_PCT = 0.365


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_team_season_3pt_pct(team_id: int, season: str = '2025-26') -> Optional[float]:
    """
    Get team's season 3PT percentage.

    Args:
        team_id: Team's NBA ID
        season: Season string

    Returns:
        3PT% as decimal (e.g., 0.380 for 38.0%) or None if no data
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT AVG(CAST(fg3m AS REAL) / NULLIF(fg3a, 0)) as season_3p_pct
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
          AND fg3a > 0
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if row and row['season_3p_pct'] is not None:
        return row['season_3p_pct']
    return None


def get_opponent_3pt_pct_allowed(team_id: int, season: str = '2025-26') -> Optional[float]:
    """
    Get opponent's 3PT% allowed (defensive 3PT%).

    This calculates the average 3PT% that opponents have shot against this team.

    Args:
        team_id: Team's NBA ID (the defensive team)
        season: Season string

    Returns:
        Opponent 3PT% as decimal or None if no data
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get all games for this team, then calculate opponent's 3PT%
    # We need to look at opponent_team_id's stats from those games
    cursor.execute('''
        SELECT
            team_id as opponent_id,
            AVG(CAST(fg3m AS REAL) / NULLIF(fg3a, 0)) as opp_3p_pct
        FROM team_game_logs
        WHERE game_id IN (
            SELECT game_id
            FROM team_game_logs
            WHERE team_id = ? AND season = ?
        )
        AND team_id != ?
        AND season = ?
        AND fg3a > 0
    ''', (team_id, season, team_id, season))

    row = cursor.fetchone()
    conn.close()

    if row and row['opp_3p_pct'] is not None:
        return row['opp_3p_pct']
    return None


def get_last5_3pt_pct(team_id: int, season: str = '2025-26') -> Optional[float]:
    """
    Get team's 3PT% over last 5 games.

    Args:
        team_id: Team's NBA ID
        season: Season string

    Returns:
        Last 5 games 3PT% as decimal or None if insufficient data
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            AVG(CAST(fg3m AS REAL) / NULLIF(fg3a, 0)) as last5_3p_pct
        FROM (
            SELECT fg3m, fg3a
            FROM team_game_logs
            WHERE team_id = ?
              AND season = ?
              AND fg3a > 0
            ORDER BY game_date DESC
            LIMIT 5
        )
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if row and row['last5_3p_pct'] is not None:
        return row['last5_3p_pct']
    return None


def get_rest_days(team_id: int, season: str = '2025-26') -> tuple[int, bool]:
    """
    Calculate rest days before today's game.

    Args:
        team_id: Team's NBA ID
        season: Season string

    Returns:
        Tuple of (rest_days, on_back_to_back)
            rest_days: Number of days since last game (0, 1, 2, 3+)
            on_back_to_back: True if playing back-to-back (played yesterday)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get most recent game
    cursor.execute('''
        SELECT game_date
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
        ORDER BY game_date DESC
        LIMIT 1
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row or not row['game_date']:
        # No recent games found, assume well-rested
        return (3, False)

    try:
        last_game_date_str = row['game_date']

        # Handle datetime format (strip time if present)
        if 'T' in last_game_date_str:
            last_game_date_str = last_game_date_str.split('T')[0]

        last_game_date = datetime.strptime(last_game_date_str, '%Y-%m-%d').date()
        today = datetime.now().date()

        rest_days = (today - last_game_date).days
        on_back_to_back = (rest_days == 1)  # Played yesterday

        return (rest_days, on_back_to_back)
    except Exception as e:
        print(f'[shootout_stats] Error calculating rest days: {e}')
        return (1, False)  # Default to normal rest


def get_shootout_stats(team_id: int, opponent_id: int, projected_pace: float, season: str = '2025-26') -> Dict:
    """
    Gather all statistics needed for dynamic shootout adjustment.

    Args:
        team_id: Team's NBA ID
        opponent_id: Opponent's NBA ID
        projected_pace: Projected game pace (possessions per 48 min)
        season: Season string

    Returns:
        Dict with all inputs needed for calculate_shootout_bonus():
            team_3p_pct: Team's season 3PT%
            league_avg_3p_pct: League average 3PT%
            opponent_3p_allowed_pct: Opponent's 3PT% allowed
            last5_3p_pct: Team's last 5 games 3PT%
            season_3p_pct: Team's season 3PT% (duplicate for clarity)
            projected_pace: Projected game pace
            rest_days: Days of rest
            on_back_to_back: Back-to-back status
            has_data: True if all critical data available
    """
    # Get team's season 3PT%
    team_3p_pct = get_team_season_3pt_pct(team_id, season)

    # Get opponent's 3PT% allowed
    opponent_3p_allowed_pct = get_opponent_3pt_pct_allowed(opponent_id, season)

    # Get team's last 5 games 3PT%
    last5_3p_pct = get_last5_3pt_pct(team_id, season)

    # Get rest status
    rest_days, on_back_to_back = get_rest_days(team_id, season)

    # Check if we have all critical data
    has_data = (
        team_3p_pct is not None and
        opponent_3p_allowed_pct is not None and
        last5_3p_pct is not None
    )

    # Use fallbacks if data missing
    if team_3p_pct is None:
        team_3p_pct = LEAGUE_AVG_3P_PCT
    if opponent_3p_allowed_pct is None:
        opponent_3p_allowed_pct = LEAGUE_AVG_3P_PCT
    if last5_3p_pct is None:
        last5_3p_pct = team_3p_pct  # Use season average as fallback

    return {
        'team_3p_pct': team_3p_pct,
        'league_avg_3p_pct': LEAGUE_AVG_3P_PCT,
        'opponent_3p_allowed_pct': opponent_3p_allowed_pct,
        'last5_3p_pct': last5_3p_pct,
        'season_3p_pct': team_3p_pct,
        'projected_pace': projected_pace,
        'rest_days': rest_days,
        'on_back_to_back': on_back_to_back,
        'has_data': has_data
    }
