"""
Trend-Based Prediction Adjustment Module

Applies deterministic adjustments to predictions based on recent trend analysis.
This module is 100% deterministic with hard-coded formulas and caps.

Adjustment Formula (per team, max ±4 pts total):
1. Pace Factor (±1.5 max): pace_delta * 0.3
2. Offensive Factor (±2.0 max): off_rtg_delta * 0.5
3. Defensive Factor (±1.5 max): def_rtg_delta * 0.375

Total adjustment is sum of all factors, capped at ±4 pts per team.
"""

from typing import Dict


def compute_trend_adjustment(
    home_trends: Dict,
    away_trends: Dict,
    base_home_score: float,
    base_away_score: float,
    base_total: float
) -> Dict:
    """
    Compute trend-based adjustments to base prediction.

    This function takes last-5 trend data for both teams and computes
    deterministic adjustments based on recent performance deltas.

    Args:
        home_trends: Last 5 trends for home team (from get_last_5_trends)
        away_trends: Last 5 trends for away team
        base_home_score: Base predicted score for home team
        base_away_score: Base predicted score for away team
        base_total: Base predicted total (sum of base scores)

    Returns:
        Dict with:
        - home_adjustment: Points to add to home score (can be negative)
        - away_adjustment: Points to add to away score (can be negative)
        - total_adjustment: Net change to total (home_adj + away_adj)
        - adjusted_home: base_home_score + home_adjustment
        - adjusted_away: base_away_score + away_adjustment
        - adjusted_total: base_total + total_adjustment
        - explanation: Human-readable summary
        - factors: Breakdown of all adjustment factors

    Example:
        >>> compute_trend_adjustment(
        ...     home_trends={'season_comparison': {'pace_delta': 3.0, 'off_rtg_delta': 2.5, 'def_rtg_delta': -2.0}},
        ...     away_trends={'season_comparison': {'pace_delta': -1.0, 'off_rtg_delta': -1.5, 'def_rtg_delta': 1.5}},
        ...     base_home_score=114.0,
        ...     base_away_score=108.0,
        ...     base_total=222.0
        ... )
        {
            'home_adjustment': +2.1,
            'away_adjustment': -1.3,
            'total_adjustment': +0.8,
            'adjusted_home': 116.1,
            'adjusted_away': 106.7,
            'adjusted_total': 222.8,
            ...
        }
    """
    print('[trend_adjustment] Computing trend-based adjustments')

    # Extract season comparison deltas
    home_comp = home_trends.get('season_comparison', {})
    away_comp = away_trends.get('season_comparison', {})

    # Compute home team factors
    home_pace_factor = _compute_pace_factor(home_comp.get('pace_delta', 0))
    home_off_factor = _compute_offensive_factor(home_comp.get('off_rtg_delta', 0))
    home_def_factor = _compute_defensive_factor(home_comp.get('def_rtg_delta', 0))

    # Compute away team factors
    away_pace_factor = _compute_pace_factor(away_comp.get('pace_delta', 0))
    away_off_factor = _compute_offensive_factor(away_comp.get('off_rtg_delta', 0))
    away_def_factor = _compute_defensive_factor(away_comp.get('def_rtg_delta', 0))

    # Sum factors (before capping)
    home_adjustment_raw = home_pace_factor + home_off_factor + home_def_factor
    away_adjustment_raw = away_pace_factor + away_off_factor + away_def_factor

    # Apply hard caps (±4 pts per team)
    home_adjustment = _cap_adjustment(home_adjustment_raw, max_pts=4.0)
    away_adjustment = _cap_adjustment(away_adjustment_raw, max_pts=4.0)

    # Total adjustment
    total_adjustment = home_adjustment + away_adjustment

    # Compute adjusted predictions
    adjusted_home = base_home_score + home_adjustment
    adjusted_away = base_away_score + away_adjustment
    adjusted_total = base_total + total_adjustment

    # Generate explanation
    explanation = _generate_explanation(
        home_trends.get('team_tricode', 'Home'),
        away_trends.get('team_tricode', 'Away'),
        home_adjustment,
        away_adjustment,
        home_comp,
        away_comp
    )

    print(f'[trend_adjustment] Home: {home_adjustment:+.1f} pts, Away: {away_adjustment:+.1f} pts, Total: {total_adjustment:+.1f} pts')

    return {
        'home_adjustment': round(home_adjustment, 1),
        'away_adjustment': round(away_adjustment, 1),
        'total_adjustment': round(total_adjustment, 1),
        'adjusted_home': round(adjusted_home, 1),
        'adjusted_away': round(adjusted_away, 1),
        'adjusted_total': round(adjusted_total, 1),
        'explanation': explanation,
        'factors': {
            'home_pace_factor': round(home_pace_factor, 2),
            'home_off_factor': round(home_off_factor, 2),
            'home_def_factor': round(home_def_factor, 2),
            'away_pace_factor': round(away_pace_factor, 2),
            'away_off_factor': round(away_off_factor, 2),
            'away_def_factor': round(away_def_factor, 2),
            'home_raw_total': round(home_adjustment_raw, 2),
            'away_raw_total': round(away_adjustment_raw, 2),
            'home_capped': round(home_adjustment, 1),
            'away_capped': round(away_adjustment, 1)
        }
    }


def _compute_pace_factor(pace_delta: float, max_adjustment: float = 1.5) -> float:
    """
    Compute pace-based adjustment.

    Formula: pace_delta * 0.3, capped at ±max_adjustment

    Args:
        pace_delta: Recent pace - season pace (can be positive or negative)
        max_adjustment: Maximum adjustment magnitude (default 1.5)

    Returns:
        Adjustment in points (±1.5 max)

    Example:
        >>> _compute_pace_factor(3.0)  # Playing 3.0 possessions faster
        0.9  # +0.9 pts
        >>> _compute_pace_factor(-2.0)  # Playing 2.0 possessions slower
        -0.6  # -0.6 pts
    """
    raw = pace_delta * 0.3
    return _cap_adjustment(raw, max_adjustment)


def _compute_offensive_factor(off_rtg_delta: float, max_adjustment: float = 2.0) -> float:
    """
    Compute offensive rating adjustment.

    Formula: off_rtg_delta * 0.5, capped at ±max_adjustment

    Args:
        off_rtg_delta: Recent off_rtg - season off_rtg
        max_adjustment: Maximum adjustment magnitude (default 2.0)

    Returns:
        Adjustment in points (±2.0 max)

    Example:
        >>> _compute_offensive_factor(2.5)  # Offense 2.5 points per 100 poss better
        1.25  # +1.25 pts
        >>> _compute_offensive_factor(-3.0)  # Offense 3.0 points worse
        -1.5  # -1.5 pts
    """
    raw = off_rtg_delta * 0.5
    return _cap_adjustment(raw, max_adjustment)


def _compute_defensive_factor(def_rtg_delta: float, max_adjustment: float = 1.5) -> float:
    """
    Compute defensive rating adjustment.

    Formula: def_rtg_delta * 0.375, capped at ±max_adjustment

    NOTE: Negative def_rtg_delta means defense is IMPROVING (allowing fewer points),
    so the adjustment will be NEGATIVE (team scores fewer because pace slows down).

    Args:
        def_rtg_delta: Recent def_rtg - season def_rtg
        max_adjustment: Maximum adjustment magnitude (default 1.5)

    Returns:
        Adjustment in points (±1.5 max)

    Example:
        >>> _compute_defensive_factor(-2.0)  # Defense improving
        -0.75  # -0.75 pts (slower pace, fewer possessions)
        >>> _compute_defensive_factor(3.0)  # Defense worsening
        1.125  # +1.125 pts (faster pace from opponent scoring)
    """
    raw = def_rtg_delta * 0.375
    return _cap_adjustment(raw, max_adjustment)


def _cap_adjustment(value: float, max_pts: float) -> float:
    """
    Cap an adjustment value to ±max_pts.

    Args:
        value: Raw adjustment value
        max_pts: Maximum absolute value

    Returns:
        Capped value

    Example:
        >>> _cap_adjustment(2.3, 2.0)
        2.0
        >>> _cap_adjustment(-5.0, 4.0)
        -4.0
        >>> _cap_adjustment(1.2, 2.0)
        1.2
    """
    if value > max_pts:
        return max_pts
    elif value < -max_pts:
        return -max_pts
    else:
        return value


def _generate_explanation(
    home_team: str,
    away_team: str,
    home_adj: float,
    away_adj: float,
    home_comp: Dict,
    away_comp: Dict
) -> str:
    """
    Generate human-readable explanation of adjustments.

    Args:
        home_team: Home team abbreviation
        away_team: Away team abbreviation
        home_adj: Home adjustment value
        away_adj: Away adjustment value
        home_comp: Home season comparison dict
        away_comp: Away season comparison dict

    Returns:
        Explanation string

    Example:
        "BOS trending hot (+2.1), LAL defense improving (-1.3)"
    """
    parts = []

    # Home team explanation
    if abs(home_adj) >= 0.5:
        if home_adj > 0:
            # Positive adjustment - find dominant factor
            if home_comp.get('off_rtg_delta', 0) >= 2.0:
                parts.append(f'{home_team} offense hot ({home_adj:+.1f})')
            elif home_comp.get('pace_delta', 0) >= 2.0:
                parts.append(f'{home_team} playing faster ({home_adj:+.1f})')
            else:
                parts.append(f'{home_team} trending up ({home_adj:+.1f})')
        else:
            # Negative adjustment
            if home_comp.get('off_rtg_delta', 0) <= -2.0:
                parts.append(f'{home_team} offense cold ({home_adj:+.1f})')
            elif home_comp.get('def_rtg_delta', 0) <= -2.0:
                parts.append(f'{home_team} defense improved ({home_adj:+.1f})')
            else:
                parts.append(f'{home_team} trending down ({home_adj:+.1f})')

    # Away team explanation
    if abs(away_adj) >= 0.5:
        if away_adj > 0:
            if away_comp.get('off_rtg_delta', 0) >= 2.0:
                parts.append(f'{away_team} offense hot ({away_adj:+.1f})')
            elif away_comp.get('pace_delta', 0) >= 2.0:
                parts.append(f'{away_team} playing faster ({away_adj:+.1f})')
            else:
                parts.append(f'{away_team} trending up ({away_adj:+.1f})')
        else:
            if away_comp.get('off_rtg_delta', 0) <= -2.0:
                parts.append(f'{away_team} offense cold ({away_adj:+.1f})')
            elif away_comp.get('def_rtg_delta', 0) <= -2.0:
                parts.append(f'{away_team} defense improved ({away_adj:+.1f})')
            else:
                parts.append(f'{away_team} trending down ({away_adj:+.1f})')

    # If no significant adjustments
    if not parts:
        return 'Both teams playing near season averages'

    return ', '.join(parts)
