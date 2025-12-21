"""
Enhanced Defensive Adjustments

This module provides more aggressive defensive adjustments to prevent over-prediction:
- DRTG tier-based multipliers
- Recent defensive trend analysis
- Matchup-specific defensive performance
"""

import sqlite3
import os
from typing import Dict, Optional, Tuple


def get_db_path(db_name='nba_data.db'):
    """Get the path to the database file"""
    return os.path.join(os.path.dirname(__file__), '..', 'data', db_name)


def get_defensive_multiplier(drtg_rank: Optional[int], recent_drtg_trend: float = 0.0) -> Tuple[float, str]:
    """
    Calculate aggressive defensive multiplier based on DRTG rank and recent trend.

    This is MORE aggressive than previous logic to combat over-prediction.

    Args:
        drtg_rank: Defensive rating rank (1-30, where 1 is best)
        recent_drtg_trend: Recent DRTG change (negative = improving defense)

    Returns:
        (multiplier, tier_name)
        multiplier < 1.0 = reduce opponent scoring
    """
    if drtg_rank is None:
        return (1.0, 'unknown')

    # Base tier multipliers (MORE AGGRESSIVE)
    if drtg_rank <= 5:
        # Elite top-5 defense
        base_mult = 0.91  # Reduce opponent scoring by 9%
        tier = 'elite_top5'
    elif drtg_rank <= 10:
        # Elite defense
        base_mult = 0.94  # Reduce by 6%
        tier = 'elite'
    elif drtg_rank <= 15:
        # Above average
        base_mult = 0.97  # Reduce by 3%
        tier = 'above_avg'
    elif drtg_rank <= 20:
        # Average
        base_mult = 0.99  # Reduce by 1%
        tier = 'average'
    elif drtg_rank <= 25:
        # Below average
        base_mult = 1.01  # Slight increase
        tier = 'below_avg'
    else:
        # Weak defense
        base_mult = 1.03  # Increase by 3%
        tier = 'weak'

    # Apply recent trend modifier
    # If defense improving (negative trend), make multiplier more strict
    if recent_drtg_trend < -1.5:
        # Defense improving significantly
        trend_adj = 0.97
    elif recent_drtg_trend < -0.5:
        # Defense improving
        trend_adj = 0.99
    elif recent_drtg_trend > 1.5:
        # Defense declining
        trend_adj = 1.02
    elif recent_drtg_trend > 0.5:
        # Defense declining slightly
        trend_adj = 1.01
    else:
        trend_adj = 1.0

    final_mult = base_mult * trend_adj

    return (final_mult, tier)


def calculate_recent_defensive_trend(team_id: int, season: str = '2025-26', n_games: int = 5) -> float:
    """
    Calculate recent defensive rating trend.

    Returns:
        DRTG change (negative = defense improving)

    NOTE: Uses 'def_rtg' from team_season_stats and 'def_rating' from team_game_logs
    """
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get season DRTG from team_season_stats (uses 'def_rtg' column)
        cursor.execute('''
            SELECT def_rtg
            FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = 'overall'
        ''', (team_id, season))

        season_row = cursor.fetchone()

        # Get recent games DRTG from team_game_logs (uses 'def_rating' column)
        cursor.execute('''
            SELECT AVG(def_rating) as recent_drtg
            FROM team_game_logs
            WHERE team_id = ? AND season = ? AND def_rating IS NOT NULL
            ORDER BY game_date DESC
            LIMIT ?
        ''', (team_id, season, n_games))

        recent_row = cursor.fetchone()
        conn.close()

        if not season_row or not recent_row:
            return 0.0

        season_drtg = season_row['def_rtg']
        recent_drtg = recent_row['recent_drtg']

        if season_drtg is None or recent_drtg is None:
            return 0.0

        # Return the change (negative = improving)
        return recent_drtg - season_drtg

    except Exception as e:
        # If defensive stats unavailable, return neutral (no trend)
        print(f'[enhanced_defense] Warning: Could not calculate defensive trend for team {team_id}: {e}')
        return 0.0


def get_matchup_defensive_performance(
    defender_team_id: int,
    offense_team_id: int,
    season: str = '2025-26'
) -> Optional[float]:
    """
    Get how well this defense has performed vs this specific offense.

    Returns:
        Points allowed per game vs this opponent (or None if no history)
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get points allowed by defender when facing this offense
    cursor.execute('''
        SELECT AVG(tgl_opp.team_pts) as avg_pts_allowed
        FROM team_game_logs tgl_def
        JOIN team_game_logs tgl_opp ON tgl_def.game_id = tgl_opp.game_id
        WHERE tgl_def.team_id = ?
          AND tgl_opp.team_id = ?
          AND tgl_def.season = ?
          AND tgl_opp.team_pts IS NOT NULL
    ''', (defender_team_id, offense_team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row or row['avg_pts_allowed'] is None:
        return None

    return row['avg_pts_allowed']


def apply_double_strong_defense_penalty(
    home_drtg_rank: Optional[int],
    away_drtg_rank: Optional[int],
    home_projected: float,
    away_projected: float
) -> Tuple[float, float, bool]:
    """
    When BOTH teams have strong defenses, apply an additional dampening factor.

    This prevents over-prediction in defensive slugfests.

    Args:
        home_drtg_rank: Home team defensive rank
        away_drtg_rank: Away team defensive rank
        home_projected: Current home projection
        away_projected: Current away projection

    Returns:
        (adjusted_home, adjusted_away, penalty_applied)
    """
    if home_drtg_rank is None or away_drtg_rank is None:
        return (home_projected, away_projected, False)

    # Both teams have top-15 defenses
    if home_drtg_rank <= 15 and away_drtg_rank <= 15:
        # Apply additional 2% reduction to each team
        penalty = 0.98
        return (
            home_projected * penalty,
            away_projected * penalty,
            True
        )

    # Both teams have top-10 defenses (very rare, very defensive)
    if home_drtg_rank <= 10 and away_drtg_rank <= 10:
        # Apply additional 4% reduction
        penalty = 0.96
        return (
            home_projected * penalty,
            away_projected * penalty,
            True
        )

    return (home_projected, away_projected, False)


def calculate_defense_vs_offense_strength_factor(
    offense_ortg_rank: Optional[int],
    defense_drtg_rank: Optional[int]
) -> float:
    """
    When a weak offense faces a strong defense, reduce scoring even more.
    When a strong offense faces a weak defense, allow normal scoring.

    Returns:
        Multiplier (typically 0.92-1.02)
    """
    if offense_ortg_rank is None or defense_drtg_rank is None:
        return 1.0

    # Weak offense (rank 20+) vs strong defense (rank 1-10)
    if offense_ortg_rank >= 20 and defense_drtg_rank <= 10:
        return 0.93  # Further reduce weak offense vs strong defense

    # Weak offense vs average defense
    if offense_ortg_rank >= 20 and defense_drtg_rank <= 15:
        return 0.96

    # Strong offense (rank 1-10) vs weak defense (rank 20+)
    if offense_ortg_rank <= 10 and defense_drtg_rank >= 20:
        return 1.02  # Allow slightly more scoring

    return 1.0
