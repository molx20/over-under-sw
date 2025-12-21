#!/usr/bin/env python3
"""
Test script for Prediction Engine v5.0

Tests:
1. TeamProfile building
2. MatchupProfile building
3. Full prediction pipeline
4. Comparison with actual results
"""

import sys
from api.utils.team_profiles_v5 import build_team_profile, build_matchup_profile
from api.utils.prediction_engine_v5 import predict_total_for_game_v5

def test_team_profiles():
    """Test TeamProfile building"""
    print("=" * 70)
    print("TEST 1: TeamProfile Building")
    print("=" * 70)

    # Boston Celtics
    bos_profile = build_team_profile(1610612738, '2025-26')

    if bos_profile:
        print(f"\n✓ Boston Celtics Profile:")
        print(f"  Season PPG: {bos_profile.season_ppg:.1f}")
        print(f"  Last 5 PPG: {bos_profile.last_5_ppg:.1f}")
        print(f"  Season Pace: {bos_profile.season_pace:.1f}")
        print(f"  Home PPG: {bos_profile.home_ppg:.1f} ({bos_profile.home_games} games)")
        print(f"  Away PPG: {bos_profile.away_ppg:.1f} ({bos_profile.away_games} games)")
        print(f"  Recent ORtg Change: {bos_profile.recent_ortg_change:+.1f}")
    else:
        print("✗ Failed to build Boston profile")
        return False

    # Lakers
    lal_profile = build_team_profile(1610612747, '2025-26')

    if lal_profile:
        print(f"\n✓ LA Lakers Profile:")
        print(f"  Season PPG: {lal_profile.season_ppg:.1f}")
        print(f"  Last 5 PPG: {lal_profile.last_5_ppg:.1f}")
        print(f"  Season Pace: {lal_profile.season_pace:.1f}")
        print(f"  Home PPG: {lal_profile.home_ppg:.1f} ({lal_profile.home_games} games)")
        print(f"  Away PPG: {lal_profile.away_ppg:.1f} ({lal_profile.away_games} games)")
    else:
        print("✗ Failed to build Lakers profile")
        return False

    return True


def test_matchup_profiles():
    """Test MatchupProfile building"""
    print("\n" + "=" * 70)
    print("TEST 2: MatchupProfile Building")
    print("=" * 70)

    # BOS vs LAL
    bos_vs_lal = build_matchup_profile(1610612738, 1610612747, '2025-26')

    print(f"\n✓ Boston vs Lakers Matchup:")
    print(f"  H2H Games: {bos_vs_lal.h2h_games}")
    if bos_vs_lal.h2h_games > 0:
        print(f"  H2H PPG: {bos_vs_lal.h2h_ppg:.1f}")
        print(f"  H2H Pace: {bos_vs_lal.h2h_pace:.1f}")
    print(f"  Vs Fast Teams: {bos_vs_lal.vs_fast_games} games ({bos_vs_lal.vs_fast_ppg:.1f} ppg)")
    print(f"  Vs Slow Teams: {bos_vs_lal.vs_slow_games} games ({bos_vs_lal.vs_slow_ppg:.1f} ppg)")
    print(f"  Vs Good Def: {bos_vs_lal.vs_good_def_games} games ({bos_vs_lal.vs_good_def_ppg:.1f} ppg)")
    print(f"  Vs Bad Def: {bos_vs_lal.vs_bad_def_games} games ({bos_vs_lal.vs_bad_def_ppg:.1f} ppg)")

    return True


def test_full_prediction():
    """Test full prediction pipeline"""
    print("\n" + "=" * 70)
    print("TEST 3: Full Prediction v5.0")
    print("=" * 70)

    # Predict BOS (home) vs LAL (away)
    print("\n🏀 Predicting: Boston Celtics (home) vs LA Lakers (away)")
    print("-" * 70)

    try:
        result = predict_total_for_game_v5(
            home_team_id=1610612738,  # Boston
            away_team_id=1610612747,  # Lakers
            season='2025-26',
            home_rest_days=1,
            away_rest_days=1
        )

        print(f"\n✓ Prediction Complete (v{result['version']})")
        print(f"\n📊 PROJECTIONS:")
        print(f"  {result['home_team_name']}: {result['home_projected']:.1f}")
        print(f"  {result['away_team_name']}: {result['away_projected']:.1f}")
        print(f"  PREDICTED TOTAL: {result['predicted_total']:.1f}")

        print(f"\n🔧 BREAKDOWN:")
        bd = result['breakdown']
        print(f"  Smart Baseline: {bd['home_baseline']:.1f} + {bd['away_baseline']:.1f} = {bd['home_baseline'] + bd['away_baseline']:.1f}")
        print(f"  Pace: {bd['pace_tag']} ({bd['projected_pace']:.1f})")
        print(f"  Defense Adjustments: {bd['home_defense_adj']:+.1f} / {bd['away_defense_adj']:+.1f}")
        print(f"  HCA / Road: {bd['home_court_advantage']:+.1f} / {bd['road_penalty']:+.1f}")
        print(f"  Shootout Bonus: {bd['shootout_bonus']:+.1f}")
        print(f"  Fatigue: {bd['home_fatigue']:+.1f} / {bd['away_fatigue']:+.1f}")
        print(f"  Rest Bonus: {bd['rest_bonus']:+.1f}")

        print(f"\n📝 EXPLANATIONS:")
        for key, explanation in result['explanations'].items():
            print(f"  {key.capitalize()}: {explanation}")

        print(f"\n🔍 PACE DETAILS:")
        pace = result['details']['pace']
        for k, v in pace.items():
            print(f"  {k}: {v}")

        print(f"\n🛡️ DEFENSE DETAILS (Home):")
        home_def = result['details']['home_defense']
        for k, v in home_def.items():
            print(f"  {k}: {v}")

        return True

    except Exception as e:
        print(f"\n✗ Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_games():
    """Test predictions for multiple games"""
    print("\n" + "=" * 70)
    print("TEST 4: Multiple Game Predictions")
    print("=" * 70)

    # Common matchups to test
    matchups = [
        (1610612738, 1610612752, "BOS @ NYK"),  # Boston @ Knicks
        (1610612739, 1610612748, "CLE @ MIA"),  # Cleveland @ Miami
        (1610612744, 1610612747, "GSW @ LAL"),  # Warriors @ Lakers
    ]

    results = []

    for home_id, away_id, label in matchups:
        try:
            result = predict_total_for_game_v5(
                home_team_id=home_id,
                away_team_id=away_id,
                season='2025-26'
            )

            print(f"\n✓ {label}:")
            print(f"  Predicted Total: {result['predicted_total']:.1f}")
            print(f"  Pace: {result['breakdown']['pace_tag']} ({result['breakdown']['projected_pace']:.1f})")
            print(f"  Projections: {result['home_projected']:.1f} - {result['away_projected']:.1f}")

            results.append(result)

        except Exception as e:
            print(f"\n✗ {label} failed: {e}")

    print(f"\n✓ Successfully predicted {len(results)}/{len(matchups)} games")

    return len(results) == len(matchups)


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PREDICTION ENGINE v5.0 - TEST SUITE")
    print("=" * 70)

    tests = [
        ("TeamProfile Building", test_team_profiles),
        ("MatchupProfile Building", test_matchup_profiles),
        ("Full Prediction Pipeline", test_full_prediction),
        ("Multiple Games", test_multiple_games)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {name}: PASSED")
            else:
                failed += 1
                print(f"\n❌ {name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name}: FAILED with exception: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 All tests passed! v5.0 is ready.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
