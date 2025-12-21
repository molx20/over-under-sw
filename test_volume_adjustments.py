"""
Test script to verify volume-based adjustments are working correctly.
"""

from api.utils.prediction_engine import predict_total_for_game

# Test with a recent game (we'll use fake IDs to trigger the calculation)
# This will help us see if the volume calculations are being logged correctly

print("=" * 80)
print("Testing Volume-Based Adjustments Integration")
print("=" * 80)

# We need actual team IDs and game IDs from the database
# Let's try to get a recent game
from api.utils.db_queries import get_games_for_date_range
from datetime import datetime, timedelta

# Get games from the last few days
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

print(f"\nFetching games between {start_date} and {end_date}...")
games = get_games_for_date_range(start_date, end_date)

if games and len(games) > 0:
    # Use the first game we find
    test_game = games[0]
    game_id = test_game.get('game_id')
    home_team_id = test_game.get('home_team_id')
    away_team_id = test_game.get('away_team_id')

    print(f"\nTesting with game: {game_id}")
    print(f"Home team ID: {home_team_id}, Away team ID: {away_team_id}")
    print("\n" + "=" * 80)
    print("Running prediction (watch for STEP 7.5 - Volume-Based Adjustments)...")
    print("=" * 80 + "\n")

    # Run prediction
    result = predict_total_for_game(game_id, home_team_id, away_team_id)

    print("\n" + "=" * 80)
    print("PREDICTION RESULT:")
    print("=" * 80)
    print(f"Predicted Total: {result.get('predicted_total')}")
    print(f"Home Projected: {result.get('breakdown', {}).get('home_projected')}")
    print(f"Away Projected: {result.get('breakdown', {}).get('away_projected')}")
    print("\nVolume adjustments should appear in the logs above.")
    print("Look for 'STEP 7.5 - Volume-Based Adjustments' section.")
else:
    print("\nNo recent games found. Cannot test volume adjustments.")
    print("Try syncing recent games first.")
