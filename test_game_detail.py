#!/usr/bin/env python3
"""
Test full game detail prediction flow
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from utils.nba_data import get_todays_games, get_matchup_data
from utils.prediction_engine import predict_game_total
import time

print("=" * 60)
print("GAME DETAIL FLOW TEST")
print("=" * 60)

# Get a game
print("\n[STEP 1] Getting today's games...")
games = get_todays_games()
if not games:
    print("❌ No games found")
    sys.exit(1)

game = games[0]
print(f"✅ Testing: {game['away_team_name']} @ {game['home_team_name']}")
print(f"   Game ID: {game['game_id']}")
print(f"   Home: {game['home_team_id']}, Away: {game['away_team_id']}")

# Test matchup data fetch (this is what times out)
print(f"\n[STEP 2] Fetching matchup data (6 API calls)...")
start = time.time()
try:
    matchup_data = get_matchup_data(
        int(game['home_team_id']),
        int(game['away_team_id'])
    )
    elapsed = time.time() - start

    if matchup_data:
        print(f"✅ SUCCESS: Got matchup data ({elapsed:.1f}s)")

        # Check what we got
        home_stats = matchup_data['home']['stats']
        away_stats = matchup_data['away']['stats']

        if home_stats and away_stats:
            print(f"   Home PPG: {home_stats.get('overall', {}).get('PTS', 'N/A')}")
            print(f"   Away PPG: {away_stats.get('overall', {}).get('PTS', 'N/A')}")
    else:
        print(f"❌ FAILED: matchup_data is None ({elapsed:.1f}s)")
        sys.exit(1)

except Exception as e:
    elapsed = time.time() - start
    print(f"❌ EXCEPTION: {str(e)} ({elapsed:.1f}s)")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test prediction generation
print(f"\n[STEP 3] Generating prediction...")
start = time.time()
try:
    prediction = predict_game_total(
        matchup_data['home'],
        matchup_data['away'],
        betting_line=220.5
    )
    elapsed = time.time() - start

    if prediction:
        print(f"✅ SUCCESS: Generated prediction ({elapsed:.3f}s)")
        print(f"   Predicted Total: {prediction['predicted_total']}")
        print(f"   Recommendation: {prediction['recommendation']}")
        print(f"   Confidence: {prediction['confidence']}%")
    else:
        print(f"❌ FAILED: prediction is None ({elapsed:.3f}s)")

except Exception as e:
    elapsed = time.time() - start
    print(f"❌ EXCEPTION: {str(e)} ({elapsed:.3f}s)")
    import traceback
    traceback.print_exc()

total_time = time.time() - start
print(f"\n{'='*60}")
print(f"TOTAL TIME: {total_time:.1f}s")
print(f"{'='*60}")
