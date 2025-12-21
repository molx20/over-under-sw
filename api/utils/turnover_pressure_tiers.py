"""
Turnover Pressure Tier Classification Module

Classifies teams by their ability to force turnovers (defensive pressure).
Used to analyze team turnover rates vs different defensive pressure levels.

Tiers based on opponent turnovers forced per game rank (1-30):
- Elite pressure: ranks 1-10 (best at forcing turnovers)
- Average pressure: ranks 11-20 (middle tier)
- Low pressure: ranks 21-30 (worst at forcing turnovers)
"""

from typing import Optional


def get_turnover_pressure_tier(opp_tov_forced_rank: Optional[int]) -> Optional[str]:
    """
    Convert opponent turnovers forced rank into pressure tier.

    Args:
        opp_tov_forced_rank: Team's rank for forcing opponent turnovers (1-30)
                            Lower rank = better at forcing turnovers

    Returns:
        'elite': ranks 1-10 (forces most turnovers)
        'average': ranks 11-20 (middle tier)
        'low': ranks 21-30 (forces fewest turnovers)
        None: if rank is invalid or missing

    Example:
        >>> get_turnover_pressure_tier(3)
        'elite'
        >>> get_turnover_pressure_tier(15)
        'average'
        >>> get_turnover_pressure_tier(28)
        'low'
    """
    if opp_tov_forced_rank is None:
        return None

    if not isinstance(opp_tov_forced_rank, (int, float)):
        return None

    rank = int(opp_tov_forced_rank)

    if rank < 1 or rank > 30:
        return None

    # Elite pressure defenses (force most turnovers)
    if 1 <= rank <= 10:
        return 'elite'

    # Average pressure defenses
    elif 11 <= rank <= 20:
        return 'average'

    # Low pressure defenses (force fewest turnovers)
    elif 21 <= rank <= 30:
        return 'low'

    return None


def get_all_turnover_pressure_tiers():
    """Return all turnover pressure tier names"""
    return ['elite', 'average', 'low']


def get_turnover_pressure_tier_label(tier: str) -> str:
    """
    Get human-readable label for turnover pressure tier

    Args:
        tier: Tier name ('elite', 'average', 'low')

    Returns:
        Human-readable label for display
    """
    labels = {
        'elite': 'Elite Pressure (1-10)',
        'average': 'Average Pressure (11-20)',
        'low': 'Low Pressure (21-30)'
    }
    return labels.get(tier, tier.capitalize())
