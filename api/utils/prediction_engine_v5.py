"""
NBA Over/Under Prediction Engine v5.0

Major changes from v4.4:
- Uses TeamProfile and MatchupProfile built from game_logs
- Refactored Smart Baseline to use TeamProfile data
- Advanced Pace uses TeamProfile + MatchupProfile
- Defense logic uses TeamProfile + small matchup tweaks (max ±4)
- HCA/Road scaled by home/away performance
- Optional AST seasoning for 3PT games
- Optional rest bonus for well-rested teams
- Removed large MATCHUP_ADJUSTMENTS block

Pipeline order:
1. Smart Baseline (from TeamProfile)
2. Advanced Pace (context-aware, returns projectedPace + paceTag)
3. Defense + Defense Quality + Matchup Tweaks (max ±4 per team)
4. HCA + Road Penalty (scaled by home/away splits)
5. 3PT Shootout + optional AST seasoning
6. Fatigue/Rest + optional rest bonus
7. Final total
"""

import sqlite3
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from api.utils.team_profiles_v5 import (
    TeamProfile, MatchupProfile,
    build_team_profile, build_matchup_profile
)

logger = logging.getLogger(__name__)

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


# ============================================================================
# STEP 1: SMART BASELINE (Updated to use TeamProfile)
# ============================================================================

def compute_smart_baseline_v5(profile: TeamProfile) -> Tuple[float, str, float, float]:
    """
    Compute smart baseline PPG using TeamProfile.

    Uses season_ppg and last_5_ppg with adaptive weighting based on trend strength.

    Args:
        profile: TeamProfile with season and recent stats

    Returns:
        (baseline_ppg, trend_type, season_weight, recent_weight)
    """
    season_ppg = profile.season_ppg
    recent_ppg = profile.last_5_ppg
    recent_ortg_change = profile.recent_ortg_change

    ppg_change = abs(recent_ppg - season_ppg)
    abs_ortg_change = abs(recent_ortg_change)

    # Determine weights based on trend magnitude
    if ppg_change > 10 or abs_ortg_change > 8:
        # Extreme trend
        season_weight = 0.60
        recent_weight = 0.40
        trend_type = "extreme"
    elif ppg_change > 3 or abs_ortg_change > 3:
        # Normal trend
        season_weight = 0.70
        recent_weight = 0.30
        trend_type = "normal"
    else:
        # Minimal trend
        season_weight = 0.80
        recent_weight = 0.20
        trend_type = "minimal"

    baseline = season_ppg * season_weight + recent_ppg * recent_weight

    return baseline, trend_type, season_weight, recent_weight


# ============================================================================
# STEP 2: ADVANCED PACE (Updated to use TeamProfile + MatchupProfile)
# ============================================================================

def calculate_advanced_pace_v5(
    home_profile: TeamProfile,
    away_profile: TeamProfile,
    home_matchup: MatchupProfile,
    away_matchup: MatchupProfile
) -> Tuple[float, str, Dict]:
    """
    Calculate projected pace using TeamProfile and MatchupProfile.

    Keeps same math as v4.3 but uses profile data.

    Returns:
        (projected_pace, pace_tag, details_dict)
    """
    # Blend season (60%) + recent (40%) for each team
    home_blended = home_profile.season_pace * 0.6 + home_profile.last_5_pace * 0.4
    away_blended = away_profile.season_pace * 0.6 + away_profile.last_5_pace * 0.4

    # Base pace (slight home bias)
    base_pace = home_blended * 0.52 + away_blended * 0.48

    # Pace mismatch penalty
    pace_diff = abs(home_blended - away_blended)
    mismatch_penalty = 0
    if pace_diff > 6:
        mismatch_penalty = -1.5
    elif pace_diff > 3:
        mismatch_penalty = -0.75

    # Turnover boost (high TO = more transition possessions)
    avg_turnovers = (home_profile.season_turnovers + away_profile.season_turnovers) / 2
    to_boost = 0
    if avg_turnovers > 15:
        to_boost = 1.5
    elif avg_turnovers > 13.5:
        to_boost = 0.75

    # FT penalty (free throws slow pace)
    # Estimate FTA from FT%: FTA ≈ (PPG * 0.22) / FT%
    home_fta_est = (home_profile.season_ppg * 0.22) / max(home_profile.season_ft_pct, 0.5)
    away_fta_est = (away_profile.season_ppg * 0.22) / max(away_profile.season_ft_pct, 0.5)
    avg_fta = (home_fta_est + away_fta_est) / 2

    ft_penalty = 0
    if avg_fta > 26:
        ft_penalty = -1.5
    elif avg_fta > 23:
        ft_penalty = -0.75

    # Defense penalty (elite defenses slow pace)
    avg_drtg = (home_profile.season_drtg + away_profile.season_drtg) / 2
    def_penalty = 0
    if avg_drtg < 109:  # Both elite defenses
        def_penalty = -1.0

    # Projected pace
    projected_pace = base_pace + mismatch_penalty + to_boost + ft_penalty + def_penalty

    # Clamp to realistic range
    projected_pace = max(92, min(108, projected_pace))

    # Pace tag
    if projected_pace >= 102:
        pace_tag = "Fast"
    elif projected_pace <= 97:
        pace_tag = "Slow"
    else:
        pace_tag = "Normal"

    details = {
        'base_pace': round(base_pace, 1),
        'mismatch_penalty': round(mismatch_penalty, 1),
        'to_boost': round(to_boost, 1),
        'ft_penalty': round(ft_penalty, 1),
        'def_penalty': round(def_penalty, 1),
        'projected_pace': round(projected_pace, 1),
        'pace_tag': pace_tag
    }

    return projected_pace, pace_tag, details


# ============================================================================
# STEP 3: DEFENSE + MATCHUP TWEAKS
# ============================================================================

def calculate_defense_adjustment_v5(
    team_profile: TeamProfile,
    opponent_profile: TeamProfile,
    team_matchup: MatchupProfile,
    projected_pace: float,
    is_home: bool
) -> Tuple[float, Dict]:
    """
    Calculate defense-based scoring adjustment with small matchup tweaks.

    Combines:
    - Defense quality adjustment (from opponent DRtg rank)
    - Small matchup tweaks based on MatchupProfile (max ±4)

    Args:
        team_profile: Scoring team's profile
        opponent_profile: Defending team's profile
        team_matchup: Scoring team's matchup profile
        projected_pace: Game pace
        is_home: Is scoring team home?

    Returns:
        (total_adjustment, details_dict)
    """
    total_adjustment = 0.0
    details = {}

    # Get opponent defense rank
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM team_season_stats
        WHERE season = ? AND split_type = 'Overall' AND def_rtg < (
            SELECT def_rtg FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = 'Overall'
        )
    """, (team_profile.season, opponent_profile.team_id, team_profile.season))

    def_rank_row = cursor.fetchone()
    opponent_def_rank = def_rank_row['rank'] if def_rank_row else 15

    conn.close()

    # Defense quality adjustment (from v4.4)
    if opponent_def_rank <= 5:
        # Elite defense
        base_penalty = -5.0
    elif opponent_def_rank <= 10:
        # Good defense
        base_penalty = -3.0
    elif opponent_def_rank >= 26:
        # Weak defense
        base_penalty = 3.0
    elif opponent_def_rank >= 21:
        # Below average defense
        base_penalty = 1.5
    else:
        # Average defense
        base_penalty = 0.0

    total_adjustment += base_penalty
    details['defense_quality'] = round(base_penalty, 1)
    details['opponent_def_rank'] = opponent_def_rank

    # Small matchup tweaks (max ±4 total)
    matchup_tweak = 0.0

    # H2H vs this opponent
    if team_matchup.h2h_games >= 2:
        h2h_diff = team_matchup.h2h_ppg - team_profile.season_ppg
        if abs(h2h_diff) > 3:
            matchup_tweak += max(-2, min(2, h2h_diff * 0.3))

    # Vs fast/slow opponents
    if projected_pace >= 102 and team_matchup.vs_fast_games >= 3:
        fast_diff = team_matchup.vs_fast_ppg - team_profile.season_ppg
        if abs(fast_diff) > 2:
            matchup_tweak += max(-1, min(1, fast_diff * 0.2))

    elif projected_pace <= 97 and team_matchup.vs_slow_games >= 3:
        slow_diff = team_matchup.vs_slow_ppg - team_profile.season_ppg
        if abs(slow_diff) > 2:
            matchup_tweak += max(-1, min(1, slow_diff * 0.2))

    # Vs good/bad defenses
    if opponent_def_rank <= 10 and team_matchup.vs_good_def_games >= 3:
        vs_good_diff = team_matchup.vs_good_def_ppg - team_profile.season_ppg
        if abs(vs_good_diff) > 2:
            matchup_tweak += max(-1, min(1, vs_good_diff * 0.2))

    elif opponent_def_rank >= 21 and team_matchup.vs_bad_def_games >= 3:
        vs_bad_diff = team_matchup.vs_bad_def_ppg - team_profile.season_ppg
        if abs(vs_bad_diff) > 2:
            matchup_tweak += max(-1, min(1, vs_bad_diff * 0.2))

    # Cap matchup tweaks at ±4
    matchup_tweak = max(-4, min(4, matchup_tweak))

    total_adjustment += matchup_tweak
    details['matchup_tweak'] = round(matchup_tweak, 1)

    return total_adjustment, details


# ============================================================================
# STEP 4: SITUATIONAL HOME/ROAD EDGE (REMOVED OLD HCA/ROAD PENALTY)
# ============================================================================

def compute_situational_home_road_edge(
    home_profile: TeamProfile,
    away_profile: TeamProfile
) -> Tuple[float, Dict]:
    """
    Compute situational home/road edge based on CLEAR patterns only.

    NEW PHILOSOPHY:
    - Do NOT apply default home boost or road penalty
    - Only adjust total when there's a strong home/road pattern
    - Applied to game total (not individual team baselines)

    Classifications:
    - Strong at home: (home_ppg - season_ppg >= 4) OR (home_win_pct >= 0.65)
    - Weak at home:   (home_ppg - season_ppg <= -4) OR (home_win_pct <= 0.40)
    - Normal: Everything else

    - Strong on road: (road_ppg - season_ppg >= 4) OR (road_win_pct >= 0.55)
    - Weak on road:   (road_ppg - season_ppg <= -4) OR (road_win_pct <= 0.35)
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
        home_profile: Home team profile
        away_profile: Away team profile

    Returns:
        (total_edge, details_dict)
    """
    # Calculate home team's home strength
    home_ppg_diff = home_profile.home_ppg - home_profile.season_ppg

    # Calculate win% (wins / games)
    # We don't have wins in TeamProfile, so we'll use PPG diff only
    # If you have win data, add: home_win_pct = home_wins / home_games

    if home_ppg_diff >= 4:
        home_strength = "Strong"
    elif home_ppg_diff <= -4:
        home_strength = "Weak"
    else:
        home_strength = "Normal"

    # Calculate away team's road strength
    away_ppg_diff = away_profile.away_ppg - away_profile.season_ppg

    if away_ppg_diff >= 4:
        away_strength = "Strong"
    elif away_ppg_diff <= -4:
        away_strength = "Weak"
    else:
        away_strength = "Normal"

    # Determine total edge based on pattern
    total_edge = 0.0
    explanation = ""

    if home_strength == "Strong" and away_strength == "Weak":
        total_edge = 4.0
        explanation = (f"{home_profile.team_name} is much better at home "
                      f"({home_ppg_diff:+.1f} PPG) and {away_profile.team_name} "
                      f"struggles on the road ({away_ppg_diff:+.1f} PPG), so we "
                      f"bumped the total up.")

    elif home_strength == "Strong" and away_strength == "Normal":
        total_edge = 2.0
        explanation = (f"{home_profile.team_name} is strong at home "
                      f"({home_ppg_diff:+.1f} PPG), so we nudged the total up slightly.")

    elif home_strength == "Normal" and away_strength == "Weak":
        total_edge = 2.0
        explanation = (f"{away_profile.team_name} struggles on the road "
                      f"({away_ppg_diff:+.1f} PPG), so we nudged the total up slightly.")

    elif home_strength == "Weak" and away_strength == "Strong":
        total_edge = -4.0
        explanation = (f"{home_profile.team_name} is weak at home "
                      f"({home_ppg_diff:+.1f} PPG) and {away_profile.team_name} "
                      f"travels well ({away_ppg_diff:+.1f} PPG), so we nudged "
                      f"the total down.")

    elif home_strength == "Weak" and away_strength == "Normal":
        total_edge = -2.0
        explanation = (f"{home_profile.team_name} is weak at home "
                      f"({home_ppg_diff:+.1f} PPG), so we nudged the total down slightly.")

    elif home_strength == "Normal" and away_strength == "Strong":
        total_edge = -2.0
        explanation = (f"{away_profile.team_name} travels well "
                      f"({away_ppg_diff:+.1f} PPG), so we nudged the total down slightly.")

    else:  # Both Normal or other neutral combinations
        total_edge = 0.0
        if home_strength == "Normal" and away_strength == "Normal":
            explanation = (f"Both teams are pretty normal home/road, so we didn't "
                          f"adjust the total here.")
        else:
            explanation = (f"No clear home/road advantage pattern here "
                          f"({home_profile.team_name} is {home_strength.lower()} at home, "
                          f"{away_profile.team_name} is {away_strength.lower()} on road), "
                          f"so we didn't adjust the total.")

    details = {
        'home_strength': home_strength,
        'away_strength': away_strength,
        'home_ppg_diff': round(home_ppg_diff, 1),
        'away_ppg_diff': round(away_ppg_diff, 1),
        'total_edge': round(total_edge, 1),
        'explanation': explanation
    }

    return total_edge, details


# ============================================================================
# STEP 5: 3PT SHOOTOUT + OPTIONAL AST SEASONING
# ============================================================================

def calculate_shootout_v5(
    home_profile: TeamProfile,
    away_profile: TeamProfile,
    pace_tag: str
) -> Tuple[float, Dict]:
    """
    Dynamic 3PT Shootout detection (from v4.2).

    Optional: Add +1 to +2 if high combined assists and pace is not slow.
    """
    # Get defense ranks (simplified - use DRtg as proxy)
    conn = _get_db_connection()
    cursor = conn.cursor()

    # This is a simplified version - shootout bonus is DISABLED in v4.4
    # Keeping detection logic but not applying bonus
    shootout_bonus = 0.0

    # Optional AST seasoning
    ast_bonus = 0.0
    combined_ast = home_profile.season_assists + away_profile.season_assists

    # Check if top 8 in league for assists (>27 per team avg = ~54 combined)
    if combined_ast > 54 and pace_tag != "Slow":
        ast_bonus = 1.5

    conn.close()

    details = {
        'shootout_bonus': round(shootout_bonus, 1),
        'ast_bonus': round(ast_bonus, 1),
        'combined_assists': round(combined_ast, 1)
    }

    return shootout_bonus + ast_bonus, details


# ============================================================================
# STEP 6: FATIGUE/REST + OPTIONAL REST BONUS
# ============================================================================

def calculate_fatigue_v5(
    home_profile: TeamProfile,
    away_profile: TeamProfile,
    home_rest_days: int,
    away_rest_days: int
) -> Tuple[float, float, float, Dict]:
    """
    Calculate fatigue adjustments (from v4.0).

    Optional: Add +1 to +2 total when both teams have 2+ days rest.
    """
    # B2B penalties
    home_fatigue = -3.0 if home_rest_days == 0 else 0.0
    away_fatigue = -3.0 if away_rest_days == 0 else 0.0

    # Optional well-rested bonus
    rest_bonus = 0.0
    if home_rest_days >= 2 and away_rest_days >= 2:
        rest_bonus = 1.5  # Split between teams or add to total

    details = {
        'home_fatigue': round(home_fatigue, 1),
        'away_fatigue': round(away_fatigue, 1),
        'rest_bonus': round(rest_bonus, 1),
        'home_rest_days': home_rest_days,
        'away_rest_days': away_rest_days
    }

    return home_fatigue, away_fatigue, rest_bonus, details


# ============================================================================
# MAIN PREDICTION FUNCTION
# ============================================================================

def predict_total_for_game_v5(
    home_team_id: int,
    away_team_id: int,
    season: str = '2025-26',
    home_rest_days: int = 1,
    away_rest_days: int = 1,
    as_of_date: Optional[str] = None
) -> Dict:
    """
    Generate v5.0 prediction for a game.

    Pipeline:
    1. Build TeamProfile + MatchupProfile
    2. Smart Baseline
    3. Advanced Pace
    4. Defense + Matchup Tweaks (max ±4 per team)
    5. 3PT Shootout + AST Seasoning
    6. Fatigue/Rest + Rest Bonus
    7. Situational Home/Road Edge (applied to total, only when clear pattern exists)
    8. Final total

    NOTE: Old HCA/Road Penalty system REMOVED.
          New system only adjusts total when there's a CLEAR home/road pattern.
          Applied to game total, not individual baselines.

    Returns:
        Dict with projections, breakdown, and explanations
    """
    # Build profiles
    home_profile = build_team_profile(home_team_id, season, as_of_date)
    away_profile = build_team_profile(away_team_id, season, as_of_date)

    if not home_profile or not away_profile:
        raise ValueError("Insufficient data to build team profiles")

    home_matchup = build_matchup_profile(home_team_id, away_team_id, season, as_of_date)
    away_matchup = build_matchup_profile(away_team_id, home_team_id, season, as_of_date)

    # Step 1: Smart Baseline
    home_baseline, home_trend, home_s_w, home_r_w = compute_smart_baseline_v5(home_profile)
    away_baseline, away_trend, away_s_w, away_r_w = compute_smart_baseline_v5(away_profile)

    home_projected = home_baseline
    away_projected = away_baseline

    # Step 2: Advanced Pace
    projected_pace, pace_tag, pace_details = calculate_advanced_pace_v5(
        home_profile, away_profile, home_matchup, away_matchup
    )

    # Step 3: Defense + Matchup Tweaks
    home_def_adj, home_def_details = calculate_defense_adjustment_v5(
        home_profile, away_profile, home_matchup, projected_pace, is_home=True
    )
    away_def_adj, away_def_details = calculate_defense_adjustment_v5(
        away_profile, home_profile, away_matchup, projected_pace, is_home=False
    )

    home_projected += home_def_adj
    away_projected += away_def_adj

    # Step 4: 3PT Shootout + AST Seasoning
    shootout_total, shootout_details = calculate_shootout_v5(
        home_profile, away_profile, pace_tag
    )

    # Split shootout bonus between teams
    home_projected += shootout_total / 2
    away_projected += shootout_total / 2

    # Step 5: Fatigue/Rest
    home_fatigue, away_fatigue, rest_bonus, fatigue_details = calculate_fatigue_v5(
        home_profile, away_profile, home_rest_days, away_rest_days
    )

    home_projected += home_fatigue
    away_projected += away_fatigue

    # Step 6: Situational Home/Road Edge (NEW - replaces old HCA/Road)
    # This is applied to the TOTAL, not individual baselines
    # Only adjusts when there's a clear home/road pattern
    home_road_edge, home_road_details = compute_situational_home_road_edge(
        home_profile, away_profile
    )

    # Calculate base total before home/road adjustment
    base_total = home_projected + away_projected + rest_bonus

    # Apply home/road edge to total
    predicted_total = base_total + home_road_edge

    # Build result
    result = {
        'version': '5.0',
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'home_team_name': home_profile.team_name,
        'away_team_name': away_profile.team_name,

        # Final projections
        'home_projected': round(home_projected, 1),
        'away_projected': round(away_projected, 1),
        'predicted_total': round(predicted_total, 1),

        # Breakdown
        'breakdown': {
            'home_baseline': round(home_baseline, 1),
            'away_baseline': round(away_baseline, 1),
            'projected_pace': round(projected_pace, 1),
            'pace_tag': pace_tag,
            'home_defense_adj': round(home_def_adj, 1),
            'away_defense_adj': round(away_def_adj, 1),
            'shootout_bonus': round(shootout_total, 1),
            'home_fatigue': round(home_fatigue, 1),
            'away_fatigue': round(away_fatigue, 1),
            'rest_bonus': round(rest_bonus, 1),
            'home_road_edge': round(home_road_edge, 1),  # NEW: Situational edge
            'base_total': round(base_total, 1)  # Before home/road adjustment
        },

        # Details for each step
        'details': {
            'pace': pace_details,
            'home_defense': home_def_details,
            'away_defense': away_def_details,
            'shootout': shootout_details,
            'fatigue': fatigue_details,
            'home_road': home_road_details  # NEW: Situational home/road details
        },

        # Explanations
        'explanations': {
            'baseline': f"Smart baseline: {home_profile.team_name} {round(home_baseline, 1)} ({home_trend} trend), {away_profile.team_name} {round(away_baseline, 1)} ({away_trend} trend)",
            'pace': f"Pace: {pace_tag} game ({round(projected_pace, 1)} possessions)",
            'defense': f"Defense: {home_profile.team_name} {round(home_def_adj, 1):+.1f} vs rank {home_def_details['opponent_def_rank']} defense, {away_profile.team_name} {round(away_def_adj, 1):+.1f} vs rank {away_def_details['opponent_def_rank']} defense",
            'shootout': f"3PT/AST: {round(shootout_total, 1):+.1f} total bonus",
            'fatigue': f"Fatigue: {home_profile.team_name} {round(home_fatigue, 1):+.1f}, {away_profile.team_name} {round(away_fatigue, 1):+.1f}, rest bonus {round(rest_bonus, 1):+.1f}",
            'home_road': home_road_details['explanation']  # NEW: Natural language explanation
        }
    }

    return result
