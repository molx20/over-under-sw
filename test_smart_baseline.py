#!/usr/bin/env python3
"""
Test to verify smart baseline refactor:
- Recent form is now in the baseline (no double-counting)
- Baselines adapt based on trend strength
"""

import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.db_queries import get_team_by_abbreviation, get_team_stats, get_team_last_n_games
from api.utils.prediction_engine import predict_game_total

print("=" * 80)
print("SMART BASELINE TEST - Verify Recent Form Integration")
print("=" * 80)
print()

# Test with 3 different matchups to see different trend types
test_games = [
    ('BOS', 'NYK', 230.5),
    ('GSW', 'LAL', 225.0),
    ('MIL', 'PHI', 220.0)
]

for home_abbr, away_abbr, line in test_games:
    print("\n" + "=" * 80)
    print(f"GAME: {home_abbr} vs {away_abbr} (Line: {line})")
    print("=" * 80)

    # Get teams
    home_team = get_team_by_abbreviation(home_abbr)
    away_team = get_team_by_abbreviation(away_abbr)

    if not home_team or not away_team:
        print(f"Error: Could not find teams {home_abbr}/{away_abbr}")
        continue

    home_team_id = home_team['id']
    away_team_id = away_team['id']

    # Get team stats
    home_stats = get_team_stats(home_team_id)
    away_stats = get_team_stats(away_team_id)

    # Get recent games
    home_recent = get_team_last_n_games(home_team_id, n=5)
    away_recent = get_team_last_n_games(away_team_id, n=5)

    # Prepare data
    home_data = {
        'stats': home_stats,
        'advanced': home_stats.get('advanced', {}),
        'opponent': home_stats.get('opponent', {}),
        'recent_games': home_recent
    }

    away_data = {
        'stats': away_stats,
        'advanced': away_stats.get('advanced', {}),
        'opponent': away_stats.get('opponent', {}),
        'recent_games': away_recent
    }

    # Run prediction
    result = predict_game_total(
        home_data=home_data,
        away_data=away_data,
        betting_line=line,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team_abbr=home_abbr,
        away_team_abbr=away_abbr,
        season='2025-26'
    )

    print("\n" + "-" * 80)
    print("RESULTS:")
    print("-" * 80)
    print(f"Predicted Total: {result['predicted_total']}")
    print(f"Home: {result['breakdown']['home_projected']} | Away: {result['breakdown']['away_projected']}")
    print(f"Line: {line} | Diff: {result['breakdown']['difference']:+.1f}")
    print(f"Recommendation: {result['recommendation']} (Confidence: {result['confidence']}%)")
    print(f"Recent Form Adjustment: {result['breakdown']['home_form_adjustment']:+.1f} / {result['breakdown']['away_form_adjustment']:+.1f}")
    print()

    # Verify form adjustment is 0 (it's in baseline now)
    if result['breakdown']['home_form_adjustment'] == 0 and result['breakdown']['away_form_adjustment'] == 0:
        print("✓ Recent form is in baseline (form_adjustment = 0)")
    else:
        print(f"✗ WARNING: form_adjustment not 0! ({result['breakdown']['home_form_adjustment']}, {result['breakdown']['away_form_adjustment']})")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print()
print("KEY OBSERVATIONS:")
print("- Look for 'Smart Baseline' logs showing trend-adaptive weights")
print("- 'extreme' trend → 60/40 season/recent blend")
print("- 'normal' trend → 70/30 season/recent blend")
print("- 'minimal' trend → 80/20 season/recent blend")
print("- STEP 5 should show 'ALREADY IN BASELINE' (no adjustment)")
print("- form_adjustment should be 0.0 for both teams")
print()
