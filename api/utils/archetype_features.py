"""
Archetype Feature Engineering Module

Calculates offensive and defensive feature vectors for team archetype classification.
All features derived from existing database stats in team_game_logs and team_season_stats.

Feature Vectors:
- Offensive (9 features): ft_rate, ft_ppg, pitp_ppg, pitp_share, three_pa_rate,
                          efg_pct, assist_rate, turnover_rate, second_chance_ppg
- Defensive (7 features): opp_ft_rate, opp_ft_ppg, opp_pitp_ppg, opp_three_pa_rate,
                          opp_efg_pct, opp_turnovers_forced, opp_pace
"""

import sqlite3
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')

# Game type filter for Regular Season + NBA Cup only
GAME_FILTER = "AND game_type IN ('Regular Season', 'NBA Cup')"


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default fallback"""
    if denominator == 0 or denominator is None or numerator is None:
        return default
    return numerator / denominator


def calculate_offensive_features(team_id: int, season: str,
                                 window: str = 'season') -> Dict:
    """
    Calculate offensive feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        window: 'season' or 'last_10'

    Returns:
        Dict with 9 offensive features + metadata:
        {
            'ft_rate': float,
            'ft_ppg': float,
            'pitp_ppg': float,
            'pitp_share': float,
            'three_pa_rate': float,
            'efg_pct': float,
            'assist_rate': float,
            'turnover_rate': float,
            'second_chance_ppg': float,
            'games_count': int,
            'window': str
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        # Query season-level stats
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(fta) as avg_fta,
                AVG(fga) as avg_fga,
                AVG(ftm) as avg_ftm,
                AVG(points_in_paint) as avg_pitp,
                AVG(team_pts) as avg_pts,
                AVG(fg3a) as avg_fg3a,
                AVG(fgm) as avg_fgm,
                AVG(fg3m) as avg_fg3m,
                AVG(assists) as avg_assists,
                AVG(turnovers) as avg_turnovers,
                AVG(possessions) as avg_possessions,
                AVG(second_chance_points) as avg_second_chance
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))

    else:  # last_10
        # Query last 10 games
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(fta) as avg_fta,
                AVG(fga) as avg_fga,
                AVG(ftm) as avg_ftm,
                AVG(points_in_paint) as avg_pitp,
                AVG(team_pts) as avg_pts,
                AVG(fg3a) as avg_fg3a,
                AVG(fgm) as avg_fgm,
                AVG(fg3m) as avg_fg3m,
                AVG(assists) as avg_assists,
                AVG(turnovers) as avg_turnovers,
                AVG(possessions) as avg_possessions,
                AVG(second_chance_points) as avg_second_chance
            FROM (
                SELECT *
                FROM team_game_logs
                WHERE team_id = ?
                AND season = ?
                {GAME_FILTER}
                ORDER BY game_date DESC
                LIMIT 10
            )
        ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row or row['games_count'] == 0:
        logger.warning(f"No game data found for team {team_id}, {window}")
        return None

    # Calculate features
    features = {
        'ft_rate': _safe_divide(row['avg_fta'], row['avg_fga']),
        'ft_ppg': row['avg_ftm'] or 0.0,
        'pitp_ppg': row['avg_pitp'] or 0.0,
        'pitp_share': _safe_divide(row['avg_pitp'], row['avg_pts']),
        'three_pa_rate': _safe_divide(row['avg_fg3a'], row['avg_fga']),
        'efg_pct': _safe_divide(row['avg_fgm'] + 0.5 * row['avg_fg3m'], row['avg_fga']),
        'assist_rate': _safe_divide(row['avg_assists'], row['avg_fgm']),
        'turnover_rate': _safe_divide(row['avg_turnovers'], row['avg_possessions']),
        'second_chance_ppg': row['avg_second_chance'] or 0.0,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Offensive features for team {team_id} ({window}): {features}")
    return features


def calculate_defensive_features(team_id: int, season: str,
                                 window: str = 'season') -> Dict:
    """
    Calculate defensive feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string
        window: 'season' or 'last_10'

    Returns:
        Dict with 7 defensive features + metadata:
        {
            'opp_ft_rate': float,
            'opp_ft_ppg': float,
            'opp_pitp_ppg': float,
            'opp_three_pa_rate': float,
            'opp_efg_pct': float,
            'opp_turnovers_forced': float,
            'opp_pace': float,
            'games_count': int,
            'window': str
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        # Query season-level opponent stats
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_fta) as avg_opp_fta,
                AVG(opp_fga) as avg_opp_fga,
                AVG(opp_ftm) as avg_opp_ftm,
                AVG(opp_points_in_paint) as avg_opp_pitp,
                AVG(opp_fg3a) as avg_opp_fg3a,
                AVG(opp_fgm) as avg_opp_fgm,
                AVG(opp_fg3m) as avg_opp_fg3m,
                AVG(opp_turnovers) as avg_opp_turnovers,
                AVG(opp_pace) as avg_opp_pace
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))

    else:  # last_10
        # Query last 10 games opponent stats
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_fta) as avg_opp_fta,
                AVG(opp_fga) as avg_opp_fga,
                AVG(opp_ftm) as avg_opp_ftm,
                AVG(opp_points_in_paint) as avg_opp_pitp,
                AVG(opp_fg3a) as avg_opp_fg3a,
                AVG(opp_fgm) as avg_opp_fgm,
                AVG(opp_fg3m) as avg_opp_fg3m,
                AVG(opp_turnovers) as avg_opp_turnovers,
                AVG(opp_pace) as avg_opp_pace
            FROM (
                SELECT *
                FROM team_game_logs
                WHERE team_id = ?
                AND season = ?
                {GAME_FILTER}
                ORDER BY game_date DESC
                LIMIT 10
            )
        ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row or row['games_count'] == 0:
        logger.warning(f"No game data found for team {team_id}, {window}")
        return None

    # Calculate features
    features = {
        'opp_ft_rate': _safe_divide(row['avg_opp_fta'], row['avg_opp_fga']),
        'opp_ft_ppg': row['avg_opp_ftm'] or 0.0,
        'opp_pitp_ppg': row['avg_opp_pitp'] or 0.0,
        'opp_three_pa_rate': _safe_divide(row['avg_opp_fg3a'], row['avg_opp_fga']),
        'opp_efg_pct': _safe_divide(row['avg_opp_fgm'] + 0.5 * row['avg_opp_fg3m'], row['avg_opp_fga']),
        'opp_turnovers_forced': row['avg_opp_turnovers'] or 0.0,
        'opp_pace': row['avg_opp_pace'] or 0.0,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Defensive features for team {team_id} ({window}): {features}")
    return features


def calculate_all_team_features(season: str = '2025-26') -> Dict:
    """
    Calculate features for all 30 teams (season + last 10).

    Args:
        season: Season string

    Returns:
        {
            'offensive': {
                team_id: {
                    'season': {...9 features...},
                    'last_10': {...9 features...}
                },
                ...
            },
            'defensive': {
                team_id: {
                    'season': {...7 features...},
                    'last_10': {...7 features...}
                },
                ...
            }
        }
    """
    # Get all team IDs
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DISTINCT team_id
        FROM team_game_logs
        WHERE season = ?
    ''', (season,))

    team_ids = [row['team_id'] for row in cursor.fetchall()]
    conn.close()

    logger.info(f"Calculating features for {len(team_ids)} teams in season {season}")

    # Calculate features for each team
    result = {
        'offensive': {},
        'defensive': {}
    }

    for team_id in team_ids:
        # Offensive features
        season_off = calculate_offensive_features(team_id, season, 'season')
        last10_off = calculate_offensive_features(team_id, season, 'last_10')

        if season_off and last10_off:
            result['offensive'][team_id] = {
                'season': season_off,
                'last_10': last10_off
            }

        # Defensive features
        season_def = calculate_defensive_features(team_id, season, 'season')
        last10_def = calculate_defensive_features(team_id, season, 'last_10')

        if season_def and last10_def:
            result['defensive'][team_id] = {
                'season': season_def,
                'last_10': last10_def
            }

    logger.info(f"Feature calculation complete: {len(result['offensive'])} teams with offensive features, "
                f"{len(result['defensive'])} teams with defensive features")

    return result


# List of feature names for reference
OFFENSIVE_FEATURE_NAMES = [
    'ft_rate',
    'ft_ppg',
    'pitp_ppg',
    'pitp_share',
    'three_pa_rate',
    'efg_pct',
    'assist_rate',
    'turnover_rate',
    'second_chance_ppg'
]

DEFENSIVE_FEATURE_NAMES = [
    'opp_ft_rate',
    'opp_ft_ppg',
    'opp_pitp_ppg',
    'opp_three_pa_rate',
    'opp_efg_pct',
    'opp_turnovers_forced',
    'opp_pace'
]
