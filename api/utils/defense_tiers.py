"""
Defense Tier Classification Module

Maps defensive rating ranks (1-30) to categorical tiers:
- Elite: Ranks 1-10 (best defenses)
- Average: Ranks 11-20 (middle-tier defenses)
- Bad: Ranks 21-30 (worst defenses)

This module provides simple classification logic for opponent strength analysis.
All tier boundaries are inclusive.
"""

from typing import Optional, List


def get_defense_tier(def_rtg_rank: Optional[int]) -> Optional[str]:
    """
    Map defensive rating rank to tier classification.

    Args:
        def_rtg_rank: Defensive rating rank (1-30, where 1 is best defense)

    Returns:
        Tier name ('elite', 'average', 'bad') or None if rank is missing/invalid

    Examples:
        >>> get_defense_tier(1)
        'elite'
        >>> get_defense_tier(15)
        'average'
        >>> get_defense_tier(28)
        'bad'
        >>> get_defense_tier(None)
        None
    """
    if def_rtg_rank is None:
        return None

    # Validate rank is in valid range
    if not isinstance(def_rtg_rank, int) or def_rtg_rank < 1 or def_rtg_rank > 30:
        return None

    # Elite defenses: Top 10 teams
    if 1 <= def_rtg_rank <= 10:
        return 'elite'

    # Average defenses: Middle tier
    elif 11 <= def_rtg_rank <= 20:
        return 'average'

    # Bad defenses: Bottom 10 teams
    elif 21 <= def_rtg_rank <= 30:
        return 'bad'

    return None


def get_all_defense_tiers() -> List[str]:
    """
    Return list of all tier names in order from best to worst.

    Returns:
        List of tier names: ['elite', 'average', 'bad']

    Usage:
        Useful for iterating through all tiers when building response structures
        or initializing data structures.
    """
    return ['elite', 'average', 'bad']


def get_tier_description(tier: str) -> str:
    """
    Get human-readable description of a defense tier.

    Args:
        tier: Tier name ('elite', 'average', or 'bad')

    Returns:
        Description string

    Examples:
        >>> get_tier_description('elite')
        'Elite Defense (Ranks 1-10)'
    """
    descriptions = {
        'elite': 'Elite Defense (Ranks 1-10)',
        'average': 'Average Defense (Ranks 11-20)',
        'bad': 'Bad Defense (Ranks 21-30)'
    }
    return descriptions.get(tier, 'Unknown Tier')


def get_tier_rank_range(tier: str) -> Optional[tuple]:
    """
    Get the rank range (inclusive) for a tier.

    Args:
        tier: Tier name ('elite', 'average', or 'bad')

    Returns:
        Tuple of (min_rank, max_rank) or None if invalid tier

    Examples:
        >>> get_tier_rank_range('elite')
        (1, 10)
    """
    ranges = {
        'elite': (1, 10),
        'average': (11, 20),
        'bad': (21, 30)
    }
    return ranges.get(tier)
