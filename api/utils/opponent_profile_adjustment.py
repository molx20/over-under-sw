"""
Opponent Profile Adjustment Layer

This module provides a DETERMINISTIC adjustment to predictions based on the
strength of opponents a team has recently faced.

**IMPORTANT**: This is NOT part of the learned feature system. The adjustment
logic uses hand-coded formulas and is never trained via gradient descent.

Use case:
- If a team's last 5 opponents were all high-pace, high-scoring teams,
  their recent stats may look inflated
- If they're about to face a slower, lower-scoring team, we adjust the
  prediction DOWN slightly to account for this context shift
- Vice versa: if they faced weak opponents and now face strong ones, adjust UP

The adjustment is capped at ±4 points to keep it reasonable and explainable.
"""

from typing import Dict
from api.utils.recent_form import get_last_n_opponents_avg_ranks


def compute_opponent_profile_adjustment(
    home_tricode: str,
    away_tricode: str,
    as_of_date: str,
    base_total: float,
    base_home: float,
    base_away: float
) -> Dict:
    """
    Compute deterministic adjustment based on opponent last-5 ranks

    This is a SEPARATE layer from learned features. The adjustment uses
    simple, hand-coded formulas to account for opponent strength context.

    Args:
        home_tricode: Home team abbreviation
        away_tricode: Away team abbreviation
        as_of_date: Date for "as of" queries (YYYY-MM-DD)
        base_total: Base prediction total (before this adjustment)
        base_home: Base prediction for home team
        base_away: Base prediction for away team

    Returns:
        Dict with:
            - adjustment: Total points adjustment (-4 to +4)
            - adjusted_total: base_total + adjustment
            - adjusted_home: Proportionally adjusted home score
            - adjusted_away: Proportionally adjusted away score
            - explanation: Human-readable explanation
            - details: Breakdown of factors

    Example:
        >>> compute_opponent_profile_adjustment('BOS', 'LAL', '2025-11-20', 223.5, 114.2, 109.3)
        {
            'adjustment': -2.3,
            'adjusted_total': 221.2,
            'adjusted_home': 113.1,
            'adjusted_away': 108.1,
            'explanation': 'BOS recent opponents (avg PPG rank: 8.2, Pace rank: 11.4) were...',
            'details': {...}
        }
    """
    # Fetch last 5 opponents' ranks for each team
    home_last5 = get_last_n_opponents_avg_ranks(home_tricode, as_of_date, n=5)
    away_last5 = get_last_n_opponents_avg_ranks(away_tricode, as_of_date, n=5)

    # If no opponent data, return zero adjustment
    if (home_last5['games_found'] == 0 and away_last5['games_found'] == 0):
        print(f'[opponent_adjustment] No opponent rank data available, adjustment = 0')
        return {
            'adjustment': 0.0,
            'adjusted_total': base_total,
            'adjusted_home': base_home,
            'adjusted_away': base_away,
            'explanation': 'No historical opponent data available for adjustment',
            'details': {
                'home_last5': home_last5,
                'away_last5': away_last5,
                'pace_factor': 0.0,
                'scoring_factor': 0.0
            }
        }

    # Compute adjustment factors
    pace_factor = _compute_pace_adjustment(home_last5, away_last5)
    scoring_factor = _compute_scoring_adjustment(home_last5, away_last5)

    # Combine factors with tunable weights
    # These weights can be adjusted without touching any other code
    PACE_WEIGHT = 2.0      # Max ±2 points from pace context
    SCORING_WEIGHT = 2.0   # Max ±2 points from scoring context

    raw_adjustment = (pace_factor * PACE_WEIGHT) + (scoring_factor * SCORING_WEIGHT)

    # Cap adjustment at ±4 points total
    MAX_ADJUSTMENT = 4.0
    capped_adjustment = max(-MAX_ADJUSTMENT, min(MAX_ADJUSTMENT, raw_adjustment))

    # Apply adjustment to total
    adjusted_total = base_total + capped_adjustment

    # Adjust team scores proportionally to maintain base differential
    # Preserve the home/away split from base prediction
    if base_total > 0:
        home_ratio = base_home / base_total
        away_ratio = base_away / base_total
    else:
        home_ratio = 0.5
        away_ratio = 0.5

    adjusted_home = adjusted_total * home_ratio
    adjusted_away = adjusted_total * away_ratio

    # Generate explanation
    explanation = _generate_explanation(
        home_tricode, away_tricode,
        home_last5, away_last5,
        pace_factor, scoring_factor,
        capped_adjustment
    )

    return {
        'adjustment': round(capped_adjustment, 1),
        'adjusted_total': round(adjusted_total, 1),
        'adjusted_home': round(adjusted_home, 1),
        'adjusted_away': round(adjusted_away, 1),
        'explanation': explanation,
        'details': {
            'home_last5': home_last5,
            'away_last5': away_last5,
            'pace_factor': round(pace_factor, 2),
            'scoring_factor': round(scoring_factor, 2),
            'raw_adjustment': round(raw_adjustment, 2),
            'capped_adjustment': round(capped_adjustment, 1)
        }
    }


def _compute_pace_adjustment(home_last5: Dict, away_last5: Dict) -> float:
    """
    Compute adjustment factor based on pace of recent opponents

    Logic:
    - Lower pace rank = faster pace
    - If recent opponents were fast (low rank), and upcoming game likely slower,
      adjustment should be NEGATIVE (reduce total)
    - Vice versa for slow recent opponents

    Returns:
        Float in range approximately [-1, +1]
    """
    home_pace_rank = home_last5.get('avg_pace_rank')
    away_pace_rank = away_last5.get('avg_pace_rank')

    # If missing data, assume neutral (15.5 = league average rank)
    home_pace_rank = home_pace_rank if home_pace_rank is not None else 15.5
    away_pace_rank = away_pace_rank if away_pace_rank is not None else 15.5

    # Normalize to [-1, +1] range
    # Rank 1 (fastest) → factor = +1 (faced fast opponents, expect deflation)
    # Rank 30 (slowest) → factor = -1 (faced slow opponents, expect inflation)
    # Rank 15.5 (average) → factor = 0 (neutral)
    LEAGUE_AVG_RANK = 15.5
    RANK_RANGE = 15.0

    home_factor = (LEAGUE_AVG_RANK - home_pace_rank) / RANK_RANGE
    away_factor = (LEAGUE_AVG_RANK - away_pace_rank) / RANK_RANGE

    # Average the two teams' factors
    combined_factor = (home_factor + away_factor) / 2.0

    # Clamp to [-1, +1]
    return max(-1.0, min(1.0, combined_factor))


def _compute_scoring_adjustment(home_last5: Dict, away_last5: Dict) -> float:
    """
    Compute adjustment factor based on PPG of recent opponents

    Logic:
    - Lower PPG rank = higher scoring
    - If recent opponents were high-scoring (low rank), and upcoming game
      likely lower-scoring, adjustment should be NEGATIVE
    - Vice versa for low-scoring recent opponents

    Returns:
        Float in range approximately [-1, +1]
    """
    home_ppg_rank = home_last5.get('avg_ppg_rank')
    away_ppg_rank = away_last5.get('avg_ppg_rank')

    # If missing data, assume neutral
    home_ppg_rank = home_ppg_rank if home_ppg_rank is not None else 15.5
    away_ppg_rank = away_ppg_rank if away_ppg_rank is not None else 15.5

    # Normalize to [-1, +1] range
    LEAGUE_AVG_RANK = 15.5
    RANK_RANGE = 15.0

    home_factor = (LEAGUE_AVG_RANK - home_ppg_rank) / RANK_RANGE
    away_factor = (LEAGUE_AVG_RANK - away_ppg_rank) / RANK_RANGE

    # Average the two teams' factors
    combined_factor = (home_factor + away_factor) / 2.0

    # Clamp to [-1, +1]
    return max(-1.0, min(1.0, combined_factor))


def _generate_explanation(
    home_tricode: str,
    away_tricode: str,
    home_last5: Dict,
    away_last5: Dict,
    pace_factor: float,
    scoring_factor: float,
    adjustment: float
) -> str:
    """Generate human-readable explanation of the adjustment"""

    home_ppg = home_last5.get('avg_ppg_rank', 'N/A')
    home_pace = home_last5.get('avg_pace_rank', 'N/A')
    away_ppg = away_last5.get('avg_ppg_rank', 'N/A')
    away_pace = away_last5.get('avg_pace_rank', 'N/A')

    # Format ranks
    def fmt_rank(rank):
        if rank == 'N/A' or rank is None:
            return 'N/A'
        return f"{rank:.1f}"

    # Determine pace context
    if pace_factor > 0.3:
        pace_msg = "recent opponents were slower-paced; expect faster game"
    elif pace_factor < -0.3:
        pace_msg = "recent opponents were faster-paced; expect slower game"
    else:
        pace_msg = "recent opponent pace was average"

    # Determine scoring context
    if scoring_factor > 0.3:
        scoring_msg = "recent opponents scored less; expect higher scoring"
    elif scoring_factor < -0.3:
        scoring_msg = "recent opponents scored more; expect lower scoring"
    else:
        scoring_msg = "recent opponent scoring was average"

    # Direction
    if adjustment > 0.5:
        direction = f"Adjustment: +{adjustment:.1f} points (inflated total)"
    elif adjustment < -0.5:
        direction = f"Adjustment: {adjustment:.1f} points (deflated total)"
    else:
        direction = "Adjustment: neutral (minimal context shift)"

    explanation = (
        f"{home_tricode} last-5 opponents: avg PPG rank {fmt_rank(home_ppg)}, "
        f"avg Pace rank {fmt_rank(home_pace)}. "
        f"{away_tricode} last-5 opponents: avg PPG rank {fmt_rank(away_ppg)}, "
        f"avg Pace rank {fmt_rank(away_pace)}. "
        f"Context: {pace_msg}; {scoring_msg}. "
        f"{direction}"
    )

    return explanation


# ============================================================================
# TUNING GUIDE
# ============================================================================
#
# To adjust the opponent-profile adjustment behavior, modify these values:
#
# 1. **Pace Weight** (line 85):
#    PACE_WEIGHT = 2.0  # Increase for stronger pace adjustments
#
# 2. **Scoring Weight** (line 86):
#    SCORING_WEIGHT = 2.0  # Increase for stronger PPG adjustments
#
# 3. **Max Adjustment Cap** (line 92):
#    MAX_ADJUSTMENT = 4.0  # Increase to allow larger adjustments
#
# 4. **Normalization Range** (lines 134, 171):
#    RANK_RANGE = 15.0  # Affects sensitivity to rank differences
#
# 5. **Factor Formulas** (lines 132-145, 169-182):
#    Modify the normalization logic if you want different scaling
#
# Example tuning scenarios:
# - More aggressive adjustments: Increase PACE_WEIGHT and SCORING_WEIGHT to 3.0
# - Conservative adjustments: Decrease MAX_ADJUSTMENT to 2.0
# - Pace-focused: Set PACE_WEIGHT = 3.0, SCORING_WEIGHT = 1.0
# - Scoring-focused: Set PACE_WEIGHT = 1.0, SCORING_WEIGHT = 3.0
#
# ============================================================================
