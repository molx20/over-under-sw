"""
Test Suite for Road Penalty Calculation

Validates all components of the road penalty formula:
- Good road teams (≥50%): No penalty
- Below-average road teams (40-49%): 1.0x multiplier
- Poor road teams (30-39%): 1.2x multiplier
- Catastrophic road teams (<30%): 1.4x multiplier
- Input validation and edge cases
- Clamping to -7.0 to 0.0 range
- Tier boundary verification
"""

from api.utils.road_penalty import calculate_road_penalty


def test_road_penalty():
    """Test various road penalty calculation scenarios"""

    print("=" * 80)
    print("ROAD PENALTY CALCULATION - TEST SCENARIOS")
    print("=" * 80)

    # Test 1: Good road teams (≥50%) - No penalty
    print("\nTest 1: Good Road Teams (No Penalty)")
    print("-" * 80)

    test_cases_good = [
        (0.600, "Excellent road team (60%)"),
        (0.550, "Good road team (55%)"),
        (0.500, "Average road team (50%)"),
    ]

    for road_pct, description in test_cases_good:
        result = calculate_road_penalty(road_pct)
        print(f"{description}: {result}")
        assert result == 0.0, f"Expected 0.0 for {road_pct}, got {result}"

    print("✓ PASS - Good road teams (≥50%) receive no penalty")

    # Test 2: Below-average road teams (40-49%) - 1.0x multiplier
    print("\nTest 2: Below-Average Road Teams (1.0x Multiplier)")
    print("-" * 80)

    test_cases_below_avg = [
        (0.490, -0.1, "Just below average (49%)"),
        (0.450, -0.5, "Below-average (45%)"),
        (0.400, -1.0, "Bottom of tier (40%)"),
    ]

    for road_pct, expected, description in test_cases_below_avg:
        result = calculate_road_penalty(road_pct)
        print(f"{description}: {result} (expected: {expected})")
        assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"

    print("✓ PASS - Below-average teams (40-49%) get 1.0x base penalty")

    # Test 3: Poor road teams (30-39%) - 1.2x multiplier
    print("\nTest 3: Poor Road Teams (1.2x Multiplier)")
    print("-" * 80)

    test_cases_poor = [
        (0.390, -1.32, "Just into poor tier (39%)"),
        (0.350, -1.8, "Poor road team (35%)"),
        (0.300, -2.4, "Bottom of tier (30%)"),
    ]

    for road_pct, expected, description in test_cases_poor:
        result = calculate_road_penalty(road_pct)
        distance = 0.50 - road_pct
        base = -distance * 10.0
        multiplied = base * 1.2
        print(f"{description}:")
        print(f"  Distance below 50%: {distance}")
        print(f"  Base penalty: {base}")
        print(f"  After 1.2x multiplier: {multiplied}")
        print(f"  Actual result: {result} (expected: {expected})")
        assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"

    print("✓ PASS - Poor teams (30-39%) get 1.2x enhanced penalty")

    # Test 4: Catastrophic road teams (<30%) - 1.4x multiplier
    print("\nTest 4: Catastrophic Road Teams (1.4x Multiplier)")
    print("-" * 80)

    test_cases_catastrophic = [
        (0.290, -2.94, "Just into catastrophic tier (29%)"),
        (0.250, -3.5, "Catastrophic road team (25%)"),
        (0.200, -4.2, "Very bad road team (20%)"),
        (0.150, -4.9, "Extremely bad road team (15%)"),
        (0.100, -5.6, "Worst-case scenario (10%)"),
    ]

    for road_pct, expected, description in test_cases_catastrophic:
        result = calculate_road_penalty(road_pct)
        distance = 0.50 - road_pct
        base = -distance * 10.0
        multiplied = base * 1.4
        print(f"{description}:")
        print(f"  Distance below 50%: {distance}")
        print(f"  Base penalty: {base}")
        print(f"  After 1.4x multiplier: {multiplied}")
        print(f"  Actual result: {result} (expected: {expected})")
        assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"

    print("✓ PASS - Catastrophic teams (<30%) get 1.4x strong penalty")

    # Test 5: Clamping to -7.0 maximum penalty
    print("\nTest 5: Maximum Penalty Clamping (-7.0)")
    print("-" * 80)

    # To trigger -7.0 cap, need unclamped penalty <= -7.0
    # Formula: -distance × 10 × 1.4 <= -7.0
    # distance × 14 >= 7.0
    # distance >= 0.5
    # road_pct <= 0.0 (since distance = 0.50 - road_pct)

    test_cases_clamping = [
        (0.000, "0% road win rate (theoretical)"),
    ]

    for road_pct, description in test_cases_clamping:
        result = calculate_road_penalty(road_pct)
        distance = 0.50 - road_pct
        base = -distance * 10.0
        unclamped = base * 1.4
        print(f"{description}:")
        print(f"  Distance below 50%: {distance}")
        print(f"  Unclamped penalty: {unclamped}")
        print(f"  Clamped result: {result}")
        assert result == -7.0, f"Should be clamped to -7.0, got {result}"
        assert result >= -7.0, "Penalty should not exceed -7.0"

    # Also test that values near the cap don't get clamped
    result_near_cap = calculate_road_penalty(0.050)  # Should be -6.3, not clamped
    print(f"\n5% road win rate (near cap): {result_near_cap}")
    assert result_near_cap == -6.3, f"Should be -6.3 (not clamped), got {result_near_cap}"

    result_very_near = calculate_road_penalty(0.020)  # Should be -6.72, not clamped
    print(f"2% road win rate (very near cap): {result_very_near}")
    assert abs(result_very_near - (-6.72)) < 0.01, f"Should be -6.72 (not clamped), got {result_very_near}"

    print("✓ PASS - Maximum penalty correctly clamped to -7.0")

    # Test 6: Input validation (edge cases)
    print("\nTest 6: Input Validation")
    print("-" * 80)

    # Test negative input
    result_negative = calculate_road_penalty(-0.100)
    print(f"Negative input (-10%): {result_negative}")
    assert result_negative == -7.0, "Negative input should clamp to 0.0 then apply max penalty"

    # Test >100% input
    result_over = calculate_road_penalty(1.500)
    print(f"Over 100% input (150%): {result_over}")
    assert result_over == 0.0, "Input >100% should clamp to 1.0 then return 0.0"

    # Test exactly 100%
    result_100 = calculate_road_penalty(1.000)
    print(f"Exactly 100% (perfect road record): {result_100}")
    assert result_100 == 0.0, "100% road record should return 0.0"

    # Test exactly 0%
    result_0 = calculate_road_penalty(0.000)
    print(f"Exactly 0% (no road wins): {result_0}")
    assert result_0 == -7.0, "0% road record should return max penalty -7.0"

    print("✓ PASS - Input validation handles edge cases correctly")

    # Test 7: Tier boundary verification
    print("\nTest 7: Tier Boundary Verification")
    print("-" * 80)

    # Test boundaries between tiers
    boundaries = [
        (0.500, 0.0, "50% boundary (good/below-avg)"),
        (0.499, -0.01, "Just below 50% (below-avg tier)"),
        (0.400, -1.0, "40% boundary (below-avg/poor)"),
        (0.399, -1.21, "Just below 40% (poor tier, 1.2x kicks in)"),
        (0.300, -2.4, "30% boundary (poor/catastrophic)"),
        (0.299, -2.81, "Just below 30% (catastrophic tier, 1.4x kicks in)"),
    ]

    for road_pct, expected, description in boundaries:
        result = calculate_road_penalty(road_pct)
        print(f"{description}: {result} (expected: {expected})")
        assert abs(result - expected) < 0.02, f"Expected {expected}, got {result}"

    print("✓ PASS - Tier boundaries work correctly")

    # Test 8: Monotonicity verification (worse road record = worse penalty)
    print("\nTest 8: Monotonicity Verification")
    print("-" * 80)

    road_percentages = [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15]
    penalties = []

    print("Road Win % | Penalty | Delta from Previous")
    print("-" * 60)

    for i, pct in enumerate(road_percentages):
        penalty = calculate_road_penalty(pct)
        penalties.append(penalty)

        if i == 0:
            print(f"  {pct:.2f}     | {penalty:>6.2f}  | (baseline)")
        else:
            delta = penalty - penalties[i-1]
            print(f"  {pct:.2f}     | {penalty:>6.2f}  | {delta:>6.2f}")
            # Verify monotonicity: lower road % should have more negative penalty
            assert penalty <= penalties[i-1], f"Penalty should decrease as road win % decreases"

    print("✓ PASS - Penalties increase monotonically as road record worsens")

    # Test 9: Non-linearity verification (1.4x vs 1.2x vs 1.0x)
    print("\nTest 9: Non-Linearity Verification")
    print("-" * 80)

    # Compare same distance below 50% in different tiers
    # All are 0.10 below 50%
    test_45 = calculate_road_penalty(0.45)  # 1.0x tier
    test_35 = calculate_road_penalty(0.35)  # 1.2x tier
    test_25 = calculate_road_penalty(0.25)  # 1.4x tier

    print(f"45% road (1.0x tier): {test_45}")
    print(f"35% road (1.2x tier): {test_35}")
    print(f"25% road (1.4x tier): {test_25}")

    # Verify ratios
    # 35% should be 1.2x of 45% (both 0.05 from tier center)
    # Actually comparing base -0.5 at different multipliers:
    # 45%: distance 0.05 → -0.5 × 1.0 = -0.5
    # 35%: distance 0.15 → -1.5 × 1.2 = -1.8
    # 25%: distance 0.25 → -2.5 × 1.4 = -3.5

    assert abs(test_45 - (-0.5)) < 0.01, "45% should be -0.5"
    assert abs(test_35 - (-1.8)) < 0.01, "35% should be -1.8"
    assert abs(test_25 - (-3.5)) < 0.01, "25% should be -3.5"

    print("✓ PASS - Non-linear multipliers (1.4x, 1.2x, 1.0x) work correctly")

    # Test 10: Return value precision
    print("\nTest 10: Return Value Precision")
    print("-" * 80)

    # Test that values are rounded to 2 decimal places
    test_values = [0.333, 0.444, 0.275, 0.183]

    for pct in test_values:
        result = calculate_road_penalty(pct)
        # Check that result has at most 2 decimal places
        result_str = str(result)
        if '.' in result_str:
            decimal_places = len(result_str.split('.')[1])
            print(f"Road {pct:.3f}: {result} ({decimal_places} decimal places)")
            assert decimal_places <= 2, f"Should have max 2 decimal places, got {decimal_places}"
        else:
            print(f"Road {pct:.3f}: {result} (integer)")

    print("✓ PASS - Return values properly rounded to 2 decimal places")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
    print("\nSummary:")
    print("- Good road teams (≥50%) get no penalty (0.0)")
    print("- Below-average (40-49%) get 1.0x base penalty")
    print("- Poor (30-39%) get 1.2x enhanced penalty")
    print("- Catastrophic (<30%) get 1.4x strong penalty")
    print("- Maximum penalty clamped to -7.0")
    print("- Input validation handles edge cases")
    print("- Tier boundaries work correctly")
    print("- Penalties increase monotonically")
    print("- Non-linear scaling verified")
    print("- Return values properly formatted")


if __name__ == "__main__":
    test_road_penalty()
