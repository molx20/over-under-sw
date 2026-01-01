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
            'offensive': {...},      # EXISTING scoring archetypes
            'defensive': {...},      # EXISTING scoring archetypes
            'assists_offensive': {team_id: {'season': {...}, 'last_10': {...}}},
            'assists_defensive': {...},
            'rebounds_offensive': {...},
            'rebounds_defensive': {...},
            'threes_offensive': {...},
            'threes_defensive': {...},
            'turnovers_offensive': {...},
            'turnovers_defensive': {...}
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
        # Existing scoring archetypes
        'offensive': {},
        'defensive': {},
        # New archetype families
        'assists_offensive': {},
        'assists_defensive': {},
        'rebounds_offensive': {},
        'rebounds_defensive': {},
        'threes_offensive': {},
        'threes_defensive': {},
        'turnovers_offensive': {},
        'turnovers_defensive': {}
    }

    for team_id in team_ids:
        # EXISTING: Scoring Offensive features
        season_off = calculate_offensive_features(team_id, season, 'season')
        last10_off = calculate_offensive_features(team_id, season, 'last_10')

        if season_off and last10_off:
            result['offensive'][team_id] = {
                'season': season_off,
                'last_10': last10_off
            }

        # EXISTING: Scoring Defensive features
        season_def = calculate_defensive_features(team_id, season, 'season')
        last10_def = calculate_defensive_features(team_id, season, 'last_10')

        if season_def and last10_def:
            result['defensive'][team_id] = {
                'season': season_def,
                'last_10': last10_def
            }

        # NEW: Assists Offensive features
        season_assists_off = calculate_assists_features(team_id, season, 'season')
        last10_assists_off = calculate_assists_features(team_id, season, 'last_10')

        if season_assists_off and last10_assists_off:
            result['assists_offensive'][team_id] = {
                'season': season_assists_off,
                'last_10': last10_assists_off
            }

        # NEW: Assists Defensive features
        season_assists_def = calculate_assists_defensive_features(team_id, season, 'season')
        last10_assists_def = calculate_assists_defensive_features(team_id, season, 'last_10')

        if season_assists_def and last10_assists_def:
            result['assists_defensive'][team_id] = {
                'season': season_assists_def,
                'last_10': last10_assists_def
            }

        # NEW: Rebounds Offensive features
        season_rebounds_off = calculate_rebounds_features(team_id, season, 'season')
        last10_rebounds_off = calculate_rebounds_features(team_id, season, 'last_10')

        if season_rebounds_off and last10_rebounds_off:
            result['rebounds_offensive'][team_id] = {
                'season': season_rebounds_off,
                'last_10': last10_rebounds_off
            }

        # NEW: Rebounds Defensive features
        season_rebounds_def = calculate_rebounds_defensive_features(team_id, season, 'season')
        last10_rebounds_def = calculate_rebounds_defensive_features(team_id, season, 'last_10')

        if season_rebounds_def and last10_rebounds_def:
            result['rebounds_defensive'][team_id] = {
                'season': season_rebounds_def,
                'last_10': last10_rebounds_def
            }

        # NEW: Threes Offensive features
        season_threes_off = calculate_threes_features(team_id, season, 'season')
        last10_threes_off = calculate_threes_features(team_id, season, 'last_10')

        if season_threes_off and last10_threes_off:
            result['threes_offensive'][team_id] = {
                'season': season_threes_off,
                'last_10': last10_threes_off
            }

        # NEW: Threes Defensive features
        season_threes_def = calculate_threes_defensive_features(team_id, season, 'season')
        last10_threes_def = calculate_threes_defensive_features(team_id, season, 'last_10')

        if season_threes_def and last10_threes_def:
            result['threes_defensive'][team_id] = {
                'season': season_threes_def,
                'last_10': last10_threes_def
            }

        # NEW: Turnovers Offensive features
        season_turnovers_off = calculate_turnovers_features(team_id, season, 'season')
        last10_turnovers_off = calculate_turnovers_features(team_id, season, 'last_10')

        if season_turnovers_off and last10_turnovers_off:
            result['turnovers_offensive'][team_id] = {
                'season': season_turnovers_off,
                'last_10': last10_turnovers_off
            }

        # NEW: Turnovers Defensive features
        season_turnovers_def = calculate_turnovers_defensive_features(team_id, season, 'season')
        last10_turnovers_def = calculate_turnovers_defensive_features(team_id, season, 'last_10')

        if season_turnovers_def and last10_turnovers_def:
            result['turnovers_defensive'][team_id] = {
                'season': season_turnovers_def,
                'last_10': last10_turnovers_def
            }

    logger.info(f"Feature calculation complete: {len(result['offensive'])} teams with offensive features, "
                f"{len(result['defensive'])} teams with defensive features, "
                f"{len(result['assists_offensive'])} teams with assists offensive features, "
                f"{len(result['rebounds_offensive'])} teams with rebounds offensive features, "
                f"{len(result['threes_offensive'])} teams with threes offensive features, "
                f"{len(result['turnovers_offensive'])} teams with turnovers offensive features")

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


# ============================================================================
# NEW ARCHETYPE FAMILIES - Feature Names
# ============================================================================

# Assists Family
ASSISTS_FEATURE_NAMES = ['assists', 'assist_rate', 'assists_per_100']
ASSISTS_DEFENSIVE_FEATURE_NAMES = ['opp_assists', 'opp_assist_rate', 'opp_assists_per_100']

# Rebounds Family
REBOUNDS_FEATURE_NAMES = ['offensive_rebounds', 'defensive_rebounds', 'oreb_rate', 'dreb_rate', 'second_chance_points']
REBOUNDS_DEFENSIVE_FEATURE_NAMES = ['opp_offensive_rebounds', 'opp_defensive_rebounds', 'opp_oreb_rate', 'opp_dreb_rate', 'opp_second_chance_points']

# Threes Family
THREES_FEATURE_NAMES = ['fg3a', 'fg3_pct', 'three_pa_rate']
THREES_DEFENSIVE_FEATURE_NAMES = ['opp_fg3a', 'opp_fg3_pct', 'opp_three_pa_rate']

# Turnovers Family
TURNOVERS_FEATURE_NAMES = ['turnovers', 'turnover_rate', 'steals']
TURNOVERS_DEFENSIVE_FEATURE_NAMES = ['opp_turnovers', 'opp_turnover_rate', 'opp_steals']


# ============================================================================
# NEW ARCHETYPE FAMILIES - Feature Calculation Functions
# ============================================================================

def calculate_assists_features(team_id: int, season: str,
                               window: str = 'season') -> Dict:
    """
    Calculate assists feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        window: 'season' or 'last_10'

    Returns:
        Dict with 3 assists features + metadata:
        {
            'assists': float,
            'assist_rate': float,
            'assists_per_100': float,
            'games_count': int,
            'window': str
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(assists) as avg_assists,
                AVG(fgm) as avg_fgm,
                AVG(possessions) as avg_possessions
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(assists) as avg_assists,
                AVG(fgm) as avg_fgm,
                AVG(possessions) as avg_possessions
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

    features = {
        'assists': row['avg_assists'] or 0.0,
        'assist_rate': _safe_divide(row['avg_assists'], row['avg_fgm']),
        'assists_per_100': _safe_divide(row['avg_assists'], row['avg_possessions']) * 100,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Assists features for team {team_id} ({window}): {features}")
    return features


def calculate_assists_defensive_features(team_id: int, season: str,
                                        window: str = 'season') -> Dict:
    """
    Calculate assists defensive feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string
        window: 'season' or 'last_10'

    Returns:
        Dict with 3 defensive assists features + metadata
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_assists) as avg_opp_assists,
                AVG(opp_fgm) as avg_opp_fgm,
                AVG(opp_possessions) as avg_opp_possessions
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_assists) as avg_opp_assists,
                AVG(opp_fgm) as avg_opp_fgm,
                AVG(opp_possessions) as avg_opp_possessions
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

    features = {
        'opp_assists': row['avg_opp_assists'] or 0.0,
        'opp_assist_rate': _safe_divide(row['avg_opp_assists'], row['avg_opp_fgm']),
        'opp_assists_per_100': _safe_divide(row['avg_opp_assists'], row['avg_opp_possessions']) * 100,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Assists defensive features for team {team_id} ({window}): {features}")
    return features


def calculate_rebounds_features(team_id: int, season: str,
                                window: str = 'season') -> Dict:
    """
    Calculate rebounds feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        window: 'season' or 'last_10'

    Returns:
        Dict with 5 rebounds features + metadata:
        {
            'offensive_rebounds': float,
            'defensive_rebounds': float,
            'oreb_rate': float,
            'dreb_rate': float,
            'second_chance_points': float,
            'games_count': int,
            'window': str
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(offensive_rebounds) as avg_oreb,
                AVG(defensive_rebounds) as avg_dreb,
                AVG(opp_offensive_rebounds) as avg_opp_oreb,
                AVG(opp_defensive_rebounds) as avg_opp_dreb,
                AVG(second_chance_points) as avg_second_chance
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(offensive_rebounds) as avg_oreb,
                AVG(defensive_rebounds) as avg_dreb,
                AVG(opp_offensive_rebounds) as avg_opp_oreb,
                AVG(opp_defensive_rebounds) as avg_opp_dreb,
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

    features = {
        'offensive_rebounds': row['avg_oreb'] or 0.0,
        'defensive_rebounds': row['avg_dreb'] or 0.0,
        'oreb_rate': _safe_divide(row['avg_oreb'], (row['avg_oreb'] or 0.0) + (row['avg_opp_dreb'] or 0.0)) * 100,
        'dreb_rate': _safe_divide(row['avg_dreb'], (row['avg_dreb'] or 0.0) + (row['avg_opp_oreb'] or 0.0)) * 100,
        'second_chance_points': row['avg_second_chance'] or 0.0,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Rebounds features for team {team_id} ({window}): {features}")
    return features


def calculate_rebounds_defensive_features(team_id: int, season: str,
                                          window: str = 'season') -> Dict:
    """
    Calculate rebounds defensive feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string
        window: 'season' or 'last_10'

    Returns:
        Dict with 5 defensive rebounds features + metadata
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_offensive_rebounds) as avg_opp_oreb,
                AVG(opp_defensive_rebounds) as avg_opp_dreb,
                AVG(offensive_rebounds) as avg_oreb,
                AVG(defensive_rebounds) as avg_dreb,
                AVG(opp_second_chance_points) as avg_opp_second_chance
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_offensive_rebounds) as avg_opp_oreb,
                AVG(opp_defensive_rebounds) as avg_opp_dreb,
                AVG(offensive_rebounds) as avg_oreb,
                AVG(defensive_rebounds) as avg_dreb,
                AVG(opp_second_chance_points) as avg_opp_second_chance
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

    features = {
        'opp_offensive_rebounds': row['avg_opp_oreb'] or 0.0,
        'opp_defensive_rebounds': row['avg_opp_dreb'] or 0.0,
        'opp_oreb_rate': _safe_divide(row['avg_opp_oreb'], (row['avg_opp_oreb'] or 0.0) + (row['avg_dreb'] or 0.0)) * 100,
        'opp_dreb_rate': _safe_divide(row['avg_opp_dreb'], (row['avg_opp_dreb'] or 0.0) + (row['avg_oreb'] or 0.0)) * 100,
        'opp_second_chance_points': row['avg_opp_second_chance'] or 0.0,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Rebounds defensive features for team {team_id} ({window}): {features}")
    return features


def calculate_threes_features(team_id: int, season: str,
                              window: str = 'season') -> Dict:
    """
    Calculate threes feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        window: 'season' or 'last_10'

    Returns:
        Dict with 3 threes features + metadata:
        {
            'fg3a': float,
            'fg3_pct': float,
            'three_pa_rate': float,
            'games_count': int,
            'window': str
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(fg3a) as avg_fg3a,
                AVG(fg3m) as avg_fg3m,
                AVG(fga) as avg_fga
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(fg3a) as avg_fg3a,
                AVG(fg3m) as avg_fg3m,
                AVG(fga) as avg_fga
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

    features = {
        'fg3a': row['avg_fg3a'] or 0.0,
        'fg3_pct': _safe_divide(row['avg_fg3m'], row['avg_fg3a']),
        'three_pa_rate': _safe_divide(row['avg_fg3a'], row['avg_fga']),
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Threes features for team {team_id} ({window}): {features}")
    return features


def calculate_threes_defensive_features(team_id: int, season: str,
                                       window: str = 'season') -> Dict:
    """
    Calculate threes defensive feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string
        window: 'season' or 'last_10'

    Returns:
        Dict with 3 defensive threes features + metadata
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_fg3a) as avg_opp_fg3a,
                AVG(opp_fg3m) as avg_opp_fg3m,
                AVG(opp_fga) as avg_opp_fga
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_fg3a) as avg_opp_fg3a,
                AVG(opp_fg3m) as avg_opp_fg3m,
                AVG(opp_fga) as avg_opp_fga
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

    features = {
        'opp_fg3a': row['avg_opp_fg3a'] or 0.0,
        'opp_fg3_pct': _safe_divide(row['avg_opp_fg3m'], row['avg_opp_fg3a']),
        'opp_three_pa_rate': _safe_divide(row['avg_opp_fg3a'], row['avg_opp_fga']),
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Threes defensive features for team {team_id} ({window}): {features}")
    return features


def calculate_turnovers_features(team_id: int, season: str,
                                 window: str = 'season') -> Dict:
    """
    Calculate turnovers feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        window: 'season' or 'last_10'

    Returns:
        Dict with 3 turnovers features + metadata:
        {
            'turnovers': float,
            'turnover_rate': float,
            'steals': float,
            'games_count': int,
            'window': str
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(turnovers) as avg_turnovers,
                AVG(possessions) as avg_possessions,
                AVG(steals) as avg_steals
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(turnovers) as avg_turnovers,
                AVG(possessions) as avg_possessions,
                AVG(steals) as avg_steals
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

    features = {
        'turnovers': row['avg_turnovers'] or 0.0,
        'turnover_rate': _safe_divide(row['avg_turnovers'], row['avg_possessions']),
        'steals': row['avg_steals'] or 0.0,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Turnovers features for team {team_id} ({window}): {features}")
    return features


def calculate_turnovers_defensive_features(team_id: int, season: str,
                                          window: str = 'season') -> Dict:
    """
    Calculate turnovers defensive feature vector for a team.

    Args:
        team_id: NBA team ID
        season: Season string
        window: 'season' or 'last_10'

    Returns:
        Dict with 3 defensive turnovers features + metadata
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if window == 'season':
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_turnovers) as avg_opp_turnovers,
                AVG(opp_possessions) as avg_opp_possessions,
                AVG(opp_steals) as avg_opp_steals
            FROM team_game_logs
            WHERE team_id = ?
            AND season = ?
            {GAME_FILTER}
        ''', (team_id, season))
    else:  # last_10
        cursor.execute(f'''
            SELECT
                COUNT(*) as games_count,
                AVG(opp_turnovers) as avg_opp_turnovers,
                AVG(opp_possessions) as avg_opp_possessions,
                AVG(opp_steals) as avg_opp_steals
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

    features = {
        'opp_turnovers': row['avg_opp_turnovers'] or 0.0,
        'opp_turnover_rate': _safe_divide(row['avg_opp_turnovers'], row['avg_opp_possessions']),
        'opp_steals': row['avg_opp_steals'] or 0.0,
        'games_count': row['games_count'],
        'window': window
    }

    logger.debug(f"Turnovers defensive features for team {team_id} ({window}): {features}")
    return features
