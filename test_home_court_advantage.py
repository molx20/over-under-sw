"""
Test script for Dynamic Home Court Advantage

Tests various scenarios to ensure the home court advantage calculation
works correctly across different team matchups.
"""

from api.utils.home_court_advantage import calculate_home_court_advantage


def test_home_court_advantage():
    """Test various home court advantage scenarios"""

    print("=" * 70)
    print("DYNAMIC HOME COURT ADVANTAGE - TEST SCENARIOS")
    print("=" * 70)

    # Test 1: Elite home team vs weak road team, hot at home
    print("\nTest 1: Elite home team vs weak road team, hot at home")
    print("-" * 70)
    hca = calculate_home_court_advantage(
        home_win_pct=0.800,  # 20-5 at home
        road_win_pct=0.320,  # 8-17 on road
        last3_home_wins=3
    )
    print(f"Home: 20-5 (0.800), Away: 8-17 road (0.320), Last 3: 3/3 wins")
    print(f"Expected: ~6.0 pts (max)")
    print(f"Actual: {hca:.1f} pts")
    assert 5.5 <= hca <= 6.0, f"Expected 5.5-6.0, got {hca}"
    print("✓ PASS")

    # Test 2: Average teams, neutral momentum
    print("\nTest 2: Average teams, neutral momentum")
    print("-" * 70)
    hca = calculate_home_court_advantage(
        home_win_pct=0.500,  # 12-12 at home
        road_win_pct=0.500,  # 10-10 on road
        last3_home_wins=1
    )
    print(f"Home: 12-12 (0.500), Away: 10-10 road (0.500), Last 3: 1/3 wins")
    print(f"Expected: ~2.5 pts (baseline)")
    print(f"Actual: {hca:.1f} pts")
    assert 2.0 <= hca <= 3.0, f"Expected 2.0-3.0, got {hca}"
    print("✓ PASS")

    # Test 3: Weak home team vs strong road team, cold at home
    print("\nTest 3: Weak home team vs strong road team, cold at home")
    print("-" * 70)
    hca = calculate_home_court_advantage(
        home_win_pct=0.320,  # 8-17 at home
        road_win_pct=0.720,  # 18-7 on road
        last3_home_wins=0
    )
    print(f"Home: 8-17 (0.320), Away: 18-7 road (0.720), Last 3: 0/3 wins")
    print(f"Expected: ~0.0 pts (minimal)")
    print(f"Actual: {hca:.1f} pts")
    assert 0.0 <= hca <= 0.5, f"Expected 0.0-0.5, got {hca}"
    print("✓ PASS")

    # Test 4: Strong home team vs average road team
    print("\nTest 4: Strong home team vs average road team")
    print("-" * 70)
    hca = calculate_home_court_advantage(
        home_win_pct=0.650,  # 15-8 at home
        road_win_pct=0.435,  # 10-13 on road
        last3_home_wins=2
    )
    print(f"Home: 15-8 (0.650), Away: 10-13 road (0.435), Last 3: 2/3 wins")
    print(f"Expected: ~4.0-5.0 pts")
    print(f"Actual: {hca:.1f} pts")
    assert 3.5 <= hca <= 5.5, f"Expected 3.5-5.5, got {hca}"
    print("✓ PASS")

    # Test 5: Verify clamping (should never exceed 6.0)
    print("\nTest 5: Verify upper bound clamping")
    print("-" * 70)
    hca = calculate_home_court_advantage(
        home_win_pct=1.000,  # Perfect home record
        road_win_pct=0.000,  # Winless on road
        last3_home_wins=3
    )
    print(f"Home: Perfect (1.000), Away: Winless road (0.000), Last 3: 3/3 wins")
    print(f"Expected: 6.0 pts (max clamp)")
    print(f"Actual: {hca:.1f} pts")
    assert hca == 6.0, f"Expected exactly 6.0 (max), got {hca}"
    print("✓ PASS")

    # Test 6: Verify lower bound clamping (should never be negative)
    print("\nTest 6: Verify lower bound clamping")
    print("-" * 70)
    hca = calculate_home_court_advantage(
        home_win_pct=0.000,  # Winless at home
        road_win_pct=1.000,  # Perfect road record
        last3_home_wins=0
    )
    print(f"Home: Winless (0.000), Away: Perfect road (1.000), Last 3: 0/3 wins")
    print(f"Expected: 0.0 pts (min clamp)")
    print(f"Actual: {hca:.1f} pts")
    assert hca == 0.0, f"Expected exactly 0.0 (min), got {hca}"
    print("✓ PASS")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)


if __name__ == "__main__":
    test_home_court_advantage()
