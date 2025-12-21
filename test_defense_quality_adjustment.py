"""
Test Suite for Defense Quality Adjustment

Validates all components of the defense quality adjustment formula:
- Elite defenses (ranks 1-10): -6.0 to -4.0 linear interpolation
- Average defenses (ranks 11-19): 0.0 flat
- Bad defenses (ranks 20-30): +3.0 to +5.0 linear interpolation
- Input validation and edge cases
- Tier boundary verification
- Linear interpolation verification
"""

from api.utils.defense_quality_adjustment import calculate_defense_quality_adjustment


def test_defense_quality_adjustment():
    """Test various defense quality adjustment scenarios"""

    print("=" * 80)
    print("DEFENSE QUALITY ADJUSTMENT - TEST SCENARIOS")
    print("=" * 80)

    # Test 1: Elite defenses (ranks 1-10) - Linear interpolation from -6.0 to -4.0
    print("\nTest 1: Elite Defense Tier (Ranks 1-10)")
    print("-" * 80)

    elite_test_cases = [
        (1, -6.0, "Best defense in league"),
        (3, -5.56, "Elite defense (rank 3)"),
        (5, -5.11, "Elite defense (rank 5)"),
        (7, -4.67, "Elite defense (rank 7)"),
        (10, -4.0, "Bottom of elite tier"),
    ]

    print("Rank | Expected | Actual | Description")
    print("-" * 60)

    for rank, expected, description in elite_test_cases:
        result = calculate_defense_quality_adjustment(rank)
        print(f" {rank:2d}  | {expected:>7.2f}  | {result:>6.2f} | {description}")
        assert abs(result - expected) < 0.02, f"Rank {rank}: Expected {expected}, got {result}"

    print("✓ PASS - Elite defenses (1-10) get penalties from -6.0 to -4.0")

    # Test 2: Average defenses (ranks 11-19) - All get 0.0
    print("\nTest 2: Average Defense Tier (Ranks 11-19)")
    print("-" * 80)

    average_ranks = [11, 13, 15, 17, 19]

    print("Rank | Expected | Actual")
    print("-" * 40)

    for rank in average_ranks:
        result = calculate_defense_quality_adjustment(rank)
        print(f" {rank:2d}  |     0.0  | {result:>6.2f}")
        assert result == 0.0, f"Rank {rank}: Expected 0.0, got {result}"

    print("✓ PASS - Average defenses (11-19) get no adjustment (0.0)")

    # Test 3: Bad defenses (ranks 20-30) - Linear interpolation from +3.0 to +5.0
    print("\nTest 3: Bad Defense Tier (Ranks 20-30)")
    print("-" * 80)

    bad_test_cases = [
        (20, 3.0, "Top of bad tier"),
        (23, 3.6, "Bad defense (rank 23)"),
        (25, 4.0, "Very bad defense"),
        (27, 4.4, "Very bad defense (rank 27)"),
        (30, 5.0, "Worst defense in league"),
    ]

    print("Rank | Expected | Actual | Description")
    print("-" * 60)

    for rank, expected, description in bad_test_cases:
        result = calculate_defense_quality_adjustment(rank)
        print(f" {rank:2d}  | {expected:>7.2f}  | {result:>6.2f} | {description}")
        assert abs(result - expected) < 0.02, f"Rank {rank}: Expected {expected}, got {result}"

    print("✓ PASS - Bad defenses (20-30) get bonuses from +3.0 to +5.0")

    # Test 4: Linear interpolation verification (elite tier)
    print("\nTest 4: Linear Interpolation - Elite Tier")
    print("-" * 80)

    # Elite tier formula: -6.0 + ((rank - 1) × (2.0 / 9))
    # Verify slope is consistent

    print("Rank | Adjustment | Delta from Previous")
    print("-" * 60)

    prev_result = None
    expected_slope = 2.0 / 9  # ≈ 0.222

    for rank in range(1, 11):
        result = calculate_defense_quality_adjustment(rank)

        if prev_result is None:
            print(f" {rank:2d}  | {result:>9.2f}  | (baseline)")
        else:
            delta = result - prev_result
            print(f" {rank:2d}  | {result:>9.2f}  | {delta:>+7.2f}")
            # Verify delta is approximately equal to expected slope
            assert abs(delta - expected_slope) < 0.01, f"Slope should be ~{expected_slope:.3f}, got {delta:.3f}"

        prev_result = result

    print(f"✓ PASS - Elite tier has consistent slope (~{expected_slope:.3f})")

    # Test 5: Linear interpolation verification (bad tier)
    print("\nTest 5: Linear Interpolation - Bad Tier")
    print("-" * 80)

    # Bad tier formula: 3.0 + ((rank - 20) × (2.0 / 10))
    # Verify slope is consistent

    print("Rank | Adjustment | Delta from Previous")
    print("-" * 60)

    prev_result = None
    expected_slope = 2.0 / 10  # = 0.2

    for rank in range(20, 31):
        result = calculate_defense_quality_adjustment(rank)

        if prev_result is None:
            print(f" {rank:2d}  | {result:>9.2f}  | (baseline)")
        else:
            delta = result - prev_result
            print(f" {rank:2d}  | {result:>9.2f}  | {delta:>+7.2f}")
            # Verify delta is approximately equal to expected slope
            assert abs(delta - expected_slope) < 0.01, f"Slope should be {expected_slope:.3f}, got {delta:.3f}"

        prev_result = result

    print(f"✓ PASS - Bad tier has consistent slope ({expected_slope:.1f})")

    # Test 6: Tier boundary verification
    print("\nTest 6: Tier Boundary Verification")
    print("-" * 80)

    boundaries = [
        (10, -4.0, "Elite/Average boundary (rank 10)"),
        (11, 0.0, "Elite/Average boundary (rank 11)"),
        (19, 0.0, "Average/Bad boundary (rank 19)"),
        (20, 3.0, "Average/Bad boundary (rank 20)"),
    ]

    print("Rank | Expected | Actual | Description")
    print("-" * 60)

    for rank, expected, description in boundaries:
        result = calculate_defense_quality_adjustment(rank)
        print(f" {rank:2d}  | {expected:>7.2f}  | {result:>6.2f} | {description}")
        assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"

    print("✓ PASS - Tier boundaries are correct")

    # Test 7: Input validation (edge cases)
    print("\nTest 7: Input Validation")
    print("-" * 80)

    # Test rank < 1 (should clamp to 1)
    result_low = calculate_defense_quality_adjustment(0)
    print(f"Rank 0 (invalid): {result_low} (clamped to rank 1)")
    assert result_low == -6.0, f"Should clamp to rank 1 (-6.0), got {result_low}"

    result_negative = calculate_defense_quality_adjustment(-5)
    print(f"Rank -5 (invalid): {result_negative} (clamped to rank 1)")
    assert result_negative == -6.0, f"Should clamp to rank 1 (-6.0), got {result_negative}"

    # Test rank > 30 (should clamp to 30)
    result_high = calculate_defense_quality_adjustment(31)
    print(f"Rank 31 (invalid): {result_high} (clamped to rank 30)")
    assert result_high == 5.0, f"Should clamp to rank 30 (+5.0), got {result_high}"

    result_very_high = calculate_defense_quality_adjustment(100)
    print(f"Rank 100 (invalid): {result_very_high} (clamped to rank 30)")
    assert result_very_high == 5.0, f"Should clamp to rank 30 (+5.0), got {result_very_high}"

    print("✓ PASS - Input validation handles edge cases correctly")

    # Test 8: Monotonicity verification (worse defense = higher adjustment)
    print("\nTest 8: Monotonicity Verification")
    print("-" * 80)

    all_ranks = list(range(1, 31))
    all_results = []

    print("Checking that adjustment increases as defense gets worse...")
    print("(Rank 1→30 should go from -6.0→+5.0)")

    for rank in all_ranks:
        result = calculate_defense_quality_adjustment(rank)
        all_results.append(result)

        if len(all_results) > 1:
            # Verify monotonic increase (or equal for average tier)
            assert result >= all_results[-2], f"Adjustment should increase or stay same, rank {rank}"

    print(f"Rank  1: {all_results[0]:>6.2f}")
    print(f"Rank 10: {all_results[9]:>6.2f}")
    print(f"Rank 11: {all_results[10]:>6.2f}")
    print(f"Rank 19: {all_results[18]:>6.2f}")
    print(f"Rank 20: {all_results[19]:>6.2f}")
    print(f"Rank 30: {all_results[29]:>6.2f}")

    print("✓ PASS - Adjustments increase monotonically as defense worsens")

    # Test 9: Return value precision
    print("\nTest 9: Return Value Precision")
    print("-" * 80)

    # Test that values are rounded to 2 decimal places
    test_ranks = [3, 7, 14, 23, 27]

    for rank in test_ranks:
        result = calculate_defense_quality_adjustment(rank)
        # Check that result has at most 2 decimal places
        result_str = str(result)
        if '.' in result_str:
            decimal_places = len(result_str.split('.')[1])
            print(f"Rank {rank:2d}: {result:>6.2f} ({decimal_places} decimal places)")
            assert decimal_places <= 2, f"Should have max 2 decimal places, got {decimal_places}"
        else:
            print(f"Rank {rank:2d}: {result:>6.2f} (integer)")

    print("✓ PASS - Return values properly rounded to 2 decimal places")

    # Test 10: Asymmetry verification
    print("\nTest 10: Asymmetry Verification")
    print("-" * 80)

    # Elite defenses: -6.0 to -4.0 (2-point range)
    # Bad defenses: +3.0 to +5.0 (2-point range)
    # Both ranges are 2 points, but elite starts at -6 while bad starts at +3

    elite_range = abs(-4.0 - (-6.0))
    bad_range = abs(5.0 - 3.0)

    print(f"Elite tier range: {elite_range:.1f} points ({-6.0} to {-4.0})")
    print(f"Bad tier range: {bad_range:.1f} points (+{3.0} to +{5.0})")

    assert elite_range == 2.0, "Elite range should be 2.0"
    assert bad_range == 2.0, "Bad range should be 2.0"

    # Verify that elite penalty is stronger than bad bonus
    best_defense_penalty = calculate_defense_quality_adjustment(1)
    worst_defense_bonus = calculate_defense_quality_adjustment(30)

    print(f"\nBest defense (rank 1): {best_defense_penalty}")
    print(f"Worst defense (rank 30): {worst_defense_bonus}")
    print(f"Elite penalty magnitude: {abs(best_defense_penalty):.1f}")
    print(f"Bad bonus magnitude: {abs(worst_defense_bonus):.1f}")

    assert abs(best_defense_penalty) > abs(worst_defense_bonus), \
        "Elite defense penalty should be stronger than bad defense bonus"

    print("✓ PASS - System correctly emphasizes elite defense impact")

    # Test 11: Complete tier coverage
    print("\nTest 11: Complete Tier Coverage (All Ranks 1-30)")
    print("-" * 80)

    print("Rank | Tier    | Adjustment")
    print("-" * 40)

    tier_counts = {"Elite": 0, "Average": 0, "Bad": 0}

    for rank in range(1, 31):
        result = calculate_defense_quality_adjustment(rank)

        if 1 <= rank <= 10:
            tier = "Elite"
            tier_counts["Elite"] += 1
            assert result < 0, f"Elite defense should have negative adjustment"
        elif 11 <= rank <= 19:
            tier = "Average"
            tier_counts["Average"] += 1
            assert result == 0.0, f"Average defense should have zero adjustment"
        else:  # 20-30
            tier = "Bad"
            tier_counts["Bad"] += 1
            assert result > 0, f"Bad defense should have positive adjustment"

        if rank <= 3 or 9 <= rank <= 12 or 19 <= rank <= 22 or rank >= 28:
            print(f" {rank:2d}  | {tier:7s} | {result:>+6.2f}")

    print(" ...  | ...     | ...")
    print()
    print(f"Elite tier: {tier_counts['Elite']} teams (ranks 1-10)")
    print(f"Average tier: {tier_counts['Average']} teams (ranks 11-19)")
    print(f"Bad tier: {tier_counts['Bad']} teams (ranks 20-30)")

    assert tier_counts["Elite"] == 10, "Should have 10 elite teams"
    assert tier_counts["Average"] == 9, "Should have 9 average teams"
    assert tier_counts["Bad"] == 11, "Should have 11 bad teams"

    print("✓ PASS - All 30 ranks covered correctly across 3 tiers")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
    print("\nSummary:")
    print("- Elite defenses (1-10): -6.0 to -4.0 with linear interpolation")
    print("- Average defenses (11-19): 0.0 flat")
    print("- Bad defenses (20-30): +3.0 to +5.0 with linear interpolation")
    print("- Linear interpolation verified (slopes consistent)")
    print("- Tier boundaries correct")
    print("- Input validation handles edge cases")
    print("- Monotonicity verified")
    print("- Return values properly formatted")
    print("- Asymmetry verified (elite impact > bad impact)")
    print("- All 30 ranks covered correctly")


if __name__ == "__main__":
    test_defense_quality_adjustment()
