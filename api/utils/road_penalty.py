"""
Road Penalty Calculation for NBA Away Team Predictions

This module implements a non-linear road penalty system that penalizes away teams
based on their road win percentage. The penalty is designed to:
- Give no penalty to teams with good road records (≥50%)
- Apply progressive penalties to below-average road teams
- Use tiered multipliers for different levels of road struggles
- Cap the maximum penalty to prevent over-penalization

The penalty system uses non-linear scaling to reflect that teams with very poor
road records (e.g., 25% win rate) struggle disproportionately more than teams
with mediocre road records (e.g., 45% win rate).
"""


def calculate_road_penalty(road_win_pct: float) -> float:
    """
    Calculate penalty for away teams based on their road win percentage.

    This function implements a non-linear penalty system with tiered multipliers
    that progressively penalize teams with poor road records. The penalty
    increases more aggressively for truly terrible road teams.

    Args:
        road_win_pct: Road win percentage (0.0 to 1.0)
                     Example: 0.350 = 35% road win rate

    Returns:
        float: Penalty value from -7.0 to 0.0
              - 0.0 = No penalty (good road teams, ≥50%)
              - -7.0 = Maximum penalty (catastrophic road teams, <20%)

    Penalty Tiers:
        Good Road Teams (≥50%):
            - No penalty (0.0)
            - These teams perform well on the road

        Below-Average Road Teams (40-49%):
            - Base penalty: -distance_below × 10.0
            - Multiplier: 1.0x
            - Range: 0.0 to -1.0
            - Example: 45% → -0.5 penalty

        Poor Road Teams (30-39%):
            - Base penalty: -distance_below × 10.0
            - Multiplier: 1.2x
            - Range: -1.2 to -2.4
            - Example: 35% → -1.8 penalty

        Catastrophic Road Teams (<30%):
            - Base penalty: -distance_below × 10.0
            - Multiplier: 1.4x
            - Range: -2.8 to -7.0 (capped)
            - Example: 25% → -3.5 penalty
            - Example: 15% → -4.9 penalty

    Formula:
        IF road_win_pct >= 0.50:
            penalty = 0.0
        ELSE:
            distance_below = 0.50 - road_win_pct
            base_penalty = -distance_below × 10.0

            IF road_win_pct < 0.30:
                penalty = base_penalty × 1.4  (catastrophic multiplier)
            ELSE IF 0.30 <= road_win_pct < 0.40:
                penalty = base_penalty × 1.2  (poor multiplier)
            ELSE:  # 0.40 <= road_win_pct < 0.50
                penalty = base_penalty × 1.0  (below-average multiplier)

            penalty = clamp(penalty, -7.0, 0.0)

    Examples:
        >>> calculate_road_penalty(0.600)  # Good road team (60%)
        0.0

        >>> calculate_road_penalty(0.500)  # Average road team (50%)
        0.0

        >>> calculate_road_penalty(0.450)  # Below-average (45%)
        -0.5

        >>> calculate_road_penalty(0.350)  # Poor road team (35%)
        -1.8

        >>> calculate_road_penalty(0.250)  # Catastrophic (25%)
        -3.5

        >>> calculate_road_penalty(0.150)  # Extremely bad (15%)
        -4.9

        >>> calculate_road_penalty(0.050)  # Worst case (5%)
        -6.3

    Design Rationale:
        1. **No penalty for good road teams:** Teams with ≥50% road win rate
           are competitive on the road and don't need penalization.

        2. **Linear base formula:** The distance below 50% is multiplied by 10
           to create a meaningful penalty scale (0.10 = -1.0 penalty).

        3. **Tiered multipliers:** Different multipliers for different tiers
           reflect that teams with very poor road records struggle more than
           their win percentage alone would suggest.
           - Below-average (40-49%): Normal penalty (1.0x)
           - Poor (30-39%): Enhanced penalty (1.2x)
           - Catastrophic (<30%): Strong penalty (1.4x)

        4. **-7.0 cap:** Prevents extreme over-penalization. Even the worst
           road teams can occasionally have good games.

        5. **Non-negative results:** Penalty is always ≤0, never positive.
           Good road teams get 0, not a bonus. Road advantage is handled
           separately by the home court advantage adjustment.

    Integration Notes:
        - Apply this penalty to the AWAY team's prediction only
        - Do NOT apply to home team
        - Apply AFTER home court advantage adjustment
        - Combine with other away-specific factors (travel, rest, etc.)
        - Consider applying before or after fatigue adjustment based on testing

    Data Quality:
        - Input validation ensures road_win_pct is clamped to 0.0-1.0 range
        - Function handles edge cases (0%, 100%) gracefully
        - Returns rounded values for cleaner results
    """

    # ========================================================================
    # STEP 1: INPUT VALIDATION (CLAMP TO 0.0-1.0 RANGE)
    # ========================================================================
    # Ensure road_win_pct is within valid percentage range
    # Handle edge cases where data might be slightly out of bounds

    if road_win_pct < 0.0:
        road_win_pct = 0.0
    elif road_win_pct > 1.0:
        road_win_pct = 1.0

    # ========================================================================
    # STEP 2: CHECK IF TEAM HAS GOOD ROAD RECORD (NO PENALTY)
    # ========================================================================
    # Teams with ≥50% road win rate don't get penalized
    # These teams are competitive on the road

    if road_win_pct >= 0.50:
        return 0.0

    # ========================================================================
    # STEP 3: CALCULATE BASE PENALTY (LINEAR DISTANCE FROM 50%)
    # ========================================================================
    # Calculate how far below 50% the team's road win rate is
    # Multiply by 10 to create meaningful penalty scale
    # Example: 40% road → distance 0.10 → base penalty -1.0

    distance_below = 0.50 - road_win_pct
    base_penalty = -distance_below * 10.0

    # ========================================================================
    # STEP 4: APPLY TIERED MULTIPLIER BASED ON SEVERITY
    # ========================================================================
    # Different tiers get different penalty multipliers
    # Worse road teams get progressively harsher penalties

    if road_win_pct < 0.30:
        # CATASTROPHIC ROAD TEAMS (<30% win rate)
        # These teams are genuinely terrible on the road
        # Apply 1.4x multiplier to reflect disproportionate struggles
        # Example: 25% → base -2.5 → penalty -3.5
        road_penalty = base_penalty * 1.4

    elif 0.30 <= road_win_pct < 0.40:
        # POOR ROAD TEAMS (30-39% win rate)
        # These teams struggle significantly on the road
        # Apply 1.2x multiplier for enhanced penalty
        # Example: 35% → base -1.5 → penalty -1.8
        road_penalty = base_penalty * 1.2

    else:  # 0.40 <= road_win_pct < 0.50
        # BELOW-AVERAGE ROAD TEAMS (40-49% win rate)
        # These teams are slightly below average on the road
        # Apply 1.0x multiplier (no enhancement)
        # Example: 45% → base -0.5 → penalty -0.5
        road_penalty = base_penalty * 1.0

    # ========================================================================
    # STEP 5: CLAMP TO MAXIMUM PENALTY (-7.0 TO 0.0)
    # ========================================================================
    # Prevent extreme over-penalization
    # Even worst road teams can have good games occasionally
    # Cap ensures penalty doesn't dominate other prediction factors

    if road_penalty < -7.0:
        road_penalty = -7.0
    elif road_penalty > 0.0:
        road_penalty = 0.0

    # ========================================================================
    # STEP 6: RETURN ROUNDED PENALTY VALUE
    # ========================================================================
    # Round to 2 decimal places for cleaner results

    return round(road_penalty, 2)
