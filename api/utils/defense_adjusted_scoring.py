"""
Defense-Adjusted Scoring Module

Adjusts team scoring projections based on opponent's defensive tier and game location.
Uses the defense-adjusted scoring splits to provide context-aware predictions.
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Import database utilities
try:
    from api.utils.db_config import get_db_path
    from api.utils.defense_tiers import get_defense_tier
except ImportError:
    from db_config import get_db_path
    from defense_tiers import get_defense_tier

import sqlite3

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_defense_adjusted_ppg(
    team_id: int,
    opponent_def_rank: Optional[int],
    is_home: bool,
    season: str = '2025-26',
    fallback_ppg: Optional[float] = None
) -> Tuple[Optional[float], str]:
    """
    Get defense-adjusted PPG for a team based on opponent's defensive tier and location.

    Args:
        team_id: Team's ID
        opponent_def_rank: Opponent's defensive rating rank (1-30)
        is_home: True if team is playing at home
        season: Season string
        fallback_ppg: Fallback PPG if no split data available

    Returns:
        Tuple of (adjusted_ppg, data_quality)
        - adjusted_ppg: PPG for this specific context, or fallback if unavailable
        - data_quality: 'excellent' (3+ games), 'limited' (<3 games), or 'fallback' (no data)
    """
    if opponent_def_rank is None:
        logger.warning(f"No opponent def_rank provided for team {team_id}")
        return (fallback_ppg, 'fallback')

    # Determine defense tier
    defense_tier = get_defense_tier(opponent_def_rank)
    if defense_tier is None:
        logger.warning(f"Invalid opponent def_rank: {opponent_def_rank}")
        return (fallback_ppg, 'fallback')

    location = 'home' if is_home else 'away'

    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch game logs for this team
        cursor.execute('''
            SELECT
                tgl.team_pts,
                tss_opp.def_rtg_rank
            FROM team_game_logs tgl
            LEFT JOIN team_season_stats tss_opp
                ON tgl.opponent_team_id = tss_opp.team_id
                AND tgl.season = tss_opp.season
                AND tss_opp.split_type = 'overall'
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                AND tgl.is_home = ?
                AND tgl.team_pts IS NOT NULL
        ''', (team_id, season, 1 if is_home else 0))

        games = cursor.fetchall()

        # Filter games by defense tier
        tier_games = []
        for game in games:
            game_def_rank = game['def_rtg_rank']
            if game_def_rank is None:
                continue

            game_tier = get_defense_tier(game_def_rank)
            if game_tier == defense_tier:
                tier_games.append(game['team_pts'])

        conn.close()

        # Calculate average if we have games
        if len(tier_games) >= 3:
            # Excellent data quality - 3+ games
            avg_ppg = sum(tier_games) / len(tier_games)
            logger.info(
                f"Team {team_id} {location} vs {defense_tier}: {avg_ppg:.1f} PPG "
                f"({len(tier_games)} games) - excellent quality"
            )
            return (avg_ppg, 'excellent')

        elif len(tier_games) > 0:
            # Limited data quality - some games but <3
            avg_ppg = sum(tier_games) / len(tier_games)
            logger.info(
                f"Team {team_id} {location} vs {defense_tier}: {avg_ppg:.1f} PPG "
                f"({len(tier_games)} games) - limited quality, using with caution"
            )
            return (avg_ppg, 'limited')

        else:
            # No data - use fallback
            logger.info(
                f"Team {team_id} {location} vs {defense_tier}: No games, using fallback"
            )
            return (fallback_ppg, 'fallback')

    except Exception as e:
        logger.error(f"Error getting defense-adjusted PPG for team {team_id}: {e}")
        conn.close()
        return (fallback_ppg, 'fallback')


def calculate_defense_adjusted_score(
    team_id: int,
    opponent_def_rank: Optional[int],
    is_home: bool,
    baseline_ppg: float,
    season: str = '2025-26',
    adjustment_weight: float = 0.4,
    season_ppg: Optional[float] = None
) -> Dict:
    """
    Calculate defense-adjusted score with blending of baseline and context-specific scoring.

    Args:
        team_id: Team's ID
        opponent_def_rank: Opponent's defensive rating rank
        is_home: True if playing at home
        baseline_ppg: Baseline PPG from traditional calculation
        season: Season string
        adjustment_weight: Weight for defense-adjusted value (0-1)
                          0 = ignore defense adjustment, 1 = full defense adjustment
        season_ppg: Team's season average PPG (for safety check)

    Returns:
        Dict with:
        - adjusted_ppg: Final blended PPG
        - context_ppg: Defense-adjusted context PPG (or None)
        - baseline_ppg: Original baseline
        - adjustment: Amount adjusted from baseline
        - data_quality: Quality of context data
        - explanation: Human-readable explanation
    """
    # Get defense-adjusted PPG
    context_ppg, data_quality = get_defense_adjusted_ppg(
        team_id=team_id,
        opponent_def_rank=opponent_def_rank,
        is_home=is_home,
        season=season,
        fallback_ppg=baseline_ppg
    )

    # Determine blending weight based on data quality
    if data_quality == 'excellent':
        # Use full adjustment weight for high-quality data
        blend_weight = adjustment_weight

        # SAFETY CHECK: If context_ppg is significantly lower than season average,
        # reduce blend weight to avoid over-penalizing (cap at -10 PPG difference)
        if season_ppg and context_ppg and context_ppg < season_ppg - 10:
            logger.warning(
                f"Team {team_id} context PPG ({context_ppg:.1f}) is {season_ppg - context_ppg:.1f} pts "
                f"below season avg ({season_ppg:.1f}). Reducing blend weight to 0.6"
            )
            blend_weight = adjustment_weight * 0.6

    elif data_quality == 'limited':
        # Reduce weight significantly for limited data (< 3 games)
        blend_weight = adjustment_weight * 0.3  # Reduced from 0.5 to 0.3
        logger.info(f"Team {team_id} has limited data quality, using {blend_weight:.2f} blend weight")
    else:  # fallback
        # No adjustment if no data
        blend_weight = 0.0

    # Blend baseline with context-specific PPG
    if context_ppg is not None and blend_weight > 0:
        adjusted_ppg = baseline_ppg * (1 - blend_weight) + context_ppg * blend_weight
        adjustment = adjusted_ppg - baseline_ppg
    else:
        adjusted_ppg = baseline_ppg
        adjustment = 0.0

    # Build explanation
    location = 'home' if is_home else 'away'
    if opponent_def_rank:
        tier = get_defense_tier(opponent_def_rank)
        tier_label = {
            'elite': 'elite defense',
            'average': 'average defense',
            'bad': 'bad defense'
        }.get(tier, 'unknown defense')
    else:
        tier_label = 'unknown defense'

    if data_quality == 'excellent':
        explanation = (
            f"High-quality context adjustment: {location} vs {tier_label} "
            f"(context: {context_ppg:.1f} PPG, baseline: {baseline_ppg:.1f} PPG, "
            f"adjusted: {adjustment:+.1f} pts)"
        )
    elif data_quality == 'limited':
        explanation = (
            f"Limited context adjustment: {location} vs {tier_label} "
            f"(context: {context_ppg:.1f} PPG with limited games, "
            f"adjusted: {adjustment:+.1f} pts)"
        )
    else:
        explanation = (
            f"No context-specific data available for {location} vs {tier_label}, "
            f"using baseline projection"
        )

    return {
        'adjusted_ppg': adjusted_ppg,
        'context_ppg': context_ppg,
        'baseline_ppg': baseline_ppg,
        'adjustment': adjustment,
        'data_quality': data_quality,
        'explanation': explanation,
        'location': location,
        'opponent_tier': tier_label if opponent_def_rank else None,
    }
