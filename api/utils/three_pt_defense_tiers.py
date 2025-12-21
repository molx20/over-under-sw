"""
Three-Point Defense Tier Classification

Maps 3PT defense ranks (1-30) to tiers for prediction modeling.
Used in scoring breakdown calculations to project team 3PT scoring
based on opponent's 3PT defensive strength.
"""

from typing import Optional


def get_3pt_defense_tier(opp_fg3_pct_rank: Optional[int]) -> Optional[str]:
    """
    Map 3PT defense rank to tier.

    Args:
        opp_fg3_pct_rank: 3PT% allowed rank (1=best 3PT defense, 30=worst)

    Returns:
        'elite' (ranks 1-10), 'average' (ranks 11-20), 'bad' (ranks 21-30), or None
    """
    if not opp_fg3_pct_rank or not isinstance(opp_fg3_pct_rank, int):
        return None

    if not (1 <= opp_fg3_pct_rank <= 30):
        return None

    if 1 <= opp_fg3_pct_rank <= 10:
        return 'elite'
    elif 11 <= opp_fg3_pct_rank <= 20:
        return 'average'
    else:  # 21-30
        return 'bad'


def get_3pt_defense_tier_range(tier: str) -> tuple[int, int]:
    """
    Get rank range for a defense tier.

    Args:
        tier: 'elite', 'average', or 'bad'

    Returns:
        Tuple of (min_rank, max_rank)
    """
    if tier == 'elite':
        return (1, 10)
    elif tier == 'average':
        return (11, 20)
    elif tier == 'bad':
        return (21, 30)
    else:
        raise ValueError(f"Invalid tier: {tier}")
