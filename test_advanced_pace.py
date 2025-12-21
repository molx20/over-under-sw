"""
Test Suite for Advanced Pace Calculation

Validates all components of the advanced pace formula:
- Season/recent blend (60/40)
- Pace mismatch penalties
- Turnover-driven pace boosts
- Free throw rate penalties
- Elite defense penalties
- Clamping to 92-108 range
"""

from api.utils.advanced_pace_calculation import calculate_advanced_pace


def test_advanced_pace():
    """Test various pace calculation scenarios"""

    print("=" * 80)
    print("ADVANCED PACE CALCULATION - TEST SCENARIOS")
    print("=" * 80)

    # Test 1: Average teams, no special factors
    print("\nTest 1: Average Teams, Normal Conditions")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=100, team1_last5_pace=100,
        team2_season_pace=100, team2_last5_pace=100,
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    print(f"Team 1: 100 pace (season), 100 pace (recent)")
    print(f"Team 2: 100 pace (season), 100 pace (recent)")
    print(f"Turnovers: 12 each, FT Rate: 0.20 each, No elite defense")
    print(f"\nBreakdown: {result['breakdown']}")
    print(f"Adjustments: {result['adjustments']}")
    print(f"Expected: ~100 pace (no adjustments)")
    print(f"Actual: {result['final_pace']} pace")
    assert 99 <= result['final_pace'] <= 101, f"Expected ~100, got {result['final_pace']}"
    print("✓ PASS - Baseline case works correctly")

    # Test 2: Fast vs Slow (pace mismatch)
    print("\nTest 2: Pace Mismatch (Fast vs Slow)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=108, team1_last5_pace=110,  # Fast team
        team2_season_pace=95, team2_last5_pace=93,    # Slow team
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    print(f"Team 1 (Fast): 108 season, 110 recent → {result['breakdown']['team1_adjusted_pace']} adjusted")
    print(f"Team 2 (Slow): 95 season, 93 recent → {result['breakdown']['team2_adjusted_pace']} adjusted")
    print(f"Pace difference: {result['breakdown']['pace_difference']}")
    print(f"Pace mismatch penalty: {result['adjustments']['pace_mismatch_penalty']}")
    print(f"\nExpected: Penalty of -2.0 (difference > 8)")
    print(f"Actual Final Pace: {result['final_pace']}")
    assert result['adjustments']['pace_mismatch_penalty'] == -2.0, "Should have -2.0 penalty"
    print("✓ PASS - Large pace mismatch correctly penalized")

    # Test 3: High turnovers (faster pace)
    print("\nTest 3: High Turnover Game (Faster Pace)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=100, team1_last5_pace=100,
        team2_season_pace=100, team2_last5_pace=100,
        team1_season_turnovers=18, team2_season_turnovers=17,  # High turnovers
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    print(f"Team 1 turnovers: 18 per game")
    print(f"Team 2 turnovers: 17 per game")
    print(f"Projected turnovers: {result['context']['projected_turnovers']}")
    print(f"Turnover pace impact: +{result['adjustments']['turnover_pace_impact']}")
    print(f"\nExpected: Boost for turnovers > 15")
    print(f"Actual Final Pace: {result['final_pace']}")
    assert result['adjustments']['turnover_pace_impact'] > 0, "Should have positive turnover impact"
    assert result['final_pace'] > 100, "High turnovers should increase pace"
    print("✓ PASS - High turnovers correctly boost pace")

    # Test 4: High free throw rate (slower pace)
    print("\nTest 4: Free Throw Heavy Game (Slower Pace)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=100, team1_last5_pace=100,
        team2_season_pace=100, team2_last5_pace=100,
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.35, team2_ft_rate=0.30,  # High FT rate
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    print(f"Team 1 FT rate: 0.35 (35 FTA per 100 FGA)")
    print(f"Team 2 FT rate: 0.30 (30 FTA per 100 FGA)")
    print(f"Combined FT rate: {result['context']['combined_ft_rate']}")
    print(f"FT pace penalty: -{result['adjustments']['ft_pace_penalty']}")
    print(f"\nExpected: Penalty for FT rate > 0.25")
    print(f"Actual Final Pace: {result['final_pace']}")
    assert result['adjustments']['ft_pace_penalty'] > 0, "Should have FT penalty"
    assert result['final_pace'] < 100, "High FT rate should decrease pace"
    print("✓ PASS - High FT rate correctly slows pace")

    # Test 5: Elite defense (defensive grind)
    print("\nTest 5: Elite Defense Game (Defensive Grind)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=100, team1_last5_pace=100,
        team2_season_pace=100, team2_last5_pace=100,
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=True, team2_is_elite_defense=False  # One elite defense
    )
    print(f"Team 1: Elite defense")
    print(f"Team 2: Average defense")
    print(f"Defense pace penalty: {result['adjustments']['defense_pace_penalty']}")
    print(f"\nExpected: -1.5 penalty for elite defense")
    print(f"Actual Final Pace: {result['final_pace']}")
    assert result['adjustments']['defense_pace_penalty'] == -1.5, "Should have -1.5 penalty"
    assert result['final_pace'] < 100, "Elite defense should slow pace"
    print("✓ PASS - Elite defense correctly slows pace")

    # Test 6: Extreme fast pace (clamping upper bound)
    print("\nTest 6: Extreme Fast Pace (Upper Bound Clamping)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=110, team1_last5_pace=112,  # Very fast
        team2_season_pace=108, team2_last5_pace=110,  # Very fast
        team1_season_turnovers=20, team2_season_turnovers=19,  # High turnovers
        team1_ft_rate=0.15, team2_ft_rate=0.15,  # Low FT rate
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    print(f"Team 1: 110 season, 112 recent → {result['breakdown']['team1_adjusted_pace']}")
    print(f"Team 2: 108 season, 110 recent → {result['breakdown']['team2_adjusted_pace']}")
    print(f"High turnovers: {result['context']['projected_turnovers']}")
    print(f"Pace before clamp: {result['pace_before_clamp']}")
    print(f"\nExpected: Clamped to max 108")
    print(f"Actual Final Pace: {result['final_pace']}")
    assert result['final_pace'] == 108, "Should be clamped to 108"
    assert result['context']['clamped'], "Should show as clamped"
    print("✓ PASS - Upper bound clamping works")

    # Test 7: Extreme slow pace (clamping lower bound)
    print("\nTest 7: Extreme Slow Pace (Lower Bound Clamping)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=92, team1_last5_pace=90,  # Very slow
        team2_season_pace=93, team2_last5_pace=91,  # Very slow
        team1_season_turnovers=10, team2_season_turnovers=9,  # Low turnovers
        team1_ft_rate=0.35, team2_ft_rate=0.32,  # High FT rate
        team1_is_elite_defense=True, team2_is_elite_defense=True  # Both elite
    )
    print(f"Team 1: 92 season, 90 recent → {result['breakdown']['team1_adjusted_pace']}")
    print(f"Team 2: 93 season, 91 recent → {result['breakdown']['team2_adjusted_pace']}")
    print(f"Both elite defenses: {result['context']['has_elite_defense']}")
    print(f"High FT rate: {result['context']['combined_ft_rate']}")
    print(f"Pace before clamp: {result['pace_before_clamp']}")
    print(f"\nExpected: Clamped to min 92")
    print(f"Actual Final Pace: {result['final_pace']}")
    assert result['final_pace'] == 92, "Should be clamped to 92"
    assert result['context']['clamped'], "Should show as clamped"
    print("✓ PASS - Lower bound clamping works")

    # Test 8: Complex scenario (multiple factors)
    print("\nTest 8: Complex Scenario (Multiple Factors)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=102, team1_last5_pace=105,  # Trending faster
        team2_season_pace=98, team2_last5_pace=96,    # Trending slower
        team1_season_turnovers=16, team2_season_turnovers=14,  # Above average turnovers
        team1_ft_rate=0.28, team2_ft_rate=0.26,  # Above average FT rate
        team1_is_elite_defense=False, team2_is_elite_defense=True  # One elite defense
    )
    print(f"Team 1: 102→105 (trending up) → {result['breakdown']['team1_adjusted_pace']}")
    print(f"Team 2: 98→96 (trending down) → {result['breakdown']['team2_adjusted_pace']}")
    print(f"\nAll adjustments:")
    for key, value in result['adjustments'].items():
        sign = '+' if value > 0 else ''
        print(f"  {key}: {sign}{value}")
    print(f"\nBase pace: {result['breakdown']['base_pace']}")
    print(f"Final pace: {result['final_pace']}")
    # Verify all components are working
    assert result['adjustments']['pace_mismatch_penalty'] < 0, "Should have mismatch penalty"
    assert result['adjustments']['turnover_pace_impact'] == 0, "Turnovers at 15, no boost"
    assert result['adjustments']['ft_pace_penalty'] > 0, "Should have FT penalty"
    assert result['adjustments']['defense_pace_penalty'] == -1.5, "Should have defense penalty"
    print("✓ PASS - Complex multi-factor scenario works correctly")

    # Test 9: Season/recent blend verification
    print("\nTest 9: Season/Recent Blend Verification (60/40)")
    print("-" * 80)
    result = calculate_advanced_pace(
        team1_season_pace=100, team1_last5_pace=110,  # Recent much higher
        team2_season_pace=100, team2_last5_pace=100,
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    # Team 1 should be: 100*0.6 + 110*0.4 = 60 + 44 = 104
    expected_team1 = 100 * 0.6 + 110 * 0.4
    actual_team1 = result['breakdown']['team1_adjusted_pace']
    print(f"Team 1 season: 100, recent: 110")
    print(f"Expected adjusted: {expected_team1} (60% season + 40% recent)")
    print(f"Actual adjusted: {actual_team1}")
    assert abs(actual_team1 - expected_team1) < 0.01, "Blend should be 60/40"
    print("✓ PASS - 60/40 blend calculates correctly")

    # Test 10: Pace mismatch boundary verification
    print("\nTest 10: Pace Mismatch Boundary Verification")
    print("-" * 80)
    # Test at difference = 5 (should be 0 penalty)
    result_5 = calculate_advanced_pace(
        team1_season_pace=102.5, team1_last5_pace=102.5,
        team2_season_pace=97.5, team2_last5_pace=97.5,  # Exactly 5 difference
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    # Test at difference = 6 (should be -1 penalty)
    result_6 = calculate_advanced_pace(
        team1_season_pace=103, team1_last5_pace=103,
        team2_season_pace=97, team2_last5_pace=97,  # Exactly 6 difference
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    # Test at difference = 9 (should be -2 penalty)
    result_9 = calculate_advanced_pace(
        team1_season_pace=104.5, team1_last5_pace=104.5,
        team2_season_pace=95.5, team2_last5_pace=95.5,  # Exactly 9 difference
        team1_season_turnovers=12, team2_season_turnovers=12,
        team1_ft_rate=0.20, team2_ft_rate=0.20,
        team1_is_elite_defense=False, team2_is_elite_defense=False
    )
    print(f"Difference = 5: penalty = {result_5['adjustments']['pace_mismatch_penalty']} (expected 0)")
    print(f"Difference = 6: penalty = {result_6['adjustments']['pace_mismatch_penalty']} (expected -1)")
    print(f"Difference = 9: penalty = {result_9['adjustments']['pace_mismatch_penalty']} (expected -2)")
    assert result_5['adjustments']['pace_mismatch_penalty'] == 0, "Diff=5 should be 0"
    assert result_6['adjustments']['pace_mismatch_penalty'] == -1.0, "Diff=6 should be -1"
    assert result_9['adjustments']['pace_mismatch_penalty'] == -2.0, "Diff=9 should be -2"
    print("✓ PASS - Pace mismatch thresholds correct")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
    print("\nSummary:")
    print("- Season/recent blend (60/40) working correctly")
    print("- Pace mismatch penalties applied correctly (0, -1, -2)")
    print("- Turnover boost working (>15 turnovers)")
    print("- FT penalty working (>0.25 FT rate)")
    print("- Elite defense penalty working (-1.5)")
    print("- Clamping working (92-108 range)")
    print("- Complex multi-factor scenarios handled correctly")


if __name__ == "__main__":
    test_advanced_pace()
