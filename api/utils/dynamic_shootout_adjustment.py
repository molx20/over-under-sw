"""
Dynamic 3-Point Shootout Adjustment

Context-aware 3PT scoring adjustment that accounts for:
- Team shooting talent vs league average
- Opponent 3PT defense quality
- Recent shooting form (last 5 games)
- Projected game pace
- Rest/fatigue status

This replaces simple "if 3PM > threshold then bonus" rules with a nuanced
scoring system that correctly identifies shootout games like LAL/BOS, DEN/ATL, UTA/NYK.
"""


def calculate_shootout_bonus(
    team_3p_pct: float,
    league_avg_3p_pct: float,
    opponent_3p_allowed_pct: float,
    last5_3p_pct: float,
    season_3p_pct: float,
    projected_pace: float,
    rest_days: int,
    on_back_to_back: bool
) -> dict:
    """
    Calculate dynamic 3-point shootout bonus for a team.

    This function implements a sophisticated scoring system that identifies
    high-scoring 3PT environments based on multiple contextual factors.

    Args:
        team_3p_pct: Team's season 3PT% (0.0 to 1.0, e.g., 0.380 for 38%)
        league_avg_3p_pct: League average 3PT% (0.0 to 1.0)
        opponent_3p_allowed_pct: Opponent's 3PT% allowed (0.0 to 1.0)
        last5_3p_pct: Team's last 5 games 3PT% (0.0 to 1.0)
        season_3p_pct: Team's season 3PT% (same as team_3p_pct, for clarity)
        projected_pace: Projected game pace (possessions per 48 min, ~100 is average)
        rest_days: Number of rest days before this game (0, 1, 2, 3+)
        on_back_to_back: True if team is playing back-to-back

    Returns:
        Dict with:
            shootout_bonus: Points to add to team's projection (0.0+)
            shootout_score: Raw score before tiering (for debugging)
            breakdown: Dict of individual component scores
            tier: Description of shootout tier ('high', 'medium', 'low', 'none')

    Formula:
        Team_3PT_Ability = (team_3p_pct - league_avg_3p_pct) × 100
        Opponent_3PT_Defense = (opponent_3p_allowed_pct - league_avg_3p_pct) × 100
        Recent_3PT_Trend = (last5_3p_pct - season_3p_pct) × 50
        Pace_Factor = (projected_pace - 100) × 0.15
        Rest_Factor = +1.0 if rest_days >= 2, -1.5 if back-to-back, else 0

        Shootout_Score = sum of all components

        Bonus Tiers:
            Score > 10: bonus = score × 0.8 (high-confidence)
            Score > 6:  bonus = score × 0.6 (medium-confidence)
            Score > 3:  bonus = score × 0.4 (low-confidence)
            Score ≤ 3:  bonus = 0 (no adjustment)
    """

    # ========================================================================
    # SUB-SCORE 1: Team 3PT Ability Score
    # ========================================================================
    # Measures how much better (or worse) the team shoots compared to league average
    # Example: Team shoots 41%, league avg 36% → (0.41 - 0.36) × 100 = 5.0
    team_3pt_ability_score = (team_3p_pct - league_avg_3p_pct) * 100

    # ========================================================================
    # SUB-SCORE 2: Opponent 3PT Defense Score
    # ========================================================================
    # Measures how much better (or worse) opponent defends the 3PT line
    # Positive = opponent allows more 3s (weak defense)
    # Negative = opponent allows fewer 3s (strong defense)
    # Example: Opponent allows 39%, league avg 36% → (0.39 - 0.36) × 100 = 3.0
    opponent_3pt_defense_score = (opponent_3p_allowed_pct - league_avg_3p_pct) * 100

    # ========================================================================
    # SUB-SCORE 3: Recent 3PT Trend Score
    # ========================================================================
    # Measures if team is shooting better/worse than their season average recently
    # Example: Recent 43%, season 38% → (0.43 - 0.38) × 50 = 2.5
    recent_3pt_trend_score = (last5_3p_pct - season_3p_pct) * 50

    # ========================================================================
    # SUB-SCORE 4: Pace Factor
    # ========================================================================
    # Faster games = more possessions = more 3PT attempts
    # Example: Pace 105 → (105 - 100) × 0.15 = 0.75
    pace_factor = (projected_pace - 100) * 0.15

    # ========================================================================
    # SUB-SCORE 5: Rest Factor
    # ========================================================================
    # Fresh legs shoot better, tired legs shoot worse
    if rest_days >= 2:
        rest_factor = 1.0  # Fresh legs, better shooting
    elif on_back_to_back:
        rest_factor = -1.5  # Tired legs, worse shooting
    else:
        rest_factor = 0.0  # Normal situation (1 day rest)

    # ========================================================================
    # COMBINE INTO SHOOTOUT SCORE
    # ========================================================================
    shootout_score = (
        team_3pt_ability_score +
        opponent_3pt_defense_score +
        recent_3pt_trend_score +
        pace_factor +
        rest_factor
    )

    # ========================================================================
    # CONVERT TO SHOOTOUT BONUS USING TIERS
    # ========================================================================
    if shootout_score > 10:
        # High-confidence shootout environment
        shootout_bonus = shootout_score * 0.8
        tier = 'high'
    elif shootout_score > 6:
        # Medium-confidence shootout environment
        shootout_bonus = shootout_score * 0.6
        tier = 'medium'
    elif shootout_score > 3:
        # Low-confidence shootout environment
        shootout_bonus = shootout_score * 0.4
        tier = 'low'
    else:
        # No meaningful 3PT-driven boost
        shootout_bonus = 0.0
        tier = 'none'

    # ========================================================================
    # RETURN DETAILED BREAKDOWN
    # ========================================================================
    return {
        'shootout_bonus': round(shootout_bonus, 2),
        'shootout_score': round(shootout_score, 2),
        'tier': tier,
        'breakdown': {
            'team_3pt_ability': round(team_3pt_ability_score, 2),
            'opponent_3pt_defense': round(opponent_3pt_defense_score, 2),
            'recent_3pt_trend': round(recent_3pt_trend_score, 2),
            'pace_factor': round(pace_factor, 2),
            'rest_factor': round(rest_factor, 2)
        }
    }
