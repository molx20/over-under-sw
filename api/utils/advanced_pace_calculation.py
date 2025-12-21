"""
Advanced Pace Calculation for NBA Game Predictions

This module implements a sophisticated pace projection system that goes beyond
simple season pace averaging. It accounts for:
- Recent pace trends (last 5 games)
- Pace mismatches (slow teams drag games down)
- Turnover-driven pace increases (more turnovers = faster breaks)
- Free throw rate impacts (more FTs = slower clock stoppages)
- Elite defense effects (defensive grind games)

The result is a more accurate pace projection that captures high-turnover games,
free-throw-heavy games, and defensive battles.
"""


def calculate_advanced_pace(
    team1_season_pace: float,
    team1_last5_pace: float,
    team2_season_pace: float,
    team2_last5_pace: float,
    team1_season_turnovers: float,
    team2_season_turnovers: float,
    team1_ft_rate: float,
    team2_ft_rate: float,
    team1_is_elite_defense: bool,
    team2_is_elite_defense: bool
) -> dict:
    """
    Calculate projected game pace using advanced context-aware formula.

    This function implements a multi-factor pace calculation that blends season
    and recent pace, then adjusts for turnovers, free throw rate, pace mismatches,
    and elite defenses.

    Args:
        team1_season_pace: Team 1's season average pace (possessions per 48 min)
        team1_last5_pace: Team 1's last 5 games average pace
        team2_season_pace: Team 2's season average pace
        team2_last5_pace: Team 2's last 5 games average pace
        team1_season_turnovers: Team 1's season average turnovers per game
        team2_season_turnovers: Team 2's season average turnovers per game
        team1_ft_rate: Team 1's free throw rate (FTA / FGA)
        team2_ft_rate: Team 2's free throw rate (FTA / FGA)
        team1_is_elite_defense: True if Team 1 has elite defense (top 10)
        team2_is_elite_defense: True if Team 2 has elite defense (top 10)

    Returns:
        Dict with:
            final_pace: Projected game pace (clamped to 92-108 range)
            breakdown: Dict of all component values for debugging
            adjustments: Dict of all adjustment values applied

    Formula:
        1. Blend season (60%) + recent (40%) pace for each team
        2. Average the two adjusted paces (Base_Pace)
        3. Apply pace mismatch penalty if teams differ significantly
        4. Apply turnover-driven pace boost (high turnovers = faster)
        5. Apply free throw rate penalty (high FT rate = slower)
        6. Apply elite defense penalty (defensive grind = slower)
        7. Clamp final result to 92-108 range
    """

    # ========================================================================
    # STEP 1: ADJUSTED PACE PER TEAM (SEASON + RECENT BLEND)
    # ========================================================================
    # Blend season pace (60% weight) with last 5 games pace (40% weight)
    # This makes the model lean on season trends but still react to recent tempo changes
    # Rationale: Season pace is more stable, but recent trends show current playing style

    team1_adjusted_pace = (team1_season_pace * 0.60) + (team1_last5_pace * 0.40)
    team2_adjusted_pace = (team2_season_pace * 0.60) + (team2_last5_pace * 0.40)

    # ========================================================================
    # STEP 2: BASE PACE (AVERAGE OF BOTH TEAMS)
    # ========================================================================
    # Take the average of both teams' adjusted paces as the starting point
    # This assumes both teams equally influence the game's tempo

    base_pace = (team1_adjusted_pace + team2_adjusted_pace) / 2

    # ========================================================================
    # STEP 3: PACE MISMATCH PENALTY (SLOWER TEAM DRAGS GAME DOWN)
    # ========================================================================
    # When one team is much slower, they tend to drag the overall pace down
    # This happens because the slow team will walk the ball up and run clock
    # Examples: Warriors (fast) vs Grizzlies (slow) = slower than average of both

    pace_difference = abs(team1_adjusted_pace - team2_adjusted_pace)

    if pace_difference > 8:
        # Large mismatch (e.g., 105 pace vs 95 pace)
        # Slow team significantly drags tempo down
        pace_mismatch_penalty = -2.0
    elif pace_difference > 5:
        # Moderate mismatch (e.g., 102 pace vs 96 pace)
        # Noticeable drag on tempo
        pace_mismatch_penalty = -1.0
    else:
        # Teams play at similar pace (difference ≤ 5)
        # No significant drag effect
        pace_mismatch_penalty = 0.0

    # ========================================================================
    # STEP 4: TURNOVER-DRIVEN PACE IMPACT (MORE TURNOVERS = FASTER PACE)
    # ========================================================================
    # Turnovers create transition opportunities and fast breaks
    # High-turnover games tend to be faster because:
    # - Steals lead to fast breaks
    # - Live-ball turnovers create quick possession changes
    # - Less time spent in half-court sets

    projected_turnovers = (team1_season_turnovers + team2_season_turnovers) / 2

    if projected_turnovers > 15:
        # High-turnover game (above 15 per team average)
        # Each additional turnover above 15 adds 0.3 possessions
        # Example: 18 turnovers → (18 - 15) × 0.3 = +0.9 pace
        turnover_pace_impact = (projected_turnovers - 15) * 0.3
    else:
        # Normal or low-turnover game
        # No pace boost from turnovers
        turnover_pace_impact = 0.0

    # ========================================================================
    # STEP 5: FREE THROW RATE IMPACT (MORE FTS = SLOWER PACE)
    # ========================================================================
    # Free throws stop the clock and slow down the game tempo
    # High FT rate games are slower because:
    # - Clock stops during free throw attempts
    # - Teams can't run in transition after made FTs
    # - More fouls = more dead ball situations

    combined_ft_rate = (team1_ft_rate + team2_ft_rate) / 2

    if combined_ft_rate > 0.25:
        # High free throw rate (above 25% = 1 FTA per 4 FGA)
        # Each additional 0.01 in FT rate slows pace by 0.10
        # Example: FT rate of 0.30 → (0.30 - 0.25) × 10 = -0.5 pace
        ft_pace_penalty = (combined_ft_rate - 0.25) * 10
    else:
        # Normal or low free throw rate
        # No pace penalty
        ft_pace_penalty = 0.0

    # ========================================================================
    # STEP 6: ELITE DEFENSE PACE PENALTY (DEFENSIVE GRIND GAMES)
    # ========================================================================
    # Elite defenses slow games down through:
    # - Better half-court defense (longer possessions)
    # - Fewer easy transition buckets
    # - Forcing teams into slower, more deliberate offense
    # - Examples: Celtics, Timberwolves defensive games are slower

    if team1_is_elite_defense or team2_is_elite_defense:
        # At least one elite defense present
        # Game becomes more of a defensive grind
        defense_pace_penalty = -1.5
    else:
        # No elite defenses
        # No defensive grinding effect
        defense_pace_penalty = 0.0

    # ========================================================================
    # STEP 7: FINAL PACE CALCULATION (COMBINE ALL COMPONENTS)
    # ========================================================================
    # Combine base pace with all adjustments:
    # - Add pace mismatch penalty (negative value)
    # - Add turnover-driven boost (positive value)
    # - Subtract FT penalty (slows game)
    # - Add defense penalty (negative value)

    final_pace = (
        base_pace +
        pace_mismatch_penalty +
        turnover_pace_impact -
        ft_pace_penalty +  # Note: subtracting because it's a penalty (positive value)
        defense_pace_penalty
    )

    # ========================================================================
    # STEP 8: CLAMP TO REALISTIC NBA RANGE (92-108)
    # ========================================================================
    # NBA pace rarely goes below 92 or above 108 possessions per game
    # Clamping prevents unrealistic extreme projections
    # - 92 = very slow defensive battle (e.g., Grizzlies vs Knicks)
    # - 108 = very fast shootout (e.g., Kings vs Pacers)

    pace_before_clamp = final_pace

    if final_pace < 92:
        final_pace = 92
    elif final_pace > 108:
        final_pace = 108

    # ========================================================================
    # RETURN DETAILED BREAKDOWN FOR DEBUGGING AND TRANSPARENCY
    # ========================================================================
    return {
        'final_pace': round(final_pace, 2),
        'pace_before_clamp': round(pace_before_clamp, 2),
        'breakdown': {
            'team1_adjusted_pace': round(team1_adjusted_pace, 2),
            'team2_adjusted_pace': round(team2_adjusted_pace, 2),
            'base_pace': round(base_pace, 2),
            'pace_difference': round(pace_difference, 2)
        },
        'adjustments': {
            'pace_mismatch_penalty': round(pace_mismatch_penalty, 2),
            'turnover_pace_impact': round(turnover_pace_impact, 2),
            'ft_pace_penalty': round(ft_pace_penalty, 2),
            'defense_pace_penalty': round(defense_pace_penalty, 2)
        },
        'context': {
            'projected_turnovers': round(projected_turnovers, 2),
            'combined_ft_rate': round(combined_ft_rate, 3),
            'has_elite_defense': team1_is_elite_defense or team2_is_elite_defense,
            'clamped': pace_before_clamp != final_pace
        }
    }
