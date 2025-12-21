"""
Scoring Compression and Bias Correction

This module prevents prediction inflation when multiple high-scoring signals stack.
It also recalibrates baselines to reduce inherent bias toward high totals.
"""

from typing import Dict, Tuple, Optional


def calculate_signal_stacking_compression(
    pace_signal: str,
    offense_signal: str,
    three_pt_signal: str,
    defense_signal: str
) -> float:
    """
    When multiple signals point to high scoring, apply compression.

    Signals:
    - pace_signal: 'high', 'normal', 'low'
    - offense_signal: 'strong', 'normal', 'weak'
    - three_pt_signal: 'hot', 'normal', 'cold'
    - defense_signal: 'weak', 'normal', 'strong'

    Returns:
        Compression factor (0.92-1.0)
    """
    high_scoring_count = 0

    # Count high-scoring indicators
    if pace_signal == 'high':
        high_scoring_count += 1
    if offense_signal == 'strong':
        high_scoring_count += 1
    if three_pt_signal == 'hot':
        high_scoring_count += 1
    if defense_signal == 'weak':
        high_scoring_count += 1

    # Apply compression based on stacking
    if high_scoring_count >= 4:
        # All signals say high scoring - likely over-inflated
        return 0.94
    elif high_scoring_count == 3:
        # Three signals - moderate compression
        return 0.97
    elif high_scoring_count <= 1:
        # Low scoring scenario - no compression needed
        return 1.0
    else:
        return 0.99


def identify_low_tempo_high_defense_matchup(
    game_pace: float,
    home_drtg_rank: Optional[int],
    away_drtg_rank: Optional[int]
) -> Tuple[bool, float]:
    """
    Identify games that will be low-scoring defensive battles.

    Returns:
        (is_defensive_battle, cap_factor)
    """
    # Low tempo threshold
    is_low_tempo = game_pace < 98.0

    # Both teams strong defensively
    both_strong_defense = (
        home_drtg_rank is not None and
        away_drtg_rank is not None and
        home_drtg_rank <= 12 and
        away_drtg_rank <= 12
    )

    if is_low_tempo and both_strong_defense:
        # Defensive battle - cap scoring
        return (True, 0.95)
    elif is_low_tempo or both_strong_defense:
        # One indicator - mild cap
        return (True, 0.98)
    else:
        return (False, 1.0)


def calculate_historical_underperformance_factor(
    home_vs_strong_def: Optional[Dict],
    away_vs_strong_def: Optional[Dict],
    opp_home_drtg_rank: Optional[int],
    opp_away_drtg_rank: Optional[int]
) -> float:
    """
    If both teams historically underperform vs strong defenses,
    and they're facing strong defenses, apply a dampener.

    Args:
        home_vs_strong_def: Home team's performance vs top-15 defenses
        away_vs_strong_def: Away team's performance vs top-15 defenses
        opp_home_drtg_rank: Away team's defensive rank (opponent for home)
        opp_away_drtg_rank: Home team's defensive rank (opponent for away)

    Returns:
        Dampening factor (0.94-1.0)
    """
    dampener = 1.0

    # Check if home team underperforms vs strong defenses
    if (home_vs_strong_def and
        opp_home_drtg_rank and
        opp_home_drtg_rank <= 15 and
        home_vs_strong_def.get('avg_ppg', 999) < home_vs_strong_def.get('season_avg', 999)):
        dampener *= 0.97

    # Check if away team underperforms vs strong defenses
    if (away_vs_strong_def and
        opp_away_drtg_rank and
        opp_away_drtg_rank <= 15 and
        away_vs_strong_def.get('avg_ppg', 999) < away_vs_strong_def.get('season_avg', 999)):
        dampener *= 0.97

    return dampener


def apply_baseline_recalibration(
    baseline_ppg: float,
    recent_ppg: float,
    contextual_ppg: Optional[float],
    opp_drtg_rank: Optional[int],
    pace_factor: float
) -> float:
    """
    Recalibrate baseline using a blend of:
    - Season average
    - Recent form
    - Contextual splits vs similar opponents
    - Opponent defensive strength

    This replaces simple averaging with smarter blending.

    Args:
        baseline_ppg: Current baseline (season + recent blend)
        recent_ppg: Recent form PPG
        contextual_ppg: PPG vs similar opponents
        opp_drtg_rank: Opponent's defensive rank
        pace_factor: Projected pace multiplier

    Returns:
        Recalibrated baseline
    """
    # Start with current baseline
    weights = {'baseline': 0.5}

    # Add contextual split if available
    if contextual_ppg is not None:
        weights['contextual'] = 0.25
        weights['baseline'] = 0.4
        weights['recent'] = 0.35
    else:
        weights['recent'] = 0.5

    # Calculate weighted baseline
    recalibrated = baseline_ppg * weights['baseline']

    if 'recent' in weights:
        recalibrated += recent_ppg * weights['recent']

    if 'contextual' in weights and contextual_ppg is not None:
        recalibrated += contextual_ppg * weights['contextual']

    # Apply defensive adjustment
    if opp_drtg_rank is not None:
        if opp_drtg_rank <= 5:
            # Elite defense - reduce baseline
            recalibrated *= 0.95
        elif opp_drtg_rank <= 10:
            recalibrated *= 0.97
        elif opp_drtg_rank >= 25:
            # Weak defense - slight increase
            recalibrated *= 1.02

    return recalibrated


def calculate_total_compression_factor(
    home_projected: float,
    away_projected: float,
    betting_line: Optional[float],
    pace_volatility_home: float,
    pace_volatility_away: float,
    defensive_battle: bool
) -> Tuple[float, str]:
    """
    Master compression calculator that combines all factors.

    Returns:
        (compression_factor, reason)
    """
    compression = 1.0
    reasons = []

    projected_total = home_projected + away_projected

    # Factor 1: Projection significantly above betting line
    if betting_line is not None:
        diff = projected_total - betting_line
        if diff > 8.0:
            compression *= 0.96
            reasons.append('proj_much_higher_than_line')
        elif diff > 5.0:
            compression *= 0.98
            reasons.append('proj_higher_than_line')

    # Factor 2: High pace volatility
    avg_volatility = (pace_volatility_home + pace_volatility_away) / 2
    if avg_volatility < 0.92:
        compression *= 0.97
        reasons.append('high_pace_volatility')

    # Factor 3: Defensive battle
    if defensive_battle:
        compression *= 0.97
        reasons.append('defensive_battle')

    # Factor 4: Extremely high projection (>240)
    if projected_total > 240:
        compression *= 0.96
        reasons.append('extreme_high_total')
    elif projected_total > 235:
        compression *= 0.98
        reasons.append('very_high_total')

    reason_str = ', '.join(reasons) if reasons else 'no_compression'

    return (compression, reason_str)
