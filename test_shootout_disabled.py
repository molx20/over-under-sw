#!/usr/bin/env python3
"""
Test to verify shootout bonus is disabled
"""

import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.db_queries import get_team_by_abbreviation, get_team_stats, get_team_last_n_games
from api.utils.prediction_engine import predict_game_total

# Get BOS and NYK data
home_team = get_team_by_abbreviation('BOS')
away_team = get_team_by_abbreviation('NYK')

if not home_team or not away_team:
    print("Error: Could not find teams")
    sys.exit(1)

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

print("=" * 80)
print("TESTING SHOOTOUT BONUS DISABLED - BOS vs NYK")
print("=" * 80)
print()

# Run prediction
result = predict_game_total(
    home_data=home_data,
    away_data=away_data,
    betting_line=230.5,
    home_team_id=home_team_id,
    away_team_id=away_team_id,
    home_team_abbr='BOS',
    away_team_abbr='NYK',
    season='2025-26'
)

print()
print("=" * 80)
print("FINAL RESULT:")
print("=" * 80)
print(f"Predicted Total: {result['predicted_total']}")
print(f"Recommendation: {result['recommendation']}")
print(f"Confidence: {result['confidence']}%")
print(f"Home Projected: {result['breakdown']['home_projected']}")
print(f"Away Projected: {result['breakdown']['away_projected']}")
print(f"Shootout Bonus Applied: {result['breakdown']['shootout_bonus']}")
print()

# Verify shootout bonus is 0
if result['breakdown']['shootout_bonus'] == 0:
    print("✓✓✓ SUCCESS: Shootout bonus is DISABLED (value = 0)")
else:
    print(f"✗✗✗ FAILED: Shootout bonus is NOT disabled (value = {result['breakdown']['shootout_bonus']})")
print()

# Show shootout detection info
shootout_info = result.get('shootout_detection', {})
print("Shootout Detection Info:")
print(f"  Home shootout applied: {shootout_info.get('home_shootout_applied', False)}")
print(f"  Away shootout applied: {shootout_info.get('away_shootout_applied', False)}")
print(f"  Home reason: {shootout_info.get('home_shootout_reason', 'N/A')}")
print(f"  Away reason: {shootout_info.get('away_shootout_reason', 'N/A')}")
print()
