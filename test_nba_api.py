#!/usr/bin/env python3
"""
Quick test to diagnose NBA API issues
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from utils.nba_data import get_todays_games, get_team_stats, get_team_advanced_stats
import time

print("=" * 60)
print("NBA API DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Can we get today's games?
print("\n[TEST 1] Fetching today's games...")
start = time.time()
games = get_todays_games()
elapsed = time.time() - start

if games:
    print(f"✅ SUCCESS: Found {len(games)} games ({elapsed:.1f}s)")
    if len(games) > 0:
        game = games[0]
        print(f"   Example: {game['away_team_name']} @ {game['home_team_name']}")
        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']
        print(f"   Home Team ID: {home_team_id}, Away Team ID: {away_team_id}")
else:
    print(f"❌ FAILED: No games found ({elapsed:.1f}s)")
    sys.exit(1)

# Test 2: Can we get team stats?
print(f"\n[TEST 2] Fetching team stats for team {home_team_id}...")
start = time.time()
try:
    stats = get_team_stats(home_team_id, season='2025-26')
    elapsed = time.time() - start

    if stats:
        print(f"✅ SUCCESS: Got team stats ({elapsed:.1f}s)")
        if stats.get('overall'):
            ppg = stats['overall'].get('PTS', 'N/A')
            print(f"   Points per game: {ppg}")
    else:
        print(f"❌ FAILED: No stats returned ({elapsed:.1f}s)")
        print("   Trying 2024-25 season instead...")

        # Try previous season
        start = time.time()
        stats = get_team_stats(home_team_id, season='2024-25')
        elapsed = time.time() - start

        if stats:
            print(f"✅ SUCCESS with 2024-25: Got team stats ({elapsed:.1f}s)")
        else:
            print(f"❌ FAILED: 2024-25 also failed ({elapsed:.1f}s)")

except Exception as e:
    elapsed = time.time() - start
    print(f"❌ EXCEPTION: {str(e)} ({elapsed:.1f}s)")

# Test 3: Can we get advanced stats?
print(f"\n[TEST 3] Fetching advanced stats for team {home_team_id}...")
start = time.time()
try:
    adv_stats = get_team_advanced_stats(home_team_id, season='2025-26')
    elapsed = time.time() - start

    if adv_stats:
        print(f"✅ SUCCESS: Got advanced stats ({elapsed:.1f}s)")
        pace = adv_stats.get('PACE', 'N/A')
        ortg = adv_stats.get('OFF_RATING', 'N/A')
        print(f"   Pace: {pace}, Off Rating: {ortg}")
    else:
        print(f"❌ FAILED: No advanced stats returned ({elapsed:.1f}s)")
except Exception as e:
    elapsed = time.time() - start
    print(f"❌ EXCEPTION: {str(e)} ({elapsed:.1f}s)")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
