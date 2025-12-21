"""
Team Contextual Profiles Module

Provides team-specific behavioral profiles based on opponent characteristics:
- Scoring vs defense tiers (Elite/Average/Weak)
- Scoring vs pace buckets (Slow/Normal/Fast)
- Head-to-head history vs specific opponents

These profiles enhance the smart baseline by using actual historical performance
instead of generic league-wide adjustments.

Usage:
    from api.utils.team_contextual_profiles import (
        get_team_scoring_vs_defense_tier,
        get_team_scoring_vs_pace_bucket,
        get_h2h_history
    )
"""

import sqlite3
from typing import Dict, Optional
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


def _determine_confidence(games: int) -> str:
    """
    Determine confidence level based on sample size.

    Args:
        games: Number of games in the sample

    Returns:
        "high", "medium", or "low"
    """
    if games >= 8:
        return "high"
    elif games >= 4:
        return "medium"
    else:
        return "low"


def get_team_scoring_vs_defense_tier(
    team_id: int,
    defense_tier: str,
    season: str = '2025-26'
) -> Optional[Dict]:
    """
    Get team's average scoring vs a specific defense tier.

    Defense Tiers:
    - "elite": Defensive rank 1-10
    - "average": Defensive rank 11-19
    - "weak": Defensive rank 20-30

    Args:
        team_id: Team ID
        defense_tier: "elite", "average", or "weak"
        season: Season string

    Returns:
        {
            "avg_ppg": float,
            "games": int,
            "confidence": "high" | "medium" | "low"
        }
        or None if no data
    """
    # Map tier to rank ranges
    tier_ranges = {
        "elite": (1, 10),
        "average": (11, 19),
        "weak": (20, 30)
    }

    if defense_tier not in tier_ranges:
        logger.warning(f"Invalid defense tier: {defense_tier}")
        return None

    min_rank, max_rank = tier_ranges[defense_tier]

    conn = _get_db_connection()
    cursor = conn.cursor()

    # Query: Get games where this team faced opponents in this defense tier
    # We need to join team_game_logs with opponent's season stats to get their drtg_rank
    query = """
        SELECT
            AVG(tgl.team_pts) as avg_ppg,
            COUNT(*) as games
        FROM team_game_logs tgl
        INNER JOIN (
            SELECT team_id, drtg_rank
            FROM team_season_stats
            WHERE season = ? AND split_type = 'overall'
        ) opp_stats ON tgl.opp_team_id = opp_stats.team_id
        WHERE tgl.team_id = ?
          AND tgl.season = ?
          AND opp_stats.drtg_rank BETWEEN ? AND ?
    """

    cursor.execute(query, (season, team_id, season, min_rank, max_rank))
    row = cursor.fetchone()
    conn.close()

    if row and row['games'] > 0:
        games = row['games']
        return {
            "avg_ppg": round(row['avg_ppg'], 1),
            "games": games,
            "confidence": _determine_confidence(games)
        }

    return None


def get_team_scoring_vs_pace_bucket(
    team_id: int,
    pace_bucket: str,
    season: str = '2025-26'
) -> Optional[Dict]:
    """
    Get team's average scoring in games with specific pace characteristics.

    Pace Buckets:
    - "slow": game_pace < 97
    - "normal": 97 <= game_pace <= 103
    - "fast": game_pace > 103

    Args:
        team_id: Team ID
        pace_bucket: "slow", "normal", or "fast"
        season: Season string

    Returns:
        {
            "avg_ppg": float,
            "games": int,
            "confidence": "high" | "medium" | "low"
        }
        or None if no data
    """
    # Map bucket to pace ranges
    pace_conditions = {
        "slow": "game_pace < 97",
        "normal": "game_pace BETWEEN 97 AND 103",
        "fast": "game_pace > 103"
    }

    if pace_bucket not in pace_conditions:
        logger.warning(f"Invalid pace bucket: {pace_bucket}")
        return None

    pace_condition = pace_conditions[pace_bucket]

    conn = _get_db_connection()
    cursor = conn.cursor()

    # Query: Get games where this team played in this pace bucket
    query = f"""
        SELECT
            AVG(team_pts) as avg_ppg,
            COUNT(*) as games
        FROM team_game_logs
        WHERE team_id = ?
          AND season = ?
          AND {pace_condition}
    """

    cursor.execute(query, (team_id, season))
    row = cursor.fetchone()
    conn.close()

    if row and row['games'] > 0:
        games = row['games']
        return {
            "avg_ppg": round(row['avg_ppg'], 1),
            "games": games,
            "confidence": _determine_confidence(games)
        }

    return None


def get_h2h_history(
    home_team_id: int,
    away_team_id: int,
    season: str = '2025-26'
) -> Optional[Dict]:
    """
    Get head-to-head history between two teams this season.

    Args:
        home_team_id: Home team ID
        away_team_id: Away team ID
        season: Season string

    Returns:
        {
            "games": int,
            "avg_total": float,
            "avg_home_score": float,
            "avg_away_score": float
        }
        or None if no H2H games found
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Query: Find all games this season where these two teams played
    # We need to check both directions (home/away)
    query = """
        SELECT
            tg.game_id,
            tg.home_team_id,
            tg.away_team_id,
            tg.home_score,
            tg.away_score,
            (tg.home_score + tg.away_score) as total
        FROM todays_games tg
        WHERE tg.season = ?
          AND tg.status = 'final'
          AND (
              (tg.home_team_id = ? AND tg.away_team_id = ?)
              OR
              (tg.home_team_id = ? AND tg.away_team_id = ?)
          )
          AND tg.home_score IS NOT NULL
          AND tg.away_score IS NOT NULL
    """

    cursor.execute(query, (season, home_team_id, away_team_id, away_team_id, home_team_id))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    games = len(rows)
    total_sum = 0
    home_score_sum = 0
    away_score_sum = 0

    for row in rows:
        total_sum += row['total']

        # Normalize to current matchup's perspective (home_team_id as home)
        if row['home_team_id'] == home_team_id:
            home_score_sum += row['home_score']
            away_score_sum += row['away_score']
        else:
            # Flip if the matchup was reversed
            home_score_sum += row['away_score']
            away_score_sum += row['home_score']

    return {
        "games": games,
        "avg_total": round(total_sum / games, 1),
        "avg_home_score": round(home_score_sum / games, 1),
        "avg_away_score": round(away_score_sum / games, 1)
    }


def blend_baseline(generic_baseline: float, contextual_data: Optional[Dict]) -> float:
    """
    Blend generic baseline with contextual data based on confidence level.

    Args:
        generic_baseline: Base PPG from season/recent blend
        contextual_data: Result from get_team_scoring_vs_* functions

    Returns:
        Blended baseline PPG
    """
    if contextual_data is None or contextual_data["games"] < 4:
        return generic_baseline

    # Determine blending weight based on confidence
    if contextual_data["confidence"] == "high":
        weight_context = 0.35  # 35% contextual, 65% generic
    elif contextual_data["confidence"] == "medium":
        weight_context = 0.20  # 20% contextual, 80% generic
    else:
        weight_context = 0.0  # No blending for low confidence

    blended = generic_baseline * (1 - weight_context) + contextual_data["avg_ppg"] * weight_context

    logger.debug(
        f"Baseline blending: generic={generic_baseline:.1f}, "
        f"contextual={contextual_data['avg_ppg']:.1f} ({contextual_data['games']} games, "
        f"{contextual_data['confidence']} conf) → blended={blended:.1f}"
    )

    return blended
