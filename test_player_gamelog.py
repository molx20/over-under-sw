"""
Test PlayerGameLog endpoint for 2025-26 season
Verifies actual NBA API behavior without speculation
"""

from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import time

def test_player_gamelog():
    """Test PlayerGameLog endpoint with 2025-26 season"""

    print("=" * 80)
    print("TESTING: PlayerGameLog for 2025-26 Season")
    print("=" * 80)

    # Test with LeBron James (ID: 2544) - likely to have played games
    test_cases = [
        {"name": "LeBron James", "player_id": 2544},
        {"name": "Stephen Curry", "player_id": 201939},
        {"name": "Kevin Durant", "player_id": 201142},
    ]

    for test_case in test_cases:
        player_name = test_case["name"]
        player_id = test_case["player_id"]

        print(f"\n{'='*80}")
        print(f"Testing: {player_name} (ID: {player_id})")
        print(f"{'='*80}")

        try:
            # Call PlayerGameLog with season "2025-26"
            time.sleep(0.6)  # Rate limiting
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season="2025-26",
                season_type_all_star="Regular Season"
            )

            # Get the dataframe
            df = gamelog.get_data_frames()[0]

            print(f"✅ SUCCESS: Retrieved {len(df)} games")

            if len(df) > 0:
                print(f"\n📊 Available Fields ({len(df.columns)} total):")
                print(", ".join(df.columns.tolist()))

                print(f"\n📝 Sample Game (Most Recent):")
                first_game = df.iloc[0]
                print(f"  Game Date: {first_game.get('GAME_DATE', 'N/A')}")
                print(f"  Matchup: {first_game.get('MATCHUP', 'N/A')}")
                print(f"  Points: {first_game.get('PTS', 'N/A')}")
                print(f"  Assists: {first_game.get('AST', 'N/A')}")
                print(f"  Rebounds: {first_game.get('REB', 'N/A')}")
                print(f"  Minutes: {first_game.get('MIN', 'N/A')}")
                print(f"  FG%: {first_game.get('FG_PCT', 'N/A')}")

                print(f"\n📈 All Available Stats:")
                for col in df.columns:
                    if col not in ['SEASON_ID', 'Player_ID', 'Game_ID', 'GAME_DATE', 'MATCHUP', 'WL']:
                        val = first_game.get(col)
                        if val is not None and val != '':
                            print(f"  {col}: {val}")
            else:
                print("⚠️  Player has 0 games in 2025-26 season")
                print("   (This is EXPECTED if season just started or player hasn't played)")

        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("ENDPOINT VERIFICATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_player_gamelog()
