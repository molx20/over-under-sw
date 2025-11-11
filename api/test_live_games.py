"""
Test fetching live games for today
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.nba_data import get_todays_games, clear_cache

print("="*60)
print("TESTING LIVE NBA GAMES - 2025-26 Season")
print("="*60)

# Clear cache to get fresh data
print("\nClearing cache to fetch fresh data...")
clear_cache()

# Fetch today's games
print("\nFetching today's NBA games...")
games = get_todays_games()

if games:
    print(f"\n✅ SUCCESS! Found {len(games)} game(s) today:\n")
    for i, game in enumerate(games, 1):
        print(f"{i}. {game['away_team_name']} @ {game['home_team_name']}")
        print(f"   Status: {game['game_status']}")
        if game['home_team_score'] > 0 or game['away_team_score'] > 0:
            print(f"   Score: {game['away_team_name']} {game['away_team_score']} - {game['home_team_name']} {game['home_team_score']}")
        print(f"   Game ID: {game['game_id']}")
        print()
else:
    print("\n⚠️  No games found today.")
    print("This could mean:")
    print("  - No games are scheduled today (off-day)")
    print("  - There's an issue with the NBA API")
    print("\nCheck https://www.nba.com/games for today's schedule")

print("="*60)
