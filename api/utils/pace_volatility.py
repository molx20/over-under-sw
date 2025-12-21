"""
Pace Volatility and Contextual Pace Analysis

This module provides granular pace metrics to improve prediction accuracy:
- Recent pace volatility (standard deviation)
- Opponent-specific pace adjustments
- Contextual pace factors (turnovers, FT rate, defensive pressure)
"""

import sqlite3
import os
from typing import Dict, Optional, Tuple
import statistics


def get_db_path(db_name='nba_data.db'):
    """Get the path to the database file"""
    return os.path.join(os.path.dirname(__file__), '..', 'data', db_name)


def calculate_pace_volatility(team_id: int, season: str = '2025-26', n_games: int = 10) -> Dict:
    """
    Calculate pace volatility for a team based on recent games.

    High volatility indicates inconsistent game tempo, which should reduce
    confidence in pace-based scoring projections.

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')
        n_games: Number of recent games to analyze

    Returns:
        {
            'avg_pace': float,
            'std_dev': float,
            'volatility_factor': float,  # 1.0 = normal, <1.0 = high volatility (dampening)
            'games_analyzed': int
        }
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get recent game paces
    cursor.execute('''
        SELECT game_pace
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND game_pace IS NOT NULL
        ORDER BY game_date DESC
        LIMIT ?
    ''', (team_id, season, n_games))

    rows = cursor.fetchall()
    conn.close()

    if not rows or len(rows) < 3:
        return {
            'avg_pace': None,
            'std_dev': None,
            'volatility_factor': 1.0,
            'games_analyzed': len(rows)
        }

    paces = [row['game_pace'] for row in rows]
    avg_pace = statistics.mean(paces)
    std_dev = statistics.stdev(paces) if len(paces) > 1 else 0.0

    # Calculate volatility factor
    # If std_dev > 3.0, it's high volatility → dampen pace impact
    # If std_dev < 1.5, it's low volatility → trust pace more
    if std_dev > 3.5:
        volatility_factor = 0.85  # High volatility, reduce pace confidence
    elif std_dev > 2.5:
        volatility_factor = 0.92
    elif std_dev < 1.5:
        volatility_factor = 1.05  # Low volatility, trust pace slightly more
    else:
        volatility_factor = 1.0  # Normal

    return {
        'avg_pace': avg_pace,
        'std_dev': std_dev,
        'volatility_factor': volatility_factor,
        'games_analyzed': len(paces)
    }


def get_opponent_pace_impact(team_id: int, opp_team_id: int, season: str = '2025-26') -> Optional[float]:
    """
    Calculate how a team's pace changes when facing this specific opponent.

    Returns:
        Pace adjustment factor (e.g., 0.97 = slower, 1.03 = faster)
        None if no historical data
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get team's average pace vs this opponent
    cursor.execute('''
        SELECT AVG(game_pace) as avg_pace_vs_opp
        FROM team_game_logs
        WHERE team_id = ? AND opp_team_id = ? AND season = ?
          AND game_pace IS NOT NULL
    ''', (team_id, opp_team_id, season))

    opp_row = cursor.fetchone()

    # Get team's overall average pace
    cursor.execute('''
        SELECT AVG(game_pace) as avg_pace_overall
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND game_pace IS NOT NULL
    ''', (team_id, season))

    overall_row = cursor.fetchone()
    conn.close()

    if not opp_row or not overall_row:
        return None

    pace_vs_opp = opp_row['avg_pace_vs_opp']
    pace_overall = overall_row['avg_pace_overall']

    if pace_vs_opp is None or pace_overall is None or pace_overall == 0:
        return None

    # Return the ratio (e.g., 98/100 = 0.98 = slower vs this opponent)
    return pace_vs_opp / pace_overall


def calculate_contextual_pace_dampener(
    home_stats: Dict,
    away_stats: Dict,
    home_volatility: Dict,
    away_volatility: Dict
) -> float:
    """
    Calculate a pace dampening factor based on contextual factors:
    - High turnover teams (more stoppages)
    - High FT rate teams (more clock stoppages)
    - Both teams with high pace volatility (unpredictable)

    Returns:
        Dampening factor (0.90-1.0, where <1.0 reduces pace-based scoring)
    """
    dampener = 1.0

    # Factor 1: High turnover rate
    home_tov_pct = home_stats.get('overall', {}).get('TOV_PCT', 0) or 0
    away_tov_pct = away_stats.get('overall', {}).get('TOV_PCT', 0) or 0
    avg_tov_pct = (home_tov_pct + away_tov_pct) / 2

    if avg_tov_pct > 14.5:  # High turnover game
        dampener *= 0.97

    # Factor 2: High FT rate (more stoppages)
    home_ftr = home_stats.get('overall', {}).get('FTA_RATE', 0) or 0
    away_ftr = away_stats.get('overall', {}).get('FTA_RATE', 0) or 0
    avg_ftr = (home_ftr + away_ftr) / 2

    if avg_ftr > 0.28:  # High FT rate
        dampener *= 0.96

    # Factor 3: Both teams have high pace volatility
    home_vol_factor = home_volatility.get('volatility_factor', 1.0)
    away_vol_factor = away_volatility.get('volatility_factor', 1.0)

    if home_vol_factor < 0.95 and away_vol_factor < 0.95:
        # Both teams highly volatile
        dampener *= 0.94

    return max(dampener, 0.90)  # Don't go below 0.90


def get_defensive_pace_pressure(team_id: int, season: str = '2025-26') -> float:
    """
    Calculate how much a team's defense slows down opponents.

    Returns:
        Pace pressure factor (e.g., 0.96 = slows opponents by 4%)
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get opponent pace when facing this team
    cursor.execute('''
        SELECT AVG(tgl2.game_pace) as opp_pace_vs_us
        FROM team_game_logs tgl1
        JOIN team_game_logs tgl2 ON tgl1.game_id = tgl2.game_id
        WHERE tgl1.team_id = ? AND tgl2.team_id != ?
          AND tgl1.season = ? AND tgl2.game_pace IS NOT NULL
    ''', (team_id, team_id, season))

    our_row = cursor.fetchone()

    # Get league average pace
    cursor.execute('''
        SELECT AVG(game_pace) as league_avg_pace
        FROM team_game_logs
        WHERE season = ? AND game_pace IS NOT NULL
    ''', (season,))

    league_row = cursor.fetchone()
    conn.close()

    if not our_row or not league_row:
        return 1.0

    opp_pace_vs_us = our_row['opp_pace_vs_us']
    league_avg = league_row['league_avg_pace']

    if opp_pace_vs_us is None or league_avg is None or league_avg == 0:
        return 1.0

    # If opponents average 98 pace vs us but league avg is 100, we slow teams down
    return opp_pace_vs_us / league_avg
