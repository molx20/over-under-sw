"""
Style Stats Builder Module

Builds detailed per-team expected and actual stats for AI Model Coach analysis.
This module extracts comprehensive statistics for post-game comparison.

Expected stats: Constructed from season averages + projected pace
Actual stats: Extracted from completed game box scores

Usage:
    from api.utils.style_stats_builder import build_expected_style_stats, build_actual_style_stats

    expected = build_expected_style_stats(home_team_id, away_team_id, predicted_pace, season)
    actual = build_actual_style_stats(game_id, home_team_id, away_team_id)
"""

import sqlite3
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
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


def _safe_round(value, decimals=1):
    """Safely round a value, returning None if value is None"""
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return None


def build_expected_style_stats(
    home_team_id: int,
    away_team_id: int,
    predicted_pace: Optional[float] = None,
    season: str = '2025-26'
) -> Dict:
    """
    Build expected style stats for both teams based on season averages.

    This constructs what we EXPECTED each team to do based on:
    - Season-long averages
    - Projected game pace (if provided)

    Args:
        home_team_id: Home team ID
        away_team_id: Away team ID
        predicted_pace: Model's predicted game pace (optional)
        season: NBA season

    Returns:
        {
            'home': {
                'pace': float,
                'fg_pct': float,
                'fg3a': float,
                'fg3m': float,
                'fg3_pct': float,
                'fta': float,
                'ftm': float,
                'ft_pct': float,
                'oreb': int,
                'dreb': int,
                'reb': int,
                'assists': int,
                'steals': int,
                'blocks': int,
                'turnovers': int,
                'points_off_turnovers': int,
                'fastbreak_points': int,
                'paint_points': int,
                'second_chance_points': int
            },
            'away': { ... same structure ... }
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    result = {
        'home': None,
        'away': None
    }

    try:
        for team_type, team_id in [('home', home_team_id), ('away', away_team_id)]:
            # Query season averages
            cursor.execute('''
                SELECT
                    AVG(pace) as avg_pace,
                    AVG(fg_pct) as avg_fg_pct,
                    AVG(fg3a) as avg_fg3a,
                    AVG(fg3m) as avg_fg3m,
                    AVG(fg3_pct) as avg_fg3_pct,
                    AVG(fta) as avg_fta,
                    AVG(ftm) as avg_ftm,
                    AVG(ft_pct) as avg_ft_pct,
                    AVG(offensive_rebounds) as avg_oreb,
                    AVG(defensive_rebounds) as avg_dreb,
                    AVG(rebounds) as avg_reb,
                    AVG(assists) as avg_assists,
                    AVG(steals) as avg_steals,
                    AVG(blocks) as avg_blocks,
                    AVG(turnovers) as avg_turnovers,
                    AVG(points_off_turnovers) as avg_points_off_turnovers,
                    AVG(fast_break_points) as avg_fastbreak_points,
                    AVG(points_in_paint) as avg_paint_points,
                    AVG(second_chance_points) as avg_second_chance_points
                FROM team_game_logs
                WHERE team_id = ? AND season = ?
            ''', (team_id, season))

            row = cursor.fetchone()

            if row:
                # Use predicted pace if provided, otherwise use team's avg pace
                pace_to_use = predicted_pace if predicted_pace else row['avg_pace']

                result[team_type] = {
                    'pace': _safe_round(pace_to_use, 1),
                    'fg_pct': _safe_round(row['avg_fg_pct'] * 100, 1) if row['avg_fg_pct'] else None,  # Convert to percentage
                    'fg3a': _safe_round(row['avg_fg3a'], 1),
                    'fg3m': _safe_round(row['avg_fg3m'], 1),
                    'fg3_pct': _safe_round(row['avg_fg3_pct'] * 100, 1) if row['avg_fg3_pct'] else None,  # Convert to percentage
                    'fta': _safe_round(row['avg_fta'], 1),
                    'ftm': _safe_round(row['avg_ftm'], 1),
                    'ft_pct': _safe_round(row['avg_ft_pct'] * 100, 1) if row['avg_ft_pct'] else None,  # Convert to percentage
                    'oreb': _safe_round(row['avg_oreb'], 1),
                    'dreb': _safe_round(row['avg_dreb'], 1),
                    'reb': _safe_round(row['avg_reb'], 1),
                    'assists': _safe_round(row['avg_assists'], 1),
                    'steals': _safe_round(row['avg_steals'], 1),
                    'blocks': _safe_round(row['avg_blocks'], 1),
                    'turnovers': _safe_round(row['avg_turnovers'], 1),
                    'points_off_turnovers': _safe_round(row['avg_points_off_turnovers'], 1),
                    'fastbreak_points': _safe_round(row['avg_fastbreak_points'], 1),
                    'paint_points': _safe_round(row['avg_paint_points'], 1),
                    'second_chance_points': _safe_round(row['avg_second_chance_points'], 1)
                }

                logger.info(f"[StyleStats] Built expected stats for {team_type} team (ID: {team_id})")
            else:
                logger.warning(f"[StyleStats] No data found for {team_type} team (ID: {team_id})")

    except Exception as e:
        logger.error(f"[StyleStats] Error building expected stats: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()

    return result


def build_actual_style_stats(
    game_id: str,
    home_team_id: int,
    away_team_id: int
) -> Dict:
    """
    Build actual style stats for both teams from completed game box scores.

    This extracts what ACTUALLY happened in the game from the database.

    Args:
        game_id: NBA game ID (e.g., "0022500338")
        home_team_id: Home team ID
        away_team_id: Away team ID

    Returns:
        {
            'home': {
                'pace': float,
                'fg_pct': float,
                'fg3a': int,
                'fg3m': int,
                'fg3_pct': float,
                'fta': int,
                'ftm': int,
                'ft_pct': float,
                'oreb': int,
                'dreb': int,
                'reb': int,
                'assists': int,
                'steals': int,
                'blocks': int,
                'turnovers': int,
                'points_off_turnovers': int,
                'fastbreak_points': int,
                'paint_points': int,
                'second_chance_points': int
            },
            'away': { ... same structure ... }
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    result = {
        'home': None,
        'away': None
    }

    try:
        for team_type, team_id in [('home', home_team_id), ('away', away_team_id)]:
            # Query actual game stats
            cursor.execute('''
                SELECT
                    pace,
                    fg_pct,
                    fg3a,
                    fg3m,
                    fg3_pct,
                    fta,
                    ftm,
                    ft_pct,
                    offensive_rebounds,
                    defensive_rebounds,
                    rebounds,
                    assists,
                    steals,
                    blocks,
                    turnovers,
                    points_off_turnovers,
                    fast_break_points,
                    points_in_paint,
                    second_chance_points
                FROM team_game_logs
                WHERE game_id = ? AND team_id = ?
            ''', (game_id, team_id))

            row = cursor.fetchone()

            if row:
                result[team_type] = {
                    'pace': _safe_round(row['pace'], 1),
                    'fg_pct': _safe_round(row['fg_pct'] * 100, 1) if row['fg_pct'] else None,  # Convert to percentage
                    'fg3a': row['fg3a'],
                    'fg3m': row['fg3m'],
                    'fg3_pct': _safe_round(row['fg3_pct'] * 100, 1) if row['fg3_pct'] else None,  # Convert to percentage
                    'fta': row['fta'],
                    'ftm': row['ftm'],
                    'ft_pct': _safe_round(row['ft_pct'] * 100, 1) if row['ft_pct'] else None,  # Convert to percentage
                    'oreb': row['offensive_rebounds'],
                    'dreb': row['defensive_rebounds'],
                    'reb': row['rebounds'],
                    'assists': row['assists'],
                    'steals': row['steals'],
                    'blocks': row['blocks'],
                    'turnovers': row['turnovers'],
                    'points_off_turnovers': row['points_off_turnovers'],
                    'fastbreak_points': row['fast_break_points'],
                    'paint_points': row['points_in_paint'],
                    'second_chance_points': row['second_chance_points']
                }

                logger.info(f"[StyleStats] Extracted actual stats for {team_type} team (ID: {team_id})")
            else:
                logger.warning(f"[StyleStats] No game data found for {team_type} team (Game ID: {game_id}, Team ID: {team_id})")

    except Exception as e:
        logger.error(f"[StyleStats] Error building actual stats: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()

    return result


if __name__ == '__main__':
    # Test the functions
    print("Testing Style Stats Builder")
    print("=" * 80)

    # Test with hypothetical game
    test_game_id = "0022500338"
    test_home_id = 1610612760  # OKC
    test_away_id = 1610612756  # PHX
    test_predicted_pace = 102.5

    print("\n1. Testing Expected Style Stats:")
    print("-" * 80)
    expected = build_expected_style_stats(test_home_id, test_away_id, test_predicted_pace)

    if expected['home']:
        print(f"Home Team Expected:")
        print(f"  Pace: {expected['home']['pace']}")
        print(f"  FG%: {expected['home']['fg_pct']}")
        print(f"  3PA: {expected['home']['fg3a']}")
        print(f"  3P%: {expected['home']['fg3_pct']}")
        print(f"  FTA: {expected['home']['fta']}")
        print(f"  Rebounds: {expected['home']['reb']}")
        print(f"  Assists: {expected['home']['assists']}")
        print(f"  Turnovers: {expected['home']['turnovers']}")
        print(f"  Paint Points: {expected['home']['paint_points']}")

    print("\n2. Testing Actual Style Stats:")
    print("-" * 80)
    actual = build_actual_style_stats(test_game_id, test_home_id, test_away_id)

    if actual['home']:
        print(f"Home Team Actual:")
        print(f"  Pace: {actual['home']['pace']}")
        print(f"  FG%: {actual['home']['fg_pct']}")
        print(f"  3PA: {actual['home']['fg3a']}")
        print(f"  3P%: {actual['home']['fg3_pct']}")
        print(f"  FTA: {actual['home']['fta']}")
        print(f"  Rebounds: {actual['home']['reb']}")
        print(f"  Assists: {actual['home']['assists']}")
        print(f"  Turnovers: {actual['home']['turnovers']}")
        print(f"  Paint Points: {actual['home']['paint_points']}")
    else:
        print("  No actual game data found (game may not have been played yet)")

    print("\n" + "=" * 80)
