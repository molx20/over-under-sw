"""
Test methods to retrieve player_id values for active players
"""

from nba_api.stats.static import players
from nba_api.stats.endpoints import commonallplayers
import time

def test_static_players():
    """Test static players module"""
    print("=" * 80)
    print("METHOD 1: nba_api.stats.static.players")
    print("=" * 80)

    try:
        # Get all players
        all_players = players.get_players()

        print(f"✅ SUCCESS: Retrieved {len(all_players)} total players")

        # Show sample active players
        print("\n📝 Sample Players (First 10):")
        for player in all_players[:10]:
            print(f"  ID: {player['id']:6} | Name: {player['full_name']:30} | Active: {player.get('is_active', 'Unknown')}")

        # Filter active players
        active_players = [p for p in all_players if p.get('is_active', False)]
        print(f"\n✅ Found {len(active_players)} active players")

        # Search for specific player
        lebron = players.find_players_by_full_name("LeBron James")
        if lebron:
            print(f"\n🔍 Example Search - LeBron James:")
            print(f"   {lebron[0]}")

        print("\n📋 Fields Available:")
        if all_players:
            print(f"   {list(all_players[0].keys())}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_commonallplayers():
    """Test CommonAllPlayers endpoint for 2025-26"""
    print("\n" + "=" * 80)
    print("METHOD 2: CommonAllPlayers endpoint for 2025-26")
    print("=" * 80)

    try:
        time.sleep(0.6)  # Rate limiting

        # Get all players for 2025-26 season
        all_players_endpoint = commonallplayers.CommonAllPlayers(
            season="2025-26",
            is_only_current_season=1  # Only players active in 2025-26
        )

        df = all_players_endpoint.get_data_frames()[0]

        print(f"✅ SUCCESS: Retrieved {len(df)} players for 2025-26 season")

        print(f"\n📊 Available Fields ({len(df.columns)} total):")
        print(", ".join(df.columns.tolist()))

        print(f"\n📝 Sample Players (First 10):")
        for idx, row in df.head(10).iterrows():
            print(f"  ID: {row['PERSON_ID']:6} | Name: {row['DISPLAY_FIRST_LAST']:30} | Team: {row.get('TEAM_ABBREVIATION', 'N/A'):3}")

        # Filter by team if needed
        lakers = df[df['TEAM_ABBREVIATION'] == 'LAL']
        print(f"\n🏀 Example - Lakers roster: {len(lakers)} players")
        for idx, row in lakers.iterrows():
            print(f"  ID: {row['PERSON_ID']:6} | {row['DISPLAY_FIRST_LAST']}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_static_players()
    test_commonallplayers()

    print("\n" + "=" * 80)
    print("PLAYER ID RETRIEVAL VERIFICATION COMPLETE")
    print("=" * 80)
