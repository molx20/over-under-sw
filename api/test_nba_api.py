"""
Test suite for nba_api integration
Run with: python api/test_nba_api.py
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.nba_data import (
    get_all_teams,
    get_team_id,
    get_team_stats,
    get_team_advanced_stats,
    get_team_opponent_stats,
    get_team_last_n_games,
    get_todays_games,
    get_matchup_data,
    get_cache_info,
    clear_cache
)

def test_get_teams():
    """Test 1: Get all teams"""
    print("\n" + "="*60)
    print("TEST 1: Get All Teams")
    print("="*60)

    teams = get_all_teams()
    print(f"✓ Found {len(teams)} NBA teams")
    print(f"Sample teams: {teams[:3]}")

    return len(teams) == 30

def test_get_team_id():
    """Test 2: Get team ID by name"""
    print("\n" + "="*60)
    print("TEST 2: Get Team ID")
    print("="*60)

    test_teams = ['Nets', 'Lakers', 'Warriors', 'Celtics', 'Heat']

    for team_name in test_teams:
        team_id = get_team_id(team_name)
        print(f"✓ {team_name}: {team_id}")

    return True

def test_team_stats():
    """Test 3: Get team stats"""
    print("\n" + "="*60)
    print("TEST 3: Get Team Stats")
    print("="*60)

    nets_id = get_team_id('Nets')
    print(f"Fetching stats for Brooklyn Nets (ID: {nets_id})...")

    stats = get_team_stats(nets_id)

    if stats and stats.get('overall'):
        overall = stats['overall']
        print(f"\n✓ Overall Stats:")
        print(f"  - Games Played: {overall.get('GP', 'N/A')}")
        print(f"  - PPG: {overall.get('PTS', 'N/A')}")
        print(f"  - FG%: {overall.get('FG_PCT', 'N/A')}")
        print(f"  - 3P%: {overall.get('FG3_PCT', 'N/A')}")

        if stats.get('home'):
            home = stats['home']
            print(f"\n✓ Home Stats:")
            print(f"  - Home PPG: {home.get('PTS', 'N/A')}")

        if stats.get('away'):
            away = stats['away']
            print(f"✓ Away Stats:")
            print(f"  - Away PPG: {away.get('PTS', 'N/A')}")

        return True
    else:
        print("✗ Failed to fetch team stats")
        return False

def test_advanced_stats():
    """Test 4: Get advanced stats"""
    print("\n" + "="*60)
    print("TEST 4: Get Advanced Stats")
    print("="*60)

    lakers_id = get_team_id('Lakers')
    print(f"Fetching advanced stats for Lakers (ID: {lakers_id})...")

    advanced = get_team_advanced_stats(lakers_id)

    if advanced:
        print(f"\n✓ Advanced Stats:")
        print(f"  - OFF_RATING: {advanced.get('OFF_RATING', 'N/A')}")
        print(f"  - DEF_RATING: {advanced.get('DEF_RATING', 'N/A')}")
        print(f"  - NET_RATING: {advanced.get('NET_RATING', 'N/A')}")
        print(f"  - PACE: {advanced.get('PACE', 'N/A')}")
        return True
    else:
        print("✗ Failed to fetch advanced stats")
        return False

def test_opponent_stats():
    """Test 5: Get opponent stats"""
    print("\n" + "="*60)
    print("TEST 5: Get Opponent Stats")
    print("="*60)

    celtics_id = get_team_id('Celtics')
    print(f"Fetching opponent stats for Celtics (ID: {celtics_id})...")

    opponent = get_team_opponent_stats(celtics_id)

    if opponent:
        print(f"\n✓ Opponent Stats (what opponents score against team):")
        print(f"  - OPP_PTS: {opponent.get('OPP_PTS', 'N/A')}")
        print(f"  - OPP_FG_PCT: {opponent.get('OPP_FG_PCT', 'N/A')}")
        return True
    else:
        print("✗ Failed to fetch opponent stats")
        return False

def test_recent_games():
    """Test 6: Get recent games"""
    print("\n" + "="*60)
    print("TEST 6: Get Recent Games")
    print("="*60)

    warriors_id = get_team_id('Warriors')
    print(f"Fetching last 5 games for Warriors (ID: {warriors_id})...")

    recent = get_team_last_n_games(warriors_id, n=5)

    if recent:
        print(f"\n✓ Last 5 Games:")
        for i, game in enumerate(recent, 1):
            matchup = game.get('MATCHUP', 'N/A')
            pts = game.get('PTS', 'N/A')
            wl = game.get('WL', 'N/A')
            print(f"  {i}. {matchup} - {pts} pts ({wl})")
        return True
    else:
        print("✗ Failed to fetch recent games")
        return False

def test_todays_games():
    """Test 7: Get today's games"""
    print("\n" + "="*60)
    print("TEST 7: Get Today's Games")
    print("="*60)

    games = get_todays_games()

    if games is not None:
        print(f"\n✓ Found {len(games)} games today")

        if len(games) > 0:
            print("\nToday's Matchups:")
            for game in games:
                print(f"  {game['away_team_name']} @ {game['home_team_name']} - {game['game_status']}")
        else:
            print("  No games scheduled today (this is normal for off-days)")

        return True
    else:
        print("✗ Failed to fetch today's games")
        return False

def test_matchup_data():
    """Test 8: Get full matchup data"""
    print("\n" + "="*60)
    print("TEST 8: Get Full Matchup Data")
    print("="*60)

    nets_id = get_team_id('Nets')
    knicks_id = get_team_id('Knicks')

    print(f"Fetching complete matchup data: Nets vs Knicks...")
    print("This will take ~10-15 seconds due to rate limiting...")

    matchup = get_matchup_data(nets_id, knicks_id)

    if matchup and matchup.get('home') and matchup.get('away'):
        print(f"\n✓ Matchup data successfully fetched!")
        print(f"\nHome Team Data:")
        print(f"  - Stats: {matchup['home']['stats'] is not None}")
        print(f"  - Advanced: {matchup['home']['advanced'] is not None}")
        print(f"  - Opponent: {matchup['home']['opponent'] is not None}")
        print(f"  - Recent Games: {len(matchup['home']['recent_games']) if matchup['home']['recent_games'] else 0}")

        print(f"\nAway Team Data:")
        print(f"  - Stats: {matchup['away']['stats'] is not None}")
        print(f"  - Advanced: {matchup['away']['advanced'] is not None}")
        print(f"  - Opponent: {matchup['away']['opponent'] is not None}")
        print(f"  - Recent Games: {len(matchup['away']['recent_games']) if matchup['away']['recent_games'] else 0}")

        return True
    else:
        print("✗ Failed to fetch matchup data")
        return False

def test_cache():
    """Test 9: Verify caching works"""
    print("\n" + "="*60)
    print("TEST 9: Verify Caching")
    print("="*60)

    # Clear cache first
    clear_cache()
    print("✓ Cache cleared")

    # First call (should miss cache)
    print("\nFirst call (should be slow - fetching from API):")
    nets_id = get_team_id('Nets')
    import time
    start = time.time()
    get_team_stats(nets_id)
    first_duration = time.time() - start

    # Second call (should hit cache)
    print("\nSecond call (should be fast - using cache):")
    start = time.time()
    get_team_stats(nets_id)
    second_duration = time.time() - start

    print(f"\n✓ First call: {first_duration:.2f}s")
    print(f"✓ Second call: {second_duration:.2f}s")
    print(f"✓ Speedup: {first_duration/second_duration:.1f}x faster")

    cache_info = get_cache_info()
    print(f"\n✓ Cache info: {cache_info['cached_items']} items cached")

    return second_duration < first_duration

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("NBA API INTEGRATION TEST SUITE")
    print("="*60)
    print("\nThis will test all nba_api wrapper functions")
    print("Tests may take a few minutes due to API rate limiting")
    print("="*60)

    tests = [
        ("Get All Teams", test_get_teams),
        ("Get Team ID", test_get_team_id),
        ("Get Team Stats", test_team_stats),
        ("Get Advanced Stats", test_advanced_stats),
        ("Get Opponent Stats", test_opponent_stats),
        ("Get Recent Games", test_recent_games),
        ("Get Today's Games", test_todays_games),
        ("Get Matchup Data", test_matchup_data),
        ("Verify Caching", test_cache),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ ERROR in {test_name}: {str(e)}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed! NBA API integration is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above for details.")

if __name__ == "__main__":
    run_all_tests()
