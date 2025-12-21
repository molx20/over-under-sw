"""
Test Suite for Dynamic 3PT Shootout Adjustment

Tests various scenarios to ensure the shootout calculation correctly identifies
high-scoring 3PT games and assigns appropriate bonuses.
"""

from api.utils.dynamic_shootout_adjustment import calculate_shootout_bonus


def test_dynamic_shootout():
    """Test various 3PT shootout scenarios"""

    print("=" * 80)
    print("DYNAMIC 3PT SHOOTOUT ADJUSTMENT - TEST SCENARIOS")
    print("=" * 80)

    LEAGUE_AVG = 0.365

    # Test 1: Elite 3PT team vs weak defense, hot streak, fast pace, fresh legs
    print("\nTest 1: Extreme Shootout (LAL/BOS, DEN/ATL scenario)")
    print("-" * 80)
    result = calculate_shootout_bonus(
        team_3p_pct=0.420,  # 42% shooter
        league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.390,  # Allows 39%
        last5_3p_pct=0.450,  # 45% recently (hot!)
        season_3p_pct=0.420,
        projected_pace=108,  # Fast pace
        rest_days=3,  # Fresh legs
        on_back_to_back=False
    )
    print(f"Team: 42% 3PT, Hot (45% last 5), vs 39% defense allowed, Pace 108, Fresh")
    print(f"Breakdown: {result['breakdown']}")
    print(f"Shootout Score: {result['shootout_score']} ({result['tier']} tier)")
    print(f"Expected: High tier (score > 10), bonus ~9-10 pts")
    print(f"Actual Bonus: {result['shootout_bonus']} pts")
    assert result['tier'] == 'high', f"Expected high tier, got {result['tier']}"
    assert result['shootout_bonus'] >= 8.0, f"Expected bonus >= 8.0, got {result['shootout_bonus']}"
    print("✓ PASS - Extreme shootout correctly identified")

    # Test 2: Good shooters vs average defense, normal conditions
    print("\nTest 2: Medium Shootout (Good 3PT environment)")
    print("-" * 80)
    result = calculate_shootout_bonus(
        team_3p_pct=0.400,  # 40% shooter
        league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.380,  # Allows 38%
        last5_3p_pct=0.415,  # 41.5% recently (warm)
        season_3p_pct=0.400,
        projected_pace=103,  # Slightly fast
        rest_days=2,  # Fresh
        on_back_to_back=False
    )
    print(f"Team: 40% 3PT, Warm (41.5% last 5), vs 38% defense, Pace 103, Fresh")
    print(f"Breakdown: {result['breakdown']}")
    print(f"Shootout Score: {result['shootout_score']} ({result['tier']} tier)")
    print(f"Expected: Medium tier (6 < score <= 10), bonus ~4-6 pts")
    print(f"Actual Bonus: {result['shootout_bonus']} pts")
    assert result['tier'] == 'medium', f"Expected medium tier, got {result['tier']}"
    assert 4.0 <= result['shootout_bonus'] <= 7.0, f"Expected 4-7 pts, got {result['shootout_bonus']}"
    print("✓ PASS - Medium shootout correctly identified")

    # Test 3: Average team, average conditions
    print("\nTest 3: No Shootout (Average conditions)")
    print("-" * 80)
    result = calculate_shootout_bonus(
        team_3p_pct=0.365,  # League average
        league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.365,  # League average defense
        last5_3p_pct=0.360,  # Slightly below average recently
        season_3p_pct=0.365,
        projected_pace=100,  # Average pace
        rest_days=1,  # Normal rest
        on_back_to_back=False
    )
    print(f"Team: 36.5% 3PT (avg), 36% last 5, vs 36.5% defense, Pace 100, Normal rest")
    print(f"Breakdown: {result['breakdown']}")
    print(f"Shootout Score: {result['shootout_score']} ({result['tier']} tier)")
    print(f"Expected: None tier (score <= 3), bonus = 0 pts")
    print(f"Actual Bonus: {result['shootout_bonus']} pts")
    assert result['tier'] == 'none', f"Expected none tier, got {result['tier']}"
    assert result['shootout_bonus'] == 0.0, f"Expected 0 pts, got {result['shootout_bonus']}"
    print("✓ PASS - Average conditions correctly get no bonus")

    # Test 4: Poor shooters on B2B vs elite defense
    print("\nTest 4: Negative Environment (Should still get 0 bonus)")
    print("-" * 80)
    result = calculate_shootout_bonus(
        team_3p_pct=0.340,  # 34% shooter (below average)
        league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.340,  # Elite 3PT defense
        last5_3p_pct=0.300,  # 30% recently (cold!)
        season_3p_pct=0.340,
        projected_pace=95,  # Slow pace
        rest_days=0,  # Back-to-back
        on_back_to_back=True
    )
    print(f"Team: 34% 3PT, Cold (30% last 5), vs 34% defense, Pace 95, B2B")
    print(f"Breakdown: {result['breakdown']}")
    print(f"Shootout Score: {result['shootout_score']} ({result['tier']} tier)")
    print(f"Expected: None tier (negative score), bonus = 0 pts (no penalties)")
    print(f"Actual Bonus: {result['shootout_bonus']} pts")
    assert result['tier'] == 'none', f"Expected none tier, got {result['tier']}"
    assert result['shootout_bonus'] == 0.0, f"Expected 0 pts, got {result['shootout_bonus']}"
    print("✓ PASS - Negative environment correctly gets no penalty")

    # Test 5: Low-confidence shootout
    print("\nTest 5: Low Shootout (Marginal 3PT environment)")
    print("-" * 80)
    result = calculate_shootout_bonus(
        team_3p_pct=0.380,  # 38% shooter
        league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.375,  # Allows 37.5%
        last5_3p_pct=0.385,  # 38.5% recently (stable)
        season_3p_pct=0.380,
        projected_pace=102,  # Slightly fast
        rest_days=1,  # Normal rest
        on_back_to_back=False
    )
    print(f"Team: 38% 3PT, Stable (38.5% last 5), vs 37.5% defense, Pace 102")
    print(f"Breakdown: {result['breakdown']}")
    print(f"Shootout Score: {result['shootout_score']} ({result['tier']} tier)")
    print(f"Expected: Low tier (3 < score <= 6), bonus ~1-2 pts")
    print(f"Actual Bonus: {result['shootout_bonus']} pts")
    assert result['tier'] == 'low', f"Expected low tier, got {result['tier']}"
    assert 0.5 <= result['shootout_bonus'] <= 3.0, f"Expected 0.5-3 pts, got {result['shootout_bonus']}"
    print("✓ PASS - Low shootout correctly identified")

    # Test 6: Component verification - pace impact
    print("\nTest 6: Pace Impact Verification")
    print("-" * 80)
    # Same team, different paces
    slow_pace = calculate_shootout_bonus(
        team_3p_pct=0.400, league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.380, last5_3p_pct=0.400,
        season_3p_pct=0.400, projected_pace=95,
        rest_days=1, on_back_to_back=False
    )
    fast_pace = calculate_shootout_bonus(
        team_3p_pct=0.400, league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.380, last5_3p_pct=0.400,
        season_3p_pct=0.400, projected_pace=110,
        rest_days=1, on_back_to_back=False
    )
    pace_diff = fast_pace['breakdown']['pace_factor'] - slow_pace['breakdown']['pace_factor']
    expected_diff = (110 - 95) * 0.15
    print(f"Slow pace (95): {slow_pace['breakdown']['pace_factor']:.2f}")
    print(f"Fast pace (110): {fast_pace['breakdown']['pace_factor']:.2f}")
    print(f"Difference: {pace_diff:.2f} (expected: {expected_diff:.2f})")
    assert abs(pace_diff - expected_diff) < 0.01, f"Pace impact incorrect"
    print("✓ PASS - Pace factor calculates correctly")

    # Test 7: Component verification - rest impact
    print("\nTest 7: Rest Impact Verification")
    print("-" * 80)
    b2b = calculate_shootout_bonus(
        team_3p_pct=0.380, league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.370, last5_3p_pct=0.380,
        season_3p_pct=0.380, projected_pace=100,
        rest_days=0, on_back_to_back=True
    )
    fresh = calculate_shootout_bonus(
        team_3p_pct=0.380, league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.370, last5_3p_pct=0.380,
        season_3p_pct=0.380, projected_pace=100,
        rest_days=3, on_back_to_back=False
    )
    rest_diff = fresh['breakdown']['rest_factor'] - b2b['breakdown']['rest_factor']
    print(f"Back-to-back: {b2b['breakdown']['rest_factor']:.2f}")
    print(f"Fresh (3 days): {fresh['breakdown']['rest_factor']:.2f}")
    print(f"Difference: {rest_diff:.2f} (expected: 2.5)")
    assert b2b['breakdown']['rest_factor'] == -1.5, "B2B should be -1.5"
    assert fresh['breakdown']['rest_factor'] == 1.0, "Fresh should be +1.0"
    assert rest_diff == 2.5, "Rest difference should be 2.5"
    print("✓ PASS - Rest factor calculates correctly")

    # Test 8: Tier boundary verification
    print("\nTest 8: Tier Boundary Verification")
    print("-" * 80)
    # Test boundary at score = 10 (high tier threshold)
    just_below_high = calculate_shootout_bonus(
        team_3p_pct=0.400, league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.385, last5_3p_pct=0.415,
        season_3p_pct=0.400, projected_pace=104,
        rest_days=1, on_back_to_back=False
    )
    # Manually adjust to get score just above 10
    just_above_high = calculate_shootout_bonus(
        team_3p_pct=0.410, league_avg_3p_pct=LEAGUE_AVG,
        opponent_3p_allowed_pct=0.390, last5_3p_pct=0.425,
        season_3p_pct=0.410, projected_pace=106,
        rest_days=2, on_back_to_back=False
    )
    print(f"Score {just_below_high['shootout_score']:.2f}: {just_below_high['tier']} tier")
    print(f"Score {just_above_high['shootout_score']:.2f}: {just_above_high['tier']} tier")
    if just_below_high['shootout_score'] <= 10:
        assert just_below_high['tier'] in ['medium', 'low'], f"Score <= 10 should not be high tier"
    if just_above_high['shootout_score'] > 10:
        assert just_above_high['tier'] == 'high', f"Score > 10 should be high tier"
    print("✓ PASS - Tier boundaries working correctly")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
    print("\nSummary:")
    print("- Extreme shootouts (score >10) get high tier bonus (8-12 pts)")
    print("- Medium shootouts (score 6-10) get medium tier bonus (4-6 pts)")
    print("- Low shootouts (score 3-6) get low tier bonus (1-2 pts)")
    print("- Average/poor conditions (score ≤3) get no bonus (0 pts)")
    print("- Pace factor increases with faster games")
    print("- Rest factor: Fresh (+1.0), Normal (0), B2B (-1.5)")
    print("- No negative penalties applied")


if __name__ == "__main__":
    test_dynamic_shootout()
