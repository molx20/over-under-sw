#!/usr/bin/env python3
"""
Test dynamic defensive adjustment based on offensive form
"""

import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.prediction_engine import calculate_defensive_multiplier

print("=" * 80)
print("DYNAMIC DEFENSIVE ADJUSTMENT TESTS")
print("=" * 80)
print()

# Test cases: (ortg_change, ppg_change, def_rank, expected_behavior)
test_cases = [
    # Hot offense tests
    {
        'name': 'Hot offense vs Elite defense (rank #3)',
        'ortg_change': 6.0,
        'ppg_change': 5.0,
        'def_rank': 3,
        'expected': 0.30,
        'description': 'Hot offense should reduce elite defense penalty to 30%'
    },
    {
        'name': 'Hot offense vs Average defense (rank #15)',
        'ortg_change': 5.0,
        'ppg_change': 4.5,
        'def_rank': 15,
        'expected': 0.40,
        'description': 'Hot offense should reduce average defense penalty to 40%'
    },
    {
        'name': 'Hot offense vs Weak defense (rank #28)',
        'ortg_change': 7.0,
        'ppg_change': 6.0,
        'def_rank': 28,
        'expected': 0.50,
        'description': 'Hot offense should reduce weak defense penalty to 50%'
    },

    # Cold offense tests
    {
        'name': 'Cold offense vs Elite defense (rank #2)',
        'ortg_change': -6.0,
        'ppg_change': -5.0,
        'def_rank': 2,
        'expected': 1.50,
        'description': 'Cold offense should amplify any defense penalty to 150%'
    },
    {
        'name': 'Cold offense vs Average defense (rank #16)',
        'ortg_change': -5.0,
        'ppg_change': -4.5,
        'def_rank': 16,
        'expected': 1.50,
        'description': 'Cold offense should amplify average defense penalty to 150%'
    },
    {
        'name': 'Cold offense vs Weak defense (rank #27)',
        'ortg_change': -7.0,
        'ppg_change': -6.0,
        'def_rank': 27,
        'expected': 1.50,
        'description': 'Cold offense should still amplify weak defense penalty to 150%'
    },

    # Normal offense tests
    {
        'name': 'Normal offense vs Elite defense (rank #5)',
        'ortg_change': 2.0,
        'ppg_change': 1.5,
        'def_rank': 5,
        'expected': 1.00,
        'description': 'Normal offense should keep defense penalty at 100% (unchanged)'
    },
    {
        'name': 'Normal offense vs Average defense (rank #18)',
        'ortg_change': -2.0,
        'ppg_change': -1.0,
        'def_rank': 18,
        'expected': 1.00,
        'description': 'Normal offense should keep defense penalty at 100% (unchanged)'
    },
    {
        'name': 'Normal offense vs Weak defense (rank #29)',
        'ortg_change': 0.5,
        'ppg_change': 0.0,
        'def_rank': 29,
        'expected': 1.00,
        'description': 'Normal offense should keep defense penalty at 100% (unchanged)'
    },

    # Edge cases
    {
        'name': 'Exactly +4 ORTG (threshold for hot)',
        'ortg_change': 4.0,
        'ppg_change': 0.0,
        'def_rank': 10,
        'expected': 0.30,
        'description': 'Exactly +4 should trigger hot offense behavior'
    },
    {
        'name': 'Exactly -4 ORTG (threshold for cold)',
        'ortg_change': -4.0,
        'ppg_change': 0.0,
        'def_rank': 20,
        'expected': 1.50,
        'description': 'Exactly -4 should trigger cold offense behavior'
    },
]

print("Testing calculate_defensive_multiplier()...\n")

passed = 0
failed = 0

for test in test_cases:
    result = calculate_defensive_multiplier(
        test['ortg_change'],
        test['ppg_change'],
        test['def_rank']
    )

    if result == test['expected']:
        status = "✓ PASS"
        passed += 1
    else:
        status = "✗ FAIL"
        failed += 1

    print(f"{status}: {test['name']}")
    print(f"  ORTG change: {test['ortg_change']:+.1f}, PPG change: {test['ppg_change']:+.1f}")
    print(f"  Defense rank: #{test['def_rank']}")
    print(f"  Expected: {test['expected']:.2f}x, Got: {result:.2f}x")
    print(f"  {test['description']}")
    print()

print("=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 80)
print()

if failed == 0:
    print("✓✓✓ ALL TESTS PASSED ✓✓✓")
    print()
    print("Example Impact Scenarios:")
    print("-" * 80)
    print()

    # Scenario 1: Hot offense vs elite defense
    print("Scenario 1: HOT OFFENSE VS ELITE DEFENSE")
    print("  Team A: Season 115 PPG, Recent 121 PPG (+6), Recent ORTG +6.0")
    print("  Opponent: Defense rank #3 (elite)")
    print("  Base defensive penalty: -8.0 points")
    print("  OLD system: -8.0 × 0.30 = -2.4 pts applied")
    print("  NEW system: -8.0 × 0.30 × 0.30 = -0.72 pts applied")
    print("  → Hot offense reduces elite defense impact from -2.4 to -0.72 pts")
    print()

    # Scenario 2: Cold offense vs weak defense
    print("Scenario 2: COLD OFFENSE VS WEAK DEFENSE")
    print("  Team B: Season 110 PPG, Recent 105 PPG (-5), Recent ORTG -5.5")
    print("  Opponent: Defense rank #28 (weak)")
    print("  Base defensive penalty: -3.0 points")
    print("  OLD system: -3.0 × 0.30 = -0.9 pts applied")
    print("  NEW system: -3.0 × 0.30 × 1.50 = -1.35 pts applied")
    print("  → Cold offense amplifies even weak defense impact from -0.9 to -1.35 pts")
    print()

    # Scenario 3: Normal offense vs average defense
    print("Scenario 3: NORMAL OFFENSE VS AVERAGE DEFENSE")
    print("  Team C: Season 112 PPG, Recent 113 PPG (+1), Recent ORTG +1.5")
    print("  Opponent: Defense rank #15 (average)")
    print("  Base defensive penalty: -5.0 points")
    print("  OLD system: -5.0 × 0.30 = -1.5 pts applied")
    print("  NEW system: -5.0 × 0.30 × 1.00 = -1.5 pts applied")
    print("  → Normal offense keeps defense impact unchanged at -1.5 pts")
    print()

else:
    print(f"✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
    sys.exit(1)
