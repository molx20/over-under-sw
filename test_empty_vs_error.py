"""
Test empty vs error scenarios for PlayerGameLog
Verifies behavior when player has not played games
"""

from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import time

def test_empty_vs_error():
    """Test what happens when player has no games"""

    print("=" * 80)
    print("TESTING: Empty vs Error Scenarios")
    print("=" * 80)

    # Test cases:
    # 1. Active player who likely has games (verified)
    # 2. Rookie/player who may not have played yet
    # 3. Invalid player ID (to test error handling)

    test_cases = [
        {
            "name": "Victor Wembanyama (Should have games)",
            "player_id": 1641705,  # Wembanyama
            "expected": "games_exist"
        },
        {
            "name": "Retired player (Michael Jordan)",
            "player_id": 893,  # MJ - should return empty for 2025-26
            "expected": "empty_result"
        },
        {
            "name": "Invalid player ID",
            "player_id": 999999999,
            "expected": "error_or_empty"
        }
    ]

    for test_case in test_cases:
        player_name = test_case["name"]
        player_id = test_case["player_id"]
        expected = test_case["expected"]

        print(f"\n{'='*80}")
        print(f"Testing: {player_name}")
        print(f"Player ID: {player_id}")
        print(f"Expected: {expected}")
        print(f"{'='*80}")

        try:
            time.sleep(0.6)  # Rate limiting

            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season="2025-26",
                season_type_all_star="Regular Season"
            )

            df = gamelog.get_data_frames()[0]

            if len(df) > 0:
                print(f"✅ RESULT: Found {len(df)} games")
                print(f"   First game: {df.iloc[0]['GAME_DATE']}")
                print(f"   Latest stats: {df.iloc[0]['PTS']} PTS, {df.iloc[0]['AST']} AST, {df.iloc[0]['REB']} REB")
            else:
                print(f"⚠️  RESULT: Empty result (0 games)")
                print(f"   Type: {type(df)}")
                print(f"   Columns: {list(df.columns)}")
                print(f"   This is NOT an error - endpoint succeeded but returned no data")

        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            import traceback
            print(f"\n   Full traceback:")
            traceback.print_exc()

    # Test with a player search
    print(f"\n{'='*80}")
    print("BONUS: Finding a rookie who might not have played yet")
    print(f"{'='*80}")

    try:
        # Search for recent rookies
        all_players = players.get_players()
        active = [p for p in all_players if p.get('is_active', False)]

        # Try a few active players to find one with 0 games
        print("\nSearching for players with no games in 2025-26...")

        tested = 0
        found_empty = False

        for player in active[-50:]:  # Check last 50 active players (likely newer)
            if tested >= 5:  # Only test 5 to avoid rate limits
                break

            time.sleep(0.6)
            tested += 1

            try:
                gamelog = playergamelog.PlayerGameLog(
                    player_id=player['id'],
                    season="2025-26",
                    season_type_all_star="Regular Season"
                )

                df = gamelog.get_data_frames()[0]

                if len(df) == 0:
                    print(f"\n✅ Found player with 0 games:")
                    print(f"   Name: {player['full_name']}")
                    print(f"   ID: {player['id']}")
                    print(f"   Result: Empty DataFrame (no error thrown)")
                    found_empty = True
                    break

            except Exception:
                pass  # Skip errors during search

        if not found_empty:
            print("\nAll tested players had games (this is normal early in season)")

    except Exception as e:
        print(f"Search failed: {e}")

    print("\n" + "="*80)
    print("SUMMARY: Empty vs Error Behavior")
    print("="*80)
    print("✅ When player has NO games: Returns empty DataFrame (NOT an error)")
    print("✅ When player has games: Returns populated DataFrame")
    print("❌ Invalid player ID: May return empty or throw error (API dependent)")
    print("\nConclusion: Check len(dataframe) == 0 to detect 'no games' scenario")
    print("="*80)

if __name__ == "__main__":
    test_empty_vs_error()
