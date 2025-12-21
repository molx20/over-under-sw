"""
Opponent Matchup Statistics Module

Provides functions to load opponent stats and compute matchup-based adjustments
for game predictions. Compares team offense vs opponent defense to identify
favorable/unfavorable matchups.

Usage:
    from api.utils.opponent_matchup_stats import (
        get_team_opponent_stats,
        compute_matchup_adjustment
    )

    # Get opponent stats for a team (what they ALLOW opponents to do)
    opp_stats = get_team_opponent_stats(team_id=1610612737, season='2025-26')

    # Compute matchup adjustment comparing offense vs defense
    adjustment = compute_matchup_adjustment(
        team_offense={'fg_pct': 0.475, 'fg3_pct': 0.375, 'fg3a': 38},
        opponent_defense=opp_stats
    )
"""

import sqlite3
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def get_team_opponent_stats(team_id: int, season: str = '2025-26', split_type: str = 'overall') -> Dict:
    """
    Get opponent stats allowed by a team (defensive metrics).

    This returns what a team ALLOWS their opponents to do on average.
    For example:
    - opp_fg_pct_allowed = What FG% opponents shoot against this team
    - opp_3p_pct_allowed = What 3P% opponents shoot against this team
    - opp_pace_allowed = What pace opponents play at against this team

    Args:
        team_id: Team's NBA ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away'

    Returns:
        Dictionary of opponent stats, or empty dict if no data
    """
    try:
        conn = sqlite3.connect(NBA_DATA_DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                opp_fg_pct,
                opp_fg3_pct,
                opp_ft_pct,
                opp_rebounds,
                opp_assists,
                opp_tov,
                opp_pace,
                opp_off_rating,
                opp_def_rating,
                opp_points_in_paint,
                opp_fast_break_points,
                ppg as opp_ppg_allowed
            FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = ?
        ''', (team_id, season, split_type))

        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.warning(f"No opponent stats found for team {team_id}, season {season}, split {split_type}")
            return {}

        return {
            'opp_fg_pct_allowed': row[0],
            'opp_3p_pct_allowed': row[1],
            'opp_ft_pct_allowed': row[2],
            'opp_reb_allowed': row[3],
            'opp_ast_allowed': row[4],
            'opp_tov_forced': row[5],  # Lower is better for the opponent
            'opp_pace_allowed': row[6],
            'opp_off_rtg_allowed': row[7],
            'opp_def_rtg_allowed': row[8],
            'opp_paint_pts_allowed': row[9],
            'opp_fastbreak_pts_allowed': row[10],
            'opp_ppg_allowed': row[11],
        }

    except Exception as e:
        logger.error(f"Error getting opponent stats for team {team_id}: {e}")
        return {}


def compute_matchup_adjustment(
    team_offense: Dict,
    opponent_defense: Dict,
    team_name: str = "Team"
) -> Dict:
    """
    Compute scoring adjustments based on team offense vs opponent defense matchup.

    This compares a team's offensive capabilities against what the opponent's
    defense typically allows. For example:
    - Team shoots 47.5% FG, opponent allows 46.5% FG → +1% advantage → +2 pts
    - Team shoots 37% from 3, opponent allows 35% from 3 → +2% advantage → favorable

    Args:
        team_offense: Team's offensive stats (fg_pct, fg3_pct, fg3a, etc.)
        opponent_defense: Opponent's defensive stats (what they allow)
        team_name: Team name for logging (optional)

    Returns:
        Dictionary with:
            - total_adjustment: Total points adjustment
            - fg_pct_adjustment: Adjustment from FG% matchup
            - three_pt_adjustment: Adjustment from 3P% matchup
            - pace_adjustment: Adjustment from pace matchup
            - details: List of human-readable adjustment descriptions
    """
    adjustments = {
        'total_adjustment': 0.0,
        'fg_pct_adjustment': 0.0,
        'three_pt_adjustment': 0.0,
        'pace_adjustment': 0.0,
        'details': []
    }

    # Return early if missing data
    if not team_offense or not opponent_defense:
        logger.debug(f"{team_name}: Missing matchup data for opponent stats adjustment")
        return adjustments

    # ========================================================================
    # 1. FG% MATCHUP: Compare team's FG% to what opponent allows
    # ========================================================================
    team_fg = team_offense.get('fg_pct')
    opp_allows_fg = opponent_defense.get('opp_fg_pct_allowed')

    if team_fg and opp_allows_fg:
        # Calculate advantage as percentage points
        fg_advantage = (team_fg - opp_allows_fg) * 100  # e.g., 47.5% - 46.5% = +1.0%

        # Convert to points: +1% FG advantage = +2 pts (conservative multiplier)
        # A team taking 85 FGA with +1% FG% = 0.85 more FGM = 1.7 pts
        # Using 2x multiplier for reasonable impact
        fg_adjustment = fg_advantage * 2.0

        # Cap at ±5 points to avoid extreme adjustments
        fg_adjustment = max(min(fg_adjustment, 5.0), -5.0)

        adjustments['fg_pct_adjustment'] = fg_adjustment
        adjustments['total_adjustment'] += fg_adjustment

        if abs(fg_adjustment) > 0.5:
            direction = "favorable" if fg_adjustment > 0 else "tough"
            adjustments['details'].append(
                f"{team_name} FG% matchup: {direction} ({fg_advantage:+.1f}% edge → {fg_adjustment:+.1f} pts)"
            )

    # ========================================================================
    # 2. 3PT MATCHUP: Compare team's 3P% to what opponent allows
    # ========================================================================
    team_3p = team_offense.get('fg3_pct')
    opp_allows_3p = opponent_defense.get('opp_3p_pct_allowed')
    team_3pa = team_offense.get('fg3a', 35)  # Default to league average 35 3PA

    if team_3p and opp_allows_3p and team_3pa:
        # Calculate advantage
        three_advantage = (team_3p - opp_allows_3p) * 100  # e.g., 37% - 35% = +2.0%

        # Convert to points based on team's 3PA volume
        # +1% 3P% with 35 attempts = 0.35 more 3PM = 1.05 pts
        # Multiply by 3 (points per make) and scale by attempts
        three_adjustment = (three_advantage / 100) * team_3pa * 3.0

        # Cap at ±4 points
        three_adjustment = max(min(three_adjustment, 4.0), -4.0)

        adjustments['three_pt_adjustment'] = three_adjustment
        adjustments['total_adjustment'] += three_adjustment

        if abs(three_adjustment) > 0.5:
            direction = "favorable" if three_adjustment > 0 else "tough"
            adjustments['details'].append(
                f"{team_name} 3P% matchup: {direction} ({three_advantage:+.1f}% edge → {three_adjustment:+.1f} pts)"
            )

    # ========================================================================
    # 3. PACE MATCHUP: Compare team's pace to what opponent allows
    # ========================================================================
    team_pace = team_offense.get('pace')
    opp_allows_pace = opponent_defense.get('opp_pace_allowed')

    if team_pace and opp_allows_pace:
        # Calculate pace difference
        pace_diff = team_pace - opp_allows_pace  # e.g., 102 - 98 = +4

        # Pace adjustment: Each +1 possession = ~1.1 pts (league avg efficiency)
        # But apply conservative 50% multiplier since pace is already factored elsewhere
        pace_adjustment = pace_diff * 1.1 * 0.5

        # Cap at ±3 points
        pace_adjustment = max(min(pace_adjustment, 3.0), -3.0)

        adjustments['pace_adjustment'] = pace_adjustment
        adjustments['total_adjustment'] += pace_adjustment

        if abs(pace_adjustment) > 0.5:
            direction = "faster" if pace_diff > 0 else "slower"
            adjustments['details'].append(
                f"{team_name} pace matchup: {direction} than opponent allows ({pace_diff:+.1f} → {pace_adjustment:+.1f} pts)"
            )

    # ========================================================================
    # 4. CAP TOTAL ADJUSTMENT
    # ========================================================================
    # Prevent extreme total adjustments from stacking
    adjustments['total_adjustment'] = max(min(adjustments['total_adjustment'], 10.0), -10.0)

    # Log summary if any adjustment
    if abs(adjustments['total_adjustment']) > 0.1:
        logger.info(f"{team_name} opponent matchup adjustment: {adjustments['total_adjustment']:+.1f} pts")
        for detail in adjustments['details']:
            logger.info(f"  {detail}")

    return adjustments


if __name__ == '__main__':
    # Test the module
    print("Testing Opponent Matchup Stats Module\n")

    # Test 1: Get opponent stats for a team
    print("1. Testing get_team_opponent_stats():")
    team_id = 1610612737  # Atlanta Hawks
    opp_stats = get_team_opponent_stats(team_id, '2025-26', 'overall')

    if opp_stats:
        print(f"   Team {team_id} opponent stats (what they ALLOW):")
        print(f"     Opp FG%: {opp_stats.get('opp_fg_pct_allowed', 'N/A')}")
        print(f"     Opp 3P%: {opp_stats.get('opp_3p_pct_allowed', 'N/A')}")
        print(f"     Opp Pace: {opp_stats.get('opp_pace_allowed', 'N/A')}")
        print(f"     Opp PPG: {opp_stats.get('opp_ppg_allowed', 'N/A')}")
    else:
        print("   No opponent stats found")

    # Test 2: Compute matchup adjustment
    print("\n2. Testing compute_matchup_adjustment():")
    team_offense = {
        'fg_pct': 0.475,  # 47.5% FG
        'fg3_pct': 0.375,  # 37.5% 3P
        'fg3a': 38,  # 38 3PA per game
        'pace': 102.0
    }

    adjustment = compute_matchup_adjustment(team_offense, opp_stats, "Test Team")

    print(f"   Total adjustment: {adjustment['total_adjustment']:+.1f} pts")
    print(f"   FG% adjustment: {adjustment['fg_pct_adjustment']:+.1f} pts")
    print(f"   3P% adjustment: {adjustment['three_pt_adjustment']:+.1f} pts")
    print(f"   Pace adjustment: {adjustment['pace_adjustment']:+.1f} pts")
    print(f"   Details:")
    for detail in adjustment['details']:
        print(f"     - {detail}")
