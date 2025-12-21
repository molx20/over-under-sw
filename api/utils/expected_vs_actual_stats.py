"""
Expected vs Actual Stats Calculator

This module computes expected stat values from season averages and actual values
from game box scores for the AI Model Coach.

It provides deterministic, rule-based stat expectations without changing the core
prediction engine.
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def compute_expected_pace(
    home_season_pace: Optional[float],
    away_season_pace: Optional[float]
) -> Optional[float]:
    """
    Compute expected game pace from team season averages.

    Simple average of both teams' season pace.

    Args:
        home_season_pace: Home team's season pace average
        away_season_pace: Away team's season pace average

    Returns:
        Expected game pace, or None if data missing
    """
    if home_season_pace is None or away_season_pace is None:
        return None

    return (home_season_pace + away_season_pace) / 2.0


def compute_expected_fta(
    home_season_fta: Optional[float],
    away_season_fta: Optional[float]
) -> Optional[float]:
    """
    Compute expected combined free throw attempts.

    Simple sum of both teams' season FTA averages.

    Args:
        home_season_fta: Home team's season FTA per game
        away_season_fta: Away team's season FTA per game

    Returns:
        Expected combined FTA for the game, or None if data missing
    """
    if home_season_fta is None or away_season_fta is None:
        return None

    return home_season_fta + away_season_fta


def compute_expected_turnovers(
    home_season_tov: Optional[float],
    away_season_tov: Optional[float]
) -> Optional[float]:
    """
    Compute expected combined turnovers.

    Simple sum of both teams' season turnover averages.

    Args:
        home_season_tov: Home team's season turnovers per game
        away_season_tov: Away team's season turnovers per game

    Returns:
        Expected combined turnovers for the game, or None if data missing
    """
    if home_season_tov is None or away_season_tov is None:
        return None

    return home_season_tov + away_season_tov


def compute_expected_3pa(
    home_season_3pa: Optional[float],
    away_season_3pa: Optional[float]
) -> Optional[float]:
    """
    Compute expected combined 3-point attempts.

    Simple sum of both teams' season 3PA averages.

    Args:
        home_season_3pa: Home team's season 3PA per game
        away_season_3pa: Away team's season 3PA per game

    Returns:
        Expected combined 3PA for the game, or None if data missing
    """
    if home_season_3pa is None or away_season_3pa is None:
        return None

    return home_season_3pa + away_season_3pa


def compute_actual_stats_from_box_scores(
    home_box_score: Optional[Dict],
    away_box_score: Optional[Dict]
) -> Dict[str, Optional[float]]:
    """
    Extract actual game stats from box scores.

    Args:
        home_box_score: Home team box score dict
        away_box_score: Away team box score dict

    Returns:
        Dict with:
            - actual_pace: Game pace (from home or away box score)
            - actual_fta_total: Combined FTA
            - actual_turnovers_total: Combined turnovers
            - actual_3pa_total: Combined 3PA
    """
    result = {
        'actual_pace': None,
        'actual_fta_total': None,
        'actual_turnovers_total': None,
        'actual_3pa_total': None
    }

    if not home_box_score and not away_box_score:
        return result

    # Get pace (should be same for both teams, prefer home)
    if home_box_score and home_box_score.get('pace') is not None:
        result['actual_pace'] = home_box_score['pace']
    elif away_box_score and away_box_score.get('pace') is not None:
        result['actual_pace'] = away_box_score['pace']

    # Compute combined stats
    home_fta = home_box_score.get('fta') if home_box_score else None
    away_fta = away_box_score.get('fta') if away_box_score else None
    if home_fta is not None and away_fta is not None:
        result['actual_fta_total'] = home_fta + away_fta

    home_tov = home_box_score.get('turnovers') if home_box_score else None
    away_tov = away_box_score.get('turnovers') if away_box_score else None
    if home_tov is not None and away_tov is not None:
        result['actual_turnovers_total'] = home_tov + away_tov

    home_3pa = home_box_score.get('fg3a') if home_box_score else None
    away_3pa = away_box_score.get('fg3a') if away_box_score else None
    if home_3pa is not None and away_3pa is not None:
        result['actual_3pa_total'] = home_3pa + away_3pa

    return result


def compute_all_expected_vs_actual(
    team_season_stats: Optional[Dict],
    home_box_score: Optional[Dict],
    away_box_score: Optional[Dict],
    predicted_pace: Optional[float] = None
) -> Dict[str, Optional[float]]:
    """
    Compute all expected vs actual stats for AI Coach.

    This is the main entry point that computes all stat comparisons.

    Args:
        team_season_stats: Dict with 'home' and 'away' season stats
        home_box_score: Home team box score
        away_box_score: Away team box score
        predicted_pace: Optional predicted pace from prediction engine

    Returns:
        Dict with all expected/actual stat pairs:
            - expected_pace
            - actual_pace
            - expected_fta_total
            - actual_fta_total
            - expected_turnovers_total
            - actual_turnovers_total
            - expected_3pa_total
            - actual_3pa_total
    """
    result = {
        'expected_pace': None,
        'actual_pace': None,
        'expected_fta_total': None,
        'actual_fta_total': None,
        'expected_turnovers_total': None,
        'actual_turnovers_total': None,
        'expected_3pa_total': None,
        'actual_3pa_total': None
    }

    # Extract season stats
    home_stats = None
    away_stats = None
    if team_season_stats:
        home_stats = team_season_stats.get('home')
        away_stats = team_season_stats.get('away')

    # Compute expected values from season stats
    if home_stats and away_stats:
        # Extract values from nested structure (stats -> pace -> value)
        home_pace = home_stats.get('stats', {}).get('pace', {}).get('value')
        away_pace = away_stats.get('stats', {}).get('pace', {}).get('value')
        result['expected_pace'] = compute_expected_pace(home_pace, away_pace)

        # For FTA, TOV, 3PA we need to get from raw season data
        # These may not be in the current get_team_stats_with_ranks response
        # So we'll use predicted_pace if season pace calculation fails
        if result['expected_pace'] is None and predicted_pace is not None:
            result['expected_pace'] = predicted_pace

        # Extract per-game stats (these may need to be added to get_team_stats_with_ranks)
        home_fta = home_stats.get('stats', {}).get('fta', {}).get('value')
        away_fta = away_stats.get('stats', {}).get('fta', {}).get('value')
        result['expected_fta_total'] = compute_expected_fta(home_fta, away_fta)

        home_tov = home_stats.get('stats', {}).get('turnovers', {}).get('value')
        away_tov = away_stats.get('stats', {}).get('turnovers', {}).get('value')
        result['expected_turnovers_total'] = compute_expected_turnovers(home_tov, away_tov)

        home_3pa = home_stats.get('stats', {}).get('fg3a', {}).get('value')
        away_3pa = away_stats.get('stats', {}).get('fg3a', {}).get('value')
        result['expected_3pa_total'] = compute_expected_3pa(home_3pa, away_3pa)

    # Compute actual values from box scores
    actual_stats = compute_actual_stats_from_box_scores(home_box_score, away_box_score)
    result.update(actual_stats)

    # Log what we computed (format safely to avoid None errors)
    def safe_format(value, decimals=1):
        """Safely format a value or return N/A if None"""
        if value is None:
            return 'N/A'
        return f"{value:.{decimals}f}"

    logger.info(
        f"[Expected vs Actual] Computed stats | "
        f"exp_pace={safe_format(result['expected_pace'])} "
        f"act_pace={safe_format(result['actual_pace'])} | "
        f"exp_fta={safe_format(result['expected_fta_total'])} "
        f"act_fta={safe_format(result['actual_fta_total'], 0)} | "
        f"exp_tov={safe_format(result['expected_turnovers_total'])} "
        f"act_tov={safe_format(result['actual_turnovers_total'], 0)} | "
        f"exp_3pa={safe_format(result['expected_3pa_total'])} "
        f"act_3pa={safe_format(result['actual_3pa_total'], 0)}"
    )

    return result
