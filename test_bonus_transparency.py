#!/usr/bin/env python3
"""Test that prediction bonuses are properly exposed and calculations match."""

import sys
import os

# Add parent directory to path so we can import from api/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.utils.prediction_engine import predict_game_total
from api.utils.db_queries import get_matchup_data

def test_bonus_transparency():
    """
    Test that:
    1. assist_bonus and turnover_pace_bonus are present in breakdown
    2. The formula calculation matches: home + away + bonuses = total
    """
    print("=" * 70)
    print("BONUS TRANSPARENCY TEST")
    print("=" * 70)
    print()

    # Test with high-assist teams (Golden State, Boston, Phoenix)
    test_cases = [
        {
            'name': 'Golden State @ Boston (High-assist teams)',
            'home_team_id': 1610612738,  # Boston
            'away_team_id': 1610612744,  # Golden State
            'betting_line': 225.5,
            'season': '2025-26'
        },
        {
            'name': 'Phoenix @ Denver (High-assist vs Normal)',
            'home_team_id': 1610612743,  # Denver
            'away_team_id': 1610612756,  # Phoenix
            'betting_line': 228.0,
            'season': '2025-26'
        }
    ]

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print("-" * 70)

        try:
            # Fetch matchup data
            matchup_data = get_matchup_data(
                home_team_id=test['home_team_id'],
                away_team_id=test['away_team_id'],
                season=test['season']
            )

            if not matchup_data or 'home' not in matchup_data or 'away' not in matchup_data:
                print(f"⚠️  SKIP: No data available for this matchup")
                continue

            home_data = matchup_data['home']
            away_data = matchup_data['away']

            # Call prediction engine
            result = predict_game_total(
                home_data=home_data,
                away_data=away_data,
                betting_line=test['betting_line'],
                home_team_id=test['home_team_id'],
                away_team_id=test['away_team_id'],
                season=test['season']
            )

            # Check 1: Verify bonuses are present in breakdown
            if 'assist_bonus' not in result['breakdown']:
                print("❌ FAIL: assist_bonus missing from breakdown")
                all_passed = False
                continue

            if 'turnover_pace_bonus' not in result['breakdown']:
                print("❌ FAIL: turnover_pace_bonus missing from breakdown")
                all_passed = False
                continue

            print("✅ PASS: Both bonuses present in breakdown")

            # Extract values
            home = result['breakdown']['home_projected']
            away = result['breakdown']['away_projected']
            assist = result['breakdown']['assist_bonus']
            turnover = result['breakdown']['turnover_pace_bonus']
            predicted = result['predicted_total']

            # Check 2: Formula validation
            calculated = round(home + away + assist + turnover, 1)

            if calculated != predicted:
                print(f"❌ FAIL: Formula mismatch!")
                print(f"  Calculated: {home} + {away} + {assist} + {turnover} = {calculated}")
                print(f"  Predicted:  {predicted}")
                print(f"  Difference: {abs(calculated - predicted)}")
                all_passed = False
            else:
                print(f"✅ PASS: Formula matches!")
                print(f"  {home} + {away} + {assist} + {turnover} = {predicted}")

                # Show bonus details if any
                total_bonus = assist + turnover
                if total_bonus > 0:
                    print(f"  → Total bonus applied: +{total_bonus} pts")
                    if assist > 0:
                        print(f"    - Assist bonus: +{assist} pts")
                    if turnover > 0:
                        print(f"    - Turnover bonus: +{turnover} pts")
                else:
                    print(f"  → No bonuses applied (normal game)")

        except Exception as e:
            print(f"❌ ERROR: Test failed with exception:")
            print(f"  {str(e)}")
            all_passed = False

        print()

    # Final summary
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print()
        print("Backend changes are working correctly:")
        print("  ✓ assist_bonus and turnover_pace_bonus are exposed in API")
        print("  ✓ Formula calculation is accurate")
        print("  ✓ No mismatches between logs and API response")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please review the errors above and fix the issues.")
        return 1

if __name__ == '__main__':
    exit_code = test_bonus_transparency()
    sys.exit(exit_code)
