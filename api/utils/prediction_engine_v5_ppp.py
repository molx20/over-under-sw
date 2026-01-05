"""
NBA Over/Under Prediction Engine v5.0-PPP (Points Per Possession)

This is a parallel prediction system that uses Points Per Possession (PPP)
instead of Points Per Game (PPG) as the foundation for projections.

Key Differences from v5.0 (PPG):
- Base projections use: Possessions × Blended_PPP instead of Smart Baseline PPG
- Blended_PPP = 0.6 * ppp_last10 + 0.4 * ppp_season
- Defense adjustments are percentage-based (±1-2%) instead of fixed points (±3-5)
- Reuses pace, fatigue, shootout, and home/road logic from v5.0

Pipeline order:
1. Build TeamProfile + MatchupProfile (from v5)
2. Get Blended PPP for each team
3. Calculate projected possessions (from v5 pace)
4. Base projection: Possessions × Blended_PPP
5. Defense adjustments (PPP-specific, smaller)
6. Situational factors: fatigue, shootout, home/road (from v5)
7. Compare to PPG projection
8. Final total
"""

import sqlite3
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from api.utils.team_profiles_v5 import (
    TeamProfile, MatchupProfile,
    build_team_profile, build_matchup_profile
)
from api.utils.ppp_aggregator import get_team_ppp_metrics

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
# STEP 1: BLENDED PPP (replaces Smart Baseline from v5)
# ============================================================================

def compute_blended_ppp(team_id: int, season: str) -> Tuple[Optional[float], Dict]:
    """
    Compute blended PPP using 60% recent + 40% season.

    Formula: blended_ppp = 0.6 * ppp_last10 + 0.4 * ppp_season

    Args:
        team_id: Team ID
        season: Season string

    Returns:
        (blended_ppp, details_dict)

    Edge Cases:
        - If ppp_last10 unavailable (< 10 games), use ppp_season only
        - If ppp_season unavailable, return None
    """
    ppp_metrics = get_team_ppp_metrics(team_id, season, split_type='overall')

    if not ppp_metrics or ppp_metrics['ppp_season'] is None:
        return None, {'error': 'insufficient_ppp_data'}

    ppp_season = ppp_metrics['ppp_season']
    ppp_last10 = ppp_metrics['ppp_last10']
    last10_games = ppp_metrics['ppp_last10_games']

    # Fall back to season if < 10 games
    if ppp_last10 is None or last10_games < 10:
        blended = ppp_season
        weights = {'season': 1.0, 'recent': 0.0}
        blend_type = 'season_only'
    else:
        blended = 0.6 * ppp_last10 + 0.4 * ppp_season
        weights = {'season': 0.4, 'recent': 0.6}
        blend_type = 'blended'

    details = {
        'ppp_season': round(ppp_season, 3),
        'ppp_last10': round(ppp_last10, 3) if ppp_last10 else None,
        'last10_games_used': last10_games,
        'blended_ppp': round(blended, 3),
        'weights': weights,
        'blend_type': blend_type
    }

    return blended, details


# ============================================================================
# STEP 2: PROJECTED POSSESSIONS (reuse from v5)
# ============================================================================

def get_projected_possessions(
    home_profile: TeamProfile,
    away_profile: TeamProfile,
    home_matchup: MatchupProfile,
    away_matchup: MatchupProfile
) -> Tuple[float, str, Dict]:
    """
    Get projected possessions using existing v5 pace calculation.

    Reuses: calculate_advanced_pace_v5() from prediction_engine_v5.py

    Returns:
        (projected_pace, pace_tag, pace_details)
    """
    from api.utils.prediction_engine_v5 import calculate_advanced_pace_v5

    projected_pace, pace_tag, pace_details = calculate_advanced_pace_v5(
        home_profile, away_profile, home_matchup, away_matchup
    )

    return projected_pace, pace_tag, pace_details


# ============================================================================
# STEP 3: DEFENSE ADJUSTMENT (PPP-specific)
# ============================================================================

def calculate_ppp_defense_adjustment(
    team_profile: TeamProfile,
    opponent_profile: TeamProfile,
    projected_possessions: float,
    blended_ppp: float
) -> Tuple[float, Dict]:
    """
    Calculate defense-based adjustment for PPP system.

    Key Difference from v5 (PPG):
    - PPG system: ±5 points based on opponent defense rank
    - PPP system: ±2% of projected score (smaller, since PPP captures efficiency)

    Args:
        team_profile: Scoring team
        opponent_profile: Defending team
        projected_possessions: Possessions for this team
        blended_ppp: Team's blended PPP

    Returns:
        (adjustment_points, details_dict)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get opponent defense rank
    cursor.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM team_season_stats
        WHERE season = ? AND split_type = 'overall' AND def_rtg < (
            SELECT def_rtg FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = 'overall'
        )
    """, (team_profile.season, opponent_profile.team_id, team_profile.season))

    def_rank_row = cursor.fetchone()
    opponent_def_rank = def_rank_row['rank'] if def_rank_row else 15

    conn.close()

    # Defense quality adjustment (percentage-based)
    if opponent_def_rank <= 5:
        # Elite defense: -2% of projected score
        adjustment_pct = -0.02
        quality = 'elite'
    elif opponent_def_rank <= 10:
        # Good defense: -1% of projected score
        adjustment_pct = -0.01
        quality = 'good'
    elif opponent_def_rank >= 26:
        # Weak defense: +2% of projected score
        adjustment_pct = 0.02
        quality = 'weak'
    elif opponent_def_rank >= 21:
        # Below average defense: +1%
        adjustment_pct = 0.01
        quality = 'below_avg'
    else:
        # Average defense: 0%
        adjustment_pct = 0.0
        quality = 'average'

    # Apply to base projection
    base_projection = projected_possessions * blended_ppp
    adjustment = base_projection * adjustment_pct

    details = {
        'opponent_def_rank': opponent_def_rank,
        'defense_quality': quality,
        'adjustment_pct': round(adjustment_pct * 100, 1),  # Convert to percentage
        'adjustment_points': round(adjustment, 1)
    }

    return adjustment, details


# ============================================================================
# MAIN PREDICTION FUNCTION
# ============================================================================

def predict_total_for_game_v5_ppp(
    home_team_id: int,
    away_team_id: int,
    season: str = '2025-26',
    home_rest_days: int = 1,
    away_rest_days: int = 1,
    as_of_date: Optional[str] = None
) -> Dict:
    """
    Generate PPP-based prediction for a game.

    Pipeline:
    1. Build TeamProfile + MatchupProfile (reuse from v5)
    2. Get PPP metrics from team_season_stats
    3. Compute blended PPP for each team
    4. Get projected possessions (reuse pace from v5)
    5. Calculate base total: Possessions × Blended PPP
    6. Apply defense adjustments (smaller, PPP-specific)
    7. Apply situational factors (fatigue, shootout, home/road)
    8. Return prediction with comparison to PPG

    Returns:
        {
            'version': '5.0-PPP',
            'method': 'ppp',
            'home_projected': float,
            'away_projected': float,
            'predicted_total': float,
            'projected_possessions': float,
            'breakdown': {...},
            'comparison_to_ppg': {
                'ppg_total': float,
                'delta': float
            }
        }
    """
    from api.utils.prediction_engine_v5 import (
        predict_total_for_game_v5,
        calculate_fatigue_v5,
        calculate_shootout_v5,
        compute_situational_home_road_edge
    )

    # Step 1: Build profiles
    home_profile = build_team_profile(home_team_id, season, as_of_date)
    away_profile = build_team_profile(away_team_id, season, as_of_date)

    if not home_profile or not away_profile:
        raise ValueError("Insufficient data to build team profiles")

    home_matchup = build_matchup_profile(home_team_id, away_team_id, season, as_of_date)
    away_matchup = build_matchup_profile(away_team_id, home_team_id, season, as_of_date)

    # Step 2: Get blended PPP
    home_ppp, home_ppp_details = compute_blended_ppp(home_team_id, season)
    away_ppp, away_ppp_details = compute_blended_ppp(away_team_id, season)

    if home_ppp is None or away_ppp is None:
        raise ValueError("Insufficient PPP data for prediction")

    # Step 3: Get projected possessions
    projected_possessions, pace_tag, pace_details = get_projected_possessions(
        home_profile, away_profile, home_matchup, away_matchup
    )

    # Step 4: Base projection (Possessions × PPP)
    home_base = projected_possessions * home_ppp
    away_base = projected_possessions * away_ppp

    home_projected = home_base
    away_projected = away_base

    # Step 5: Defense adjustments
    home_def_adj, home_def_details = calculate_ppp_defense_adjustment(
        home_profile, away_profile, projected_possessions, home_ppp
    )
    away_def_adj, away_def_details = calculate_ppp_defense_adjustment(
        away_profile, home_profile, projected_possessions, away_ppp
    )

    home_projected += home_def_adj
    away_projected += away_def_adj

    # Step 6: Situational factors (reuse from v5)
    home_fatigue, away_fatigue, rest_bonus, fatigue_details = calculate_fatigue_v5(
        home_profile, away_profile, home_rest_days, away_rest_days
    )

    home_projected += home_fatigue
    away_projected += away_fatigue

    shootout_total, shootout_details = calculate_shootout_v5(
        home_profile, away_profile, pace_tag
    )

    home_projected += shootout_total / 2
    away_projected += shootout_total / 2

    # Step 7: Home/road edge
    home_road_edge, home_road_details = compute_situational_home_road_edge(
        home_profile, away_profile
    )

    base_total = home_projected + away_projected + rest_bonus
    predicted_total = base_total + home_road_edge

    # Step 8: Build result with PPG comparison
    ppg_result = predict_total_for_game_v5(
        home_team_id, away_team_id, season, home_rest_days, away_rest_days, as_of_date
    )

    result = {
        'version': '5.0-PPP',
        'method': 'ppp',
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'home_team_name': home_profile.team_name,
        'away_team_name': away_profile.team_name,

        # Final projections
        'home_projected': round(home_projected, 1),
        'away_projected': round(away_projected, 1),
        'predicted_total': round(predicted_total, 1),
        'projected_possessions': round(projected_possessions, 1),

        # Breakdown
        'breakdown': {
            'home_base': round(home_base, 1),
            'away_base': round(away_base, 1),
            'home_ppp': home_ppp_details,
            'away_ppp': away_ppp_details,
            'projected_possessions': round(projected_possessions, 1),
            'pace_tag': pace_tag,
            'home_defense_adj': round(home_def_adj, 1),
            'away_defense_adj': round(away_def_adj, 1),
            'shootout_bonus': round(shootout_total, 1),
            'home_fatigue': round(home_fatigue, 1),
            'away_fatigue': round(away_fatigue, 1),
            'rest_bonus': round(rest_bonus, 1),
            'home_road_edge': round(home_road_edge, 1),
            'base_total': round(base_total, 1)
        },

        # Details for each step
        'details': {
            'pace': pace_details,
            'home_defense': home_def_details,
            'away_defense': away_def_details,
            'shootout': shootout_details,
            'fatigue': fatigue_details,
            'home_road': home_road_details
        },

        # Explanations
        'explanations': {
            'baseline': f"PPP base: {home_profile.team_name} {round(home_base, 1)} ({round(projected_possessions, 1)} poss × {round(home_ppp, 3)} PPP), {away_profile.team_name} {round(away_base, 1)} ({round(projected_possessions, 1)} poss × {round(away_ppp, 3)} PPP)",
            'pace': f"Pace: {pace_tag} game ({round(projected_possessions, 1)} possessions)",
            'defense': f"Defense: {home_profile.team_name} {round(home_def_adj, 1):+.1f} ({home_def_details['adjustment_pct']:+.1f}% vs {home_def_details['defense_quality']} defense), {away_profile.team_name} {round(away_def_adj, 1):+.1f} ({away_def_details['adjustment_pct']:+.1f}% vs {away_def_details['defense_quality']} defense)",
            'shootout': f"3PT/AST: {round(shootout_total, 1):+.1f} total bonus",
            'fatigue': f"Fatigue: {home_profile.team_name} {round(home_fatigue, 1):+.1f}, {away_profile.team_name} {round(away_fatigue, 1):+.1f}, rest bonus {round(rest_bonus, 1):+.1f}",
            'home_road': home_road_details['explanation']
        },

        # Comparison to PPG method
        'comparison_to_ppg': {
            'ppg_predicted_total': ppg_result['predicted_total'],
            'ppg_home_projected': ppg_result['home_projected'],
            'ppg_away_projected': ppg_result['away_projected'],
            'ppp_predicted_total': round(predicted_total, 1),
            'delta_total': round(predicted_total - ppg_result['predicted_total'], 1),
            'delta_home': round(home_projected - ppg_result['home_projected'], 1),
            'delta_away': round(away_projected - ppg_result['away_projected'], 1),
            'delta_pct': round(((predicted_total - ppg_result['predicted_total']) / ppg_result['predicted_total']) * 100, 1),
            'larger_method': 'ppp' if predicted_total > ppg_result['predicted_total'] else 'ppg'
        }
    }

    return result


if __name__ == '__main__':
    # Test with a sample game
    import sys

    if len(sys.argv) >= 3:
        home_id = int(sys.argv[1])
        away_id = int(sys.argv[2])
    else:
        # Default: Celtics vs Lakers
        home_id = 1610612738
        away_id = 1610612747

    print(f'\n=== PPP Prediction Engine Test ===\n')

    result = predict_total_for_game_v5_ppp(home_id, away_id)

    print(f"{result['home_team_name']} vs {result['away_team_name']}")
    print(f"\nPPP Projection:")
    print(f"  {result['home_team_name']}: {result['home_projected']}")
    print(f"  {result['away_team_name']}: {result['away_projected']}")
    print(f"  Total: {result['predicted_total']}")
    print(f"  Possessions: {result['projected_possessions']}")

    print(f"\nComparison to PPG:")
    print(f"  PPG Total: {result['comparison_to_ppg']['ppg_predicted_total']}")
    print(f"  PPP Total: {result['comparison_to_ppg']['ppp_predicted_total']}")
    print(f"  Delta: {result['comparison_to_ppg']['delta_total']:+.1f} ({result['comparison_to_ppg']['delta_pct']:+.1f}%)")
    print(f"  Larger Method: {result['comparison_to_ppg']['larger_method'].upper()}")

    print(f"\n✅ PPP projection complete!")
