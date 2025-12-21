"""
Defense Quality Adjustment for NBA Predictions

This module implements a supplementary defense adjustment based purely on the
opponent's defensive rank (1-30). This adjustment works alongside the existing
dynamic defense adjustment to provide additional context about the quality of
the opposing defense.

The system uses linear interpolation within tiers to create smooth, proportional
adjustments based on defensive rank:
- Elite defenses (ranks 1-10): Reduce scoring expectations
- Average defenses (ranks 11-19): No adjustment
- Bad defenses (ranks 20-30): Increase scoring expectations
"""


def calculate_defense_quality_adjustment(opponent_def_rank: int) -> float:
    """
    Calculate scoring adjustment based on opponent's defensive rank.

    This function provides a supplementary defense adjustment that scales
    proportionally with the opponent's defensive rank. It uses linear
    interpolation within three tiers to ensure smooth transitions.

    Args:
        opponent_def_rank: Opponent's defensive rank (1-30)
                          1 = Best defense in league
                          30 = Worst defense in league

    Returns:
        float: Adjustment value from -6.0 to +5.0
              Negative = Playing against elite defense (score less)
              Zero = Playing against average defense (no adjustment)
              Positive = Playing against bad defense (score more)

    Adjustment Tiers:
        Elite Defense (Ranks 1-10):
            - Range: -6.0 to -4.0
            - Linear interpolation within tier
            - Rank 1 (best): -6.0
            - Rank 5: -5.0
            - Rank 10: -4.0
            - Rationale: Elite defenses significantly reduce scoring

        Average Defense (Ranks 11-19):
            - Range: 0.0 (flat)
            - No adjustment for middle-tier defenses
            - Rationale: Average defenses don't need special treatment

        Bad Defense (Ranks 20-30):
            - Range: +3.0 to +5.0
            - Linear interpolation within tier
            - Rank 20: +3.0
            - Rank 25: +4.0
            - Rank 30 (worst): +5.0
            - Rationale: Bad defenses inflate scoring opportunities

    Formula:
        Elite Tier (1-10):
            adjustment = -6.0 + ((rank - 1) × (2.0 / 9))
            Interpolates from -6.0 (rank 1) to -4.0 (rank 10)

        Average Tier (11-19):
            adjustment = 0.0
            No adjustment for average defenses

        Bad Tier (20-30):
            adjustment = 3.0 + ((rank - 20) × (2.0 / 10))
            Interpolates from +3.0 (rank 20) to +5.0 (rank 30)

    Examples:
        >>> calculate_defense_quality_adjustment(1)  # Best defense
        -6.0

        >>> calculate_defense_quality_adjustment(5)  # Elite defense
        -5.11

        >>> calculate_defense_quality_adjustment(10)  # Good defense
        -4.0

        >>> calculate_defense_quality_adjustment(11)  # Average defense
        0.0

        >>> calculate_defense_quality_adjustment(15)  # Average defense
        0.0

        >>> calculate_defense_quality_adjustment(19)  # Average defense
        0.0

        >>> calculate_defense_quality_adjustment(20)  # Bad defense
        3.0

        >>> calculate_defense_quality_adjustment(25)  # Very bad defense
        4.0

        >>> calculate_defense_quality_adjustment(30)  # Worst defense
        5.0

    Design Rationale:
        1. **Linear interpolation within tiers:** Ensures smooth scaling
           rather than discrete jumps. A rank 5 defense should be penalized
           more than rank 10, but less than rank 1.

        2. **Asymmetric ranges:** Elite defenses get -6.0 to -4.0 (2-point range),
           while bad defenses get +3.0 to +5.0 (2-point range). This reflects
           that elite defenses are more impactful than bad defenses.

        3. **Zero for average:** Ranks 11-19 (middle third) get no adjustment
           because they represent league-average defense. This prevents
           unnecessary noise in predictions.

        4. **Proportional scaling:** The adjustment scales smoothly across
           ranks, so rank 3 is between rank 1 and rank 5 in penalty.

        5. **Conservative on bad defenses:** Bad defenses only get +3.0 to +5.0,
           not as extreme as elite penalty. This prevents over-inflation against
           weak defenses.

    Integration Notes:
        - This is a SUPPLEMENTARY adjustment to the existing dynamic defense
          adjustment, not a replacement
        - Apply this AFTER the dynamic defense adjustment
        - Can be combined additively with other defensive factors
        - Consider the interaction with the existing defense tiers system
        - May need to tune the ranges (-6 to -4, +3 to +5) based on testing

    Relationship to Existing System:
        The existing dynamic defense adjustment uses:
        - Elite tier: 0.90-1.00 multiplier
        - Good tier: 1.00-1.05 multiplier
        - Average tier: 1.05-1.10 multiplier
        - Bad tier: 1.10-1.20 multiplier

        This new adjustment is ADDITIVE (points added/subtracted), while the
        existing system is MULTIPLICATIVE (scaling factor). They complement
        each other:
        - Dynamic adjustment: Scales the entire prediction
        - Quality adjustment: Adds/subtracts fixed points

    Data Quality:
        - Input validation ensures rank is clamped to 1-30 range
        - Function handles edge cases (rank 0, rank 31+) gracefully
        - Returns rounded values for cleaner results

    Usage Example in Prediction Pipeline:
        ```python
        # After dynamic defense adjustment
        prediction = apply_dynamic_defense_adjustment(prediction, ...)

        # Add quality adjustment
        opponent_rank = get_opponent_def_rank(opponent_team_id)
        quality_adj = calculate_defense_quality_adjustment(opponent_rank)
        prediction += quality_adj
        ```

    Testing Considerations:
        - Test all three tiers (elite, average, bad)
        - Test boundary values (ranks 1, 10, 11, 19, 20, 30)
        - Test interpolation within elite tier (ranks 1-10)
        - Test interpolation within bad tier (ranks 20-30)
        - Test input validation (rank 0, rank 35)
    """

    # ========================================================================
    # STEP 1: INPUT VALIDATION (CLAMP TO 1-30 RANGE)
    # ========================================================================
    # Ensure opponent_def_rank is within valid NBA range (30 teams)
    # Handle edge cases where data might be out of bounds

    if opponent_def_rank < 1:
        opponent_def_rank = 1
    elif opponent_def_rank > 30:
        opponent_def_rank = 30

    # ========================================================================
    # STEP 2: DETERMINE TIER AND CALCULATE ADJUSTMENT
    # ========================================================================

    if 1 <= opponent_def_rank <= 10:
        # ====================================================================
        # ELITE DEFENSE TIER (RANKS 1-10)
        # ====================================================================
        # These are the top 10 defenses in the league
        # Penalty ranges from -6.0 (rank 1) to -4.0 (rank 10)
        # Use linear interpolation for smooth scaling
        #
        # Formula: -6.0 + ((rank - 1) × slope)
        # Slope = (target_max - target_min) / (rank_range - 1)
        # Slope = (-4.0 - (-6.0)) / (10 - 1) = 2.0 / 9 ≈ 0.222
        #
        # Examples:
        #   Rank 1: -6.0 + ((1 - 1) × 0.222) = -6.0
        #   Rank 5: -6.0 + ((5 - 1) × 0.222) = -6.0 + 0.888 = -5.11
        #   Rank 10: -6.0 + ((10 - 1) × 0.222) = -6.0 + 2.0 = -4.0

        adjustment = -6.0 + ((opponent_def_rank - 1) * (2.0 / 9))
        return round(adjustment, 2)

    elif 11 <= opponent_def_rank <= 19:
        # ====================================================================
        # AVERAGE DEFENSE TIER (RANKS 11-19)
        # ====================================================================
        # These are middle-tier defenses (roughly 33rd to 63rd percentile)
        # No adjustment needed - they represent league average
        # Rationale: Don't over-engineer adjustments for average teams

        return 0.0

    elif 20 <= opponent_def_rank <= 30:
        # ====================================================================
        # BAD DEFENSE TIER (RANKS 20-30)
        # ====================================================================
        # These are the bottom 11 defenses in the league
        # Bonus ranges from +3.0 (rank 20) to +5.0 (rank 30)
        # Use linear interpolation for smooth scaling
        #
        # Formula: 3.0 + ((rank - 20) × slope)
        # Slope = (target_max - target_min) / (rank_range)
        # Slope = (5.0 - 3.0) / (30 - 20) = 2.0 / 10 = 0.2
        #
        # Examples:
        #   Rank 20: 3.0 + ((20 - 20) × 0.2) = 3.0
        #   Rank 25: 3.0 + ((25 - 20) × 0.2) = 3.0 + 1.0 = 4.0
        #   Rank 30: 3.0 + ((30 - 20) × 0.2) = 3.0 + 2.0 = 5.0

        adjustment = 3.0 + ((opponent_def_rank - 20) * (2.0 / 10))
        return round(adjustment, 2)

    # ========================================================================
    # FALLBACK (SHOULD NEVER REACH HERE DUE TO VALIDATION)
    # ========================================================================
    # If somehow we get here, return 0.0 as safe default
    return 0.0
