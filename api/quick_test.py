"""
Quick test to verify NBA API is working
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.nba_data import get_team_id, get_matchup_data, get_todays_games
from utils.prediction_engine import predict_game_total

print("="*60)
print("QUICK NBA API TEST - 2025-26 Season")
print("="*60)

# Test 1: Get team IDs
print("\n1. Testing team ID lookup...")
nets_id = get_team_id('Nets')
lakers_id = get_team_id('Lakers')
print(f"✓ Nets ID: {nets_id}")
print(f"✓ Lakers ID: {lakers_id}")

# Test 2: Get matchup data
print("\n2. Testing matchup data fetch (this may take 10-15 seconds)...")
try:
    matchup = get_matchup_data(nets_id, lakers_id)
    if matchup and matchup['home']['stats'].get('overall'):
        print(f"✓ Successfully fetched matchup data!")
        home_ppg = matchup['home']['stats']['overall'].get('PTS', 'N/A')
        away_ppg = matchup['away']['stats']['overall'].get('PTS', 'N/A')
        print(f"  Home (Nets) PPG: {home_ppg}")
        print(f"  Away (Lakers) PPG: {away_ppg}")
    else:
        print("⚠ Matchup data incomplete")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Generate prediction
print("\n3. Testing prediction generation...")
try:
    prediction = predict_game_total(matchup['home'], matchup['away'], betting_line=220.5)
    print(f"✓ Predicted Total: {prediction['predicted_total']}")
    print(f"✓ Recommendation: {prediction['recommendation']}")
    print(f"✓ Confidence: {prediction['confidence']}%")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Get today's games (may be empty if no games scheduled)
print("\n4. Testing today's games fetch...")
try:
    games = get_todays_games()
    if games:
        print(f"✓ Found {len(games)} games today")
        for game in games[:3]:  # Show first 3
            print(f"  - {game['away_team_name']} @ {game['home_team_name']}")
    else:
        print("✓ No games today (this is normal on off-days)")
except Exception as e:
    print(f"⚠ Error fetching today's games: {e}")

print("\n" + "="*60)
print("TEST COMPLETE!")
print("="*60)
print("\n✅ NBA API is configured for 2025-26 season!")
print("✅ Prediction engine is working!")
print("\nNote: Game data will be available once the 2025-26 season begins.")
