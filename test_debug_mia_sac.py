"""Test debug output for MIA vs SAC game"""
import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.db_queries import get_matchup_data
from api.utils.prediction_engine import predict_game_total
import json

# MIA vs SAC game
game_id = '0022500354'
away_team_id = 1610612758  # SAC
home_team_id = 1610612748  # MIA

print("="*80)
print("Testing MIA vs SAC Game - Debug Output")
print("="*80)

# Get matchup data
print(f"\nFetching matchup data for game {game_id}...")
matchup_data = get_matchup_data(home_team_id, away_team_id)

if not matchup_data:
    print("ERROR: Could not fetch matchup data")
    sys.exit(1)

print(f"✓ Matchup data fetched successfully")

# Run prediction
print(f"\nRunning prediction...")
try:
    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line=220.5,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        season='2025-26',
        game_id=game_id
    )

    print(f"\n{'='*80}")
    print("PREDICTION RESULT")
    print(f"{'='*80}")
    print(f"Predicted Total: {prediction.get('predicted_total')}")
    print(f"Home Projected: {prediction.get('breakdown', {}).get('home_projected')}")
    print(f"Away Projected: {prediction.get('breakdown', {}).get('away_projected')}")
    print(f"Game Pace: {prediction.get('breakdown', {}).get('game_pace')}")
    print(f"Difference: {prediction.get('breakdown', {}).get('difference')}")

    print(f"\n{'='*80}")
    print("DEBUG INFO")
    print(f"{'='*80}")
    debug = prediction.get('debug', {})
    print(json.dumps(debug, indent=2))

    if debug.get('using_fallback'):
        print("\n⚠️  FALLBACK WAS TRIGGERED!")
        print("Fallback Reasons:")
        for reason in debug.get('fallback_reasons', []):
            print(f"  - {reason}")

    if debug.get('missing_data'):
        print("\n⚠️  MISSING DATA DETECTED:")
        for item in debug.get('missing_data', []):
            print(f"  - {item}")

    if 'error' in prediction:
        print(f"\n❌ ERROR: {prediction['error']}")

except Exception as e:
    print(f"\n❌ EXCEPTION: {str(e)}")
    import traceback
    traceback.print_exc()
