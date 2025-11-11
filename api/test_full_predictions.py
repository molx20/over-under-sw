"""
Test full prediction functionality with today's live games
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.nba_data import get_todays_games, get_matchup_data, clear_cache
from utils.prediction_engine import predict_game_total

print("="*70)
print("TESTING FULL PREDICTION SYSTEM - 2025-26 Season")
print("="*70)

# Clear cache
print("\nClearing cache...")
clear_cache()

# Get today's games
print("\nFetching today's games...")
games = get_todays_games()

if not games:
    print("❌ No games found today")
    exit(1)

print(f"\n✅ Found {len(games)} games today!")
print("\nGenerating predictions (this will take a few minutes due to rate limiting)...")
print("="*70)

# Test prediction for the first game
first_game = games[0]
print(f"\n📊 Testing prediction for: {first_game['away_team_name']} @ {first_game['home_team_name']}")
print(f"Game Time: {first_game['game_status']}")
print(f"\nFetching team stats...")

try:
    # Get matchup data
    matchup = get_matchup_data(first_game['home_team_id'], first_game['away_team_id'])

    # Generate prediction
    mock_betting_line = 220.5  # Mock line since we don't have odds API yet
    prediction = predict_game_total(matchup['home'], matchup['away'], mock_betting_line)

    print(f"\n{'='*70}")
    print(f"PREDICTION RESULTS")
    print(f"{'='*70}")
    print(f"Betting Line:      {prediction['betting_line']}")
    print(f"Predicted Total:   {prediction['predicted_total']}")
    print(f"Recommendation:    {prediction['recommendation']}")
    print(f"Confidence:        {prediction['confidence']}%")
    print(f"\nBreakdown:")
    print(f"  Home Projected:  {prediction['breakdown']['home_projected']}")
    print(f"  Away Projected:  {prediction['breakdown']['away_projected']}")
    print(f"  Game Pace:       {prediction['breakdown']['game_pace']}")
    print(f"  Difference:      {prediction['breakdown']['difference']}")
    print(f"{'='*70}")

    print(f"\n✅ SUCCESS! Prediction system is fully functional!")
    print(f"\nYou can now run the full app with: npm run dev")

except Exception as e:
    print(f"\n❌ Error generating prediction: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
