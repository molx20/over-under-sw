"""
Pace Projection Module

Calculates projected game pace based on both teams' season averages and recent form.
"""

import sqlite3
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_team_recent_pace(team_id: int, season: str = '2025-26', n_games: int = 5) -> Optional[float]:
    """
    Get team's average pace over last N games.

    Args:
        team_id: Team's NBA ID
        season: Season string
        n_games: Number of recent games to average (default 5)

    Returns:
        Average pace over last N games, or None if insufficient data
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT pace
            FROM team_game_logs
            WHERE team_id = ? AND season = ? AND pace IS NOT NULL
            ORDER BY game_date DESC
            LIMIT ?
        ''', (team_id, season, n_games))

        pace_values = [row['pace'] for row in cursor.fetchall()]
        conn.close()

        if not pace_values:
            return None

        avg_pace = sum(pace_values) / len(pace_values)
        logger.info(f'Team {team_id} recent pace (last {len(pace_values)} games): {avg_pace:.1f}')
        return avg_pace

    except Exception as e:
        logger.error(f'Error fetching recent pace for team {team_id}: {e}')
        return None


def calculate_projected_pace(home_team_id: int, away_team_id: int, season: str = '2025-26') -> float:
    """
    Calculate projected game pace using both season averages and recent form.

    Formula:
    - Get each team's season average pace
    - Get each team's last 5 games average pace
    - Blend: 40% season average + 60% recent form (recent weighted more heavily)
    - Final projection: home_blended * 0.52 + away_blended * 0.48

    Args:
        home_team_id: Home team's NBA ID
        away_team_id: Away team's NBA ID
        season: Season string

    Returns:
        Projected pace (possessions per 48 minutes)
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Get season average pace for both teams
        cursor.execute('''
            SELECT pace
            FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = 'overall'
        ''', (home_team_id, season))
        home_season_row = cursor.fetchone()
        home_season_pace = home_season_row['pace'] if home_season_row and home_season_row['pace'] else 100.0

        cursor.execute('''
            SELECT pace
            FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = 'overall'
        ''', (away_team_id, season))
        away_season_row = cursor.fetchone()
        away_season_pace = away_season_row['pace'] if away_season_row and away_season_row['pace'] else 100.0

        conn.close()

        # Get recent pace (last 5 games) for both teams
        home_recent_pace = get_team_recent_pace(home_team_id, season, n_games=5)
        away_recent_pace = get_team_recent_pace(away_team_id, season, n_games=5)

        # If no recent data, fall back to season average
        if home_recent_pace is None:
            home_recent_pace = home_season_pace
        if away_recent_pace is None:
            away_recent_pace = away_season_pace

        # Blend season average (40%) and recent form (60%)
        # Recent form weighted more heavily to capture current playing style
        home_blended = (home_season_pace * 0.4) + (home_recent_pace * 0.6)
        away_blended = (away_season_pace * 0.4) + (away_recent_pace * 0.6)

        # Final projection: equal weight for both teams (50/50 split)
        projected_pace = (home_blended * 0.5) + (away_blended * 0.5)

        logger.info(
            f'Pace projection: Home {home_season_pace:.1f} (season) → {home_recent_pace:.1f} (recent) → {home_blended:.1f} (blended), '
            f'Away {away_season_pace:.1f} (season) → {away_recent_pace:.1f} (recent) → {away_blended:.1f} (blended), '
            f'Projected: {projected_pace:.1f}'
        )

        return projected_pace

    except Exception as e:
        logger.error(f'Error calculating projected pace: {e}')
        import traceback
        traceback.print_exc()
        # Fallback to league average
        return 100.0
