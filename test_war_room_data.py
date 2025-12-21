#!/usr/bin/env python3
"""Test script to verify War Room data is properly wired"""

import requests
import json

# Test game ID
game_id = "0022501207"

try:
    # Fetch game detail
    response = requests.get(f"http://localhost:8080/api/game_detail?game_id={game_id}")
    data = response.json()

    print("=" * 60)
    print(f"WAR ROOM DATA TEST - {data['away_team']['abbreviation']} @ {data['home_team']['abbreviation']}")
    print("=" * 60)

    # Check home_stats structure
    print("\n📊 HOME STATS:")
    home_stats = data.get('home_stats', {})

    required_fields = [
        'off_rating', 'def_rating', 'ppg', 'fg3_pct', 'pace',
        'paint_pts_per_game', 'ast_pct', 'tov_pct',
        'fg3a_per_game', 'fta_per_game', 'opp_paint_pts_per_game'
    ]

    for field in required_fields:
        value = home_stats.get(field, 'MISSING')
        status = "✓" if value != 'MISSING' and value != 0 else "✗"
        print(f"  {status} {field}: {value}")

    # Check away_stats structure
    print("\n📊 AWAY STATS:")
    away_stats = data.get('away_stats', {})

    for field in required_fields:
        value = away_stats.get(field, 'MISSING')
        status = "✓" if value != 'MISSING' and value != 0 else "✗"
        print(f"  {status} {field}: {value}")

    # Check recent games structure
    print("\n🕐 RECENT GAMES (HOME):")
    home_recent = data.get('home_recent_games', [])
    if home_recent:
        first_game = home_recent[0]
        print(f"  Total games: {len(home_recent)}")
        print(f"  First game: {first_game.get('matchup', 'N/A')}")
        print(f"    team_pts: {first_game.get('team_pts', 'MISSING')}")
        print(f"    opp_pts: {first_game.get('opp_pts', 'MISSING')}")
        print(f"    off_rating: {first_game.get('off_rating', 'MISSING')}")
        print(f"    def_rating: {first_game.get('def_rating', 'MISSING')}")
        print(f"    pace: {first_game.get('pace', 'MISSING')}")
        print(f"    fg3_pct: {first_game.get('fg3_pct', 'MISSING')}")
    else:
        print("  ✗ No recent games found")

    # Summary
    print("\n" + "=" * 60)
    all_fields_present = all(
        home_stats.get(f) not in [None, 'MISSING', 0] and
        away_stats.get(f) not in [None, 'MISSING', 0]
        for f in required_fields
    )

    if all_fields_present and home_recent:
        print("✅ SUCCESS: All War Room fields are populated!")
    else:
        print("⚠️  WARNING: Some fields are missing or zero")
    print("=" * 60)

except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
