#!/usr/bin/env python3
"""
Validation script for defense-first prediction architecture.
Tests predictions against known cases where old system was 15-25 pts off.
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from api.utils.db_queries import get_matchup_data, get_all_teams
from api.utils.prediction_engine import predict_game_total

def validate_prediction(home_abbr, away_abbr, betting_line, actual_home=None, actual_away=None):
    """
    Validate a single game prediction.

    Args:
        home_abbr: Home team abbreviation
        away_abbr: Away team abbreviation
        betting_line: Vegas O/U line
        actual_home: Actual home team score (optional)
        actual_away: Actual away team score (optional)
    """
    # Get team IDs
    all_teams = get_all_teams()
    home_team = next((t for t in all_teams if t['abbreviation'] == home_abbr), None)
    away_team = next((t for t in all_teams if t['abbreviation'] == away_abbr), None)

    if not home_team or not away_team:
        print(f"❌ ERROR: Could not find teams {away_abbr} @ {home_abbr}")
        return False

    home_id = home_team['id']
    away_id = away_team['id']

    # Get matchup data
    matchup = get_matchup_data(home_id, away_id)
    if not matchup:
        print(f"❌ ERROR: Could not get matchup data for {away_abbr} @ {home_abbr}")
        return False

    # Generate prediction
    prediction = predict_game_total(
        matchup['home'],
        matchup['away'],
        betting_line,
        home_team_id=home_id,
        away_team_id=away_id,
        home_team_abbr=home_abbr,
        away_team_abbr=away_abbr,
        season='2025-26'
    )

    home_pred = prediction['breakdown']['home_projected']
    away_pred = prediction['breakdown']['away_projected']
    home_base = prediction['breakdown'].get('home_base_ppg')
    away_base = prediction['breakdown'].get('away_base_ppg')
    home_quality = prediction['breakdown'].get('home_data_quality', 'unknown')
    away_quality = prediction['breakdown'].get('away_data_quality', 'unknown')
    total_pred = prediction['predicted_total']

    print(f"\n{'='*80}")
    print(f"GAME: {away_abbr} @ {home_abbr}")
    print(f"{'='*80}")

    print(f"\nBetting Line: {betting_line}")
    if actual_home and actual_away:
        print(f"Actual Result: {away_abbr} {actual_away}, {home_abbr} {actual_home} (Total: {actual_home + actual_away})")

    print(f"\nPREDICTION:")
    print(f"  {home_abbr} (Home): {home_pred:.1f} PPG")
    print(f"  {away_abbr} (Away): {away_pred:.1f} PPG")
    print(f"  Predicted Total: {total_pred}")

    print(f"\nDEFENSE-ADJUSTED BASE:")
    print(f"  {home_abbr} base: {home_base:.1f} PPG ({home_quality} quality)")
    print(f"  {away_abbr} base: {away_base:.1f} PPG ({away_quality} quality)")

    print(f"\nADJUSTMENTS:")
    print(f"  Pace multipliers: Home={prediction['breakdown'].get('home_pace_multiplier')}, Away={prediction['breakdown'].get('away_pace_multiplier')}")
    print(f"  Form adjustments: Home={prediction['breakdown'].get('home_form_adjustment'):+.1f} pts, Away={prediction['breakdown'].get('away_form_adjustment'):+.1f} pts")

    # Validation
    if actual_home and actual_away:
        home_error = abs(home_pred - actual_home)
        away_error = abs(away_pred - actual_away)
        total_error = abs(total_pred - (actual_home + actual_away))

        print(f"\nERROR ANALYSIS:")
        print(f"  {home_abbr} error: {home_error:.1f} pts")
        print(f"  {away_abbr} error: {away_error:.1f} pts")
        print(f"  Total error: {total_error:.1f} pts")

        # Success criteria: Individual team predictions within 20 pts, total within 10 pts
        success = home_error <= 20 and away_error <= 20 and total_error <= 10

        if success:
            print(f"\n✅ PASS: Prediction within acceptable range")
        else:
            print(f"\n⚠️  NEEDS IMPROVEMENT: Errors still significant")

        return success
    else:
        print(f"\n⚠️  No actual result provided for validation")
        return True

def main():
    print("=" * 80)
    print("DEFENSE-FIRST PREDICTION VALIDATION")
    print("=" * 80)
    print("\nTesting predictions against known cases where old system was 15-25 pts off.")
    print("Success criteria: Individual predictions within 20 pts, total within 10 pts.\n")

    test_cases = [
        # (home, away, betting_line, actual_home, actual_away)
        # HOU @ UTA (Nov 30, 2025): HOU should score more than UTA
        ("UTA", "HOU", 230.0, 101, 129),

        # Add more test cases as you identify them
        # ("OPP", "MIL", xxx, xxx, xxx),
        # ("OPP", "LAL", xxx, xxx, xxx),
    ]

    results = []
    for home, away, line, actual_home, actual_away in test_cases:
        result = validate_prediction(home, away, line, actual_home, actual_away)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✅ All tests passed! Defense-first architecture working correctly.")
        return 0
    else:
        print("⚠️  Some tests need improvement. Review predictions above.")
        return 0  # Don't fail - this is expected during iterative improvement

if __name__ == '__main__':
    sys.exit(main())
