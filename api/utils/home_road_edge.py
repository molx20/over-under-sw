"""
Situational Home/Road Edge Module (v5.0)

NEW PHILOSOPHY:
- Do NOT apply default home boost or road penalty
- Only adjust when there's a CLEAR home/road pattern
- Applied to game total (not individual baselines)
- Conservative: max ±4 points, often returns 0

Replaces the old static Home Court Advantage + Road Penalty system.
All logic is deterministic and explainable at a 5th-grade reading level.
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


def safe_get(data: Dict, key: str, default: float = 0.0) -> float:
    """Safely get a numeric value from dict, return default if missing"""
    try:
        val = data.get(key, default)
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


class GameContext:
    """
    Encapsulates all data needed for home/road edge calculation.
    Constructed from team stats, advanced stats, and game info.
    """
    def __init__(
        self,
        home_stats: Dict,
        away_stats: Dict,
        home_advanced: Dict,
        away_advanced: Dict,
        home_team_id: int,
        away_team_id: int,
        projected_pace: float,
        season: str = '2025-26'
    ):
        self.season = season
        self.projected_pace = projected_pace
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id

        # Extract team names (with fallback)
        from api.utils.db_queries import get_all_teams
        try:
            teams = get_all_teams()
            home_team_data = next((t for t in teams if t['team_id'] == home_team_id), None)
            away_team_data = next((t for t in teams if t['team_id'] == away_team_id), None)
            self.home_team_name = home_team_data['full_name'] if home_team_data else "Home Team"
            self.away_team_name = away_team_data['full_name'] if away_team_data else "Away Team"
        except:
            self.home_team_name = "Home Team"
            self.away_team_name = "Away Team"

        # Get season averages
        home_overall = home_stats.get('overall', {})
        away_overall = away_stats.get('overall', {})

        self.home_season_ppg = safe_get(home_overall, 'PTS', 110.0)
        self.away_season_ppg = safe_get(away_overall, 'PTS', 105.0)

        # Get home/away splits for PPG
        home_home_stats = home_stats.get('home', {})
        away_road_stats = away_stats.get('away', {})

        self.home_home_ppg = safe_get(home_home_stats, 'PTS', self.home_season_ppg)
        self.away_road_ppg = safe_get(away_road_stats, 'PTS', self.away_season_ppg)

        # Win percentages (optional - for future enhancement)
        home_wins = safe_get(home_home_stats, 'W', 0)
        home_games = safe_get(home_home_stats, 'GP', 1)
        self.home_win_pct = home_wins / max(home_games, 1)

        away_road_wins = safe_get(away_road_stats, 'W', 0)
        away_road_games = safe_get(away_road_stats, 'GP', 1)
        self.away_win_pct = away_road_wins / max(away_road_games, 1)

        # Rest/schedule info (will be populated by caller)
        self.home_rest_days = 2  # Default
        self.away_rest_days = 2
        self.home_is_b2b = False
        self.away_is_b2b = False

    def set_rest_info(self, home_rest: int, away_rest: int, home_b2b: bool, away_b2b: bool):
        """Set rest and schedule context"""
        self.home_rest_days = home_rest
        self.away_rest_days = away_rest
        self.home_is_b2b = home_b2b
        self.away_is_b2b = away_b2b


class HomeRoadEdgeResult:
    """Result object containing edge points and explanations"""
    def __init__(
        self,
        home_edge_points: float,
        away_edge_points: float,
        components: Dict[str, float],
        reasons_5th_grade: Dict[str, str]
    ):
        self.home_edge_points = home_edge_points
        self.away_edge_points = away_edge_points
        self.components = components
        self.reasons_5th_grade = reasons_5th_grade

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        # Round numeric values, keep strings as-is
        components_serialized = {}
        for k, v in self.components.items():
            if isinstance(v, (int, float)):
                components_serialized[k] = round(v, 2)
            else:
                components_serialized[k] = v

        return {
            'home_edge_points': round(self.home_edge_points, 1),
            'away_edge_points': round(self.away_edge_points, 1),
            'components': components_serialized,
            'reasons_5th_grade': self.reasons_5th_grade
        }


def compute_home_road_edge(context: GameContext) -> HomeRoadEdgeResult:
    """
    Compute situational home/road edge based on CLEAR patterns only.

    NEW PHILOSOPHY (v5.0):
    - Do NOT apply default home boost or road penalty
    - Only adjust total when there's a strong home/road pattern
    - Applied to game total (not individual team baselines)

    Classifications:
    - Strong at home: home_ppg - season_ppg >= 4
    - Weak at home:   home_ppg - season_ppg <= -4
    - Normal: Everything else

    - Strong on road: road_ppg - season_ppg >= 4
    - Weak on road:   road_ppg - season_ppg <= -4
    - Normal: Everything else

    Total Edge (applied to game total):
    - Home Strong & Away Weak road    → +4
    - Home Strong & Away Normal       → +2
    - Home Normal & Away Weak road    → +2
    - Home Weak & Away Strong road    → -4
    - Home Weak & Away Normal         → -2
    - Home Normal & Away Strong road  → -2
    - All other combinations          → 0

    Args:
        context: GameContext with team stats and game info

    Returns:
        HomeRoadEdgeResult with point adjustments and 5th-grade explanations
    """

    # ========================================================================
    # 1. CLASSIFY HOME TEAM'S HOME STRENGTH
    # ========================================================================
    home_ppg_diff = context.home_home_ppg - context.home_season_ppg

    if home_ppg_diff >= 4:
        home_strength = "Strong"
    elif home_ppg_diff <= -4:
        home_strength = "Weak"
    else:
        home_strength = "Normal"

    # ========================================================================
    # 2. CLASSIFY AWAY TEAM'S ROAD STRENGTH
    # ========================================================================
    away_ppg_diff = context.away_road_ppg - context.away_season_ppg

    if away_ppg_diff >= 4:
        away_strength = "Strong"
    elif away_ppg_diff <= -4:
        away_strength = "Weak"
    else:
        away_strength = "Normal"

    # ========================================================================
    # 3. DETERMINE TOTAL EDGE BASED ON PATTERN (TUNED: Max ±2 points)
    # ========================================================================
    # TUNED: Reduced all adjustments by 50% to keep home/road as light contextual nudge
    total_edge = 0.0
    explanation = ""

    if home_strength == "Strong" and away_strength == "Weak":
        total_edge = 2.0  # Was 4.0
        explanation = (f"{context.home_team_name} is better at home "
                      f"({home_ppg_diff:+.1f} PPG) and {context.away_team_name} "
                      f"struggles on the road ({away_ppg_diff:+.1f} PPG), so we "
                      f"added a small boost.")

    elif home_strength == "Strong" and away_strength == "Normal":
        total_edge = 0.0  # Was 2.0 - too aggressive for single condition
        explanation = (f"{context.home_team_name} is strong at home "
                      f"({home_ppg_diff:+.1f} PPG), but we're keeping this conservative.")

    elif home_strength == "Normal" and away_strength == "Weak":
        total_edge = 0.0  # Was 2.0 - too aggressive for single condition
        explanation = (f"{context.away_team_name} struggles on the road "
                      f"({away_ppg_diff:+.1f} PPG), but we're keeping this conservative.")

    elif home_strength == "Weak" and away_strength == "Strong":
        total_edge = -2.0  # Was -4.0
        explanation = (f"{context.home_team_name} is weak at home "
                      f"({home_ppg_diff:+.1f} PPG) and {context.away_team_name} "
                      f"travels well ({away_ppg_diff:+.1f} PPG), so we "
                      f"lowered the total slightly.")

    elif home_strength == "Weak" and away_strength == "Normal":
        total_edge = 0.0  # Was -2.0 - too aggressive for single condition
        explanation = (f"{context.home_team_name} is weak at home "
                      f"({home_ppg_diff:+.1f} PPG), but we're keeping this conservative.")

    elif home_strength == "Normal" and away_strength == "Strong":
        total_edge = 0.0  # Was -2.0 - too aggressive for single condition
        explanation = (f"{context.away_team_name} travels well "
                      f"({away_ppg_diff:+.1f} PPG), but we're keeping this conservative.")

    else:  # Both Normal or neutral combinations (Strong+Strong, Weak+Weak)
        total_edge = 0.0
        if home_strength == "Normal" and away_strength == "Normal":
            explanation = (f"Both teams are pretty normal home/road, so we didn't "
                          f"adjust the total here.")
        else:
            explanation = (f"No clear home/road advantage pattern here "
                          f"({context.home_team_name} is {home_strength.lower()} at home, "
                          f"{context.away_team_name} is {away_strength.lower()} on road), "
                          f"so we didn't adjust the total.")

    # ========================================================================
    # 4. SPLIT TOTAL EDGE INTO HOME/AWAY COMPONENTS
    # ========================================================================
    # For backwards compatibility with existing code that expects separate
    # home_edge_points and away_edge_points, we split the total edge

    if total_edge > 0:
        # Positive edge: favor home team
        home_edge_points = total_edge * 0.6  # 60% to home
        away_edge_points = total_edge * 0.4  # 40% to away
    elif total_edge < 0:
        # Negative edge: favor away team
        home_edge_points = total_edge * 0.4  # 40% penalty to home
        away_edge_points = total_edge * 0.6  # 60% boost to away (negative * negative = positive effect)
    else:
        # No edge
        home_edge_points = 0.0
        away_edge_points = 0.0

    # ========================================================================
    # 5. BUILD RESULT WITH COMPONENTS
    # ========================================================================
    components = {
        'total_edge': total_edge,
        'home_strength': home_strength,
        'away_strength': away_strength,
        'home_ppg_diff': home_ppg_diff,
        'away_ppg_diff': away_ppg_diff,
    }

    reasons = {
        'main_explanation': explanation,
        'home_pattern': f"{context.home_team_name} at home: {home_ppg_diff:+.1f} PPG vs season average",
        'away_pattern': f"{context.away_team_name} on road: {away_ppg_diff:+.1f} PPG vs season average"
    }

    return HomeRoadEdgeResult(home_edge_points, away_edge_points, components, reasons)
