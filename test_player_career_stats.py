"""
Test PlayerCareerStats endpoint for 2025-26 season
Verifies actual NBA API behavior without speculation
"""

from nba_api.stats.endpoints import playercareerstats
import time

def test_player_career_stats():
    """Test PlayerCareerStats endpoint"""

    print("=" * 80)
    print("TESTING: PlayerCareerStats for 2025-26 Season")
    print("=" * 80)

    # Test with active players
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
            # Call PlayerCareerStats
            time.sleep(0.6)  # Rate limiting
            career = playercareerstats.PlayerCareerStats(
                player_id=player_id,
                per_mode36="PerGame"
            )

            # Get season totals dataframe (index 0)
            df = career.get_data_frames()[0]

            print(f"✅ SUCCESS: Retrieved {len(df)} seasons")

            # Check if 2025-26 season exists
            season_2025_26 = df[df['SEASON_ID'] == '2025-26']

            if len(season_2025_26) > 0:
                print(f"\n✅ 2025-26 SEASON FOUND")

                print(f"\n📊 Available Fields ({len(df.columns)} total):")
                print(", ".join(df.columns.tolist()))

                print(f"\n📝 2025-26 Season Stats:")
                season_row = season_2025_26.iloc[0]
                print(f"  Season: {season_row.get('SEASON_ID', 'N/A')}")
                print(f"  Team: {season_row.get('TEAM_ABBREVIATION', 'N/A')}")
                print(f"  Games Played: {season_row.get('GP', 'N/A')}")
                print(f"  Games Started: {season_row.get('GS', 'N/A')}")
                print(f"  Minutes: {season_row.get('MIN', 'N/A')}")
                print(f"  Points: {season_row.get('PTS', 'N/A')}")
                print(f"  Assists: {season_row.get('AST', 'N/A')}")
                print(f"  Rebounds: {season_row.get('REB', 'N/A')}")
                print(f"  FG%: {season_row.get('FG_PCT', 'N/A')}")
                print(f"  3P%: {season_row.get('FG3_PCT', 'N/A')}")
                print(f"  FT%: {season_row.get('FT_PCT', 'N/A')}")

                print(f"\n📈 All Available Stats for 2025-26:")
                for col in df.columns:
                    if col not in ['PLAYER_ID', 'SEASON_ID', 'LEAGUE_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'PLAYER_AGE']:
                        val = season_row.get(col)
                        if val is not None and val != '':
                            print(f"  {col}: {val}")
            else:
                print("⚠️  2025-26 season NOT YET in career stats")
                print("   (This is EXPECTED if player hasn't played any games yet)")
                print(f"\n   Most recent season available:")
                if len(df) > 0:
                    latest = df.iloc[0]
                    print(f"   Season: {latest.get('SEASON_ID', 'N/A')}")
                    print(f"   Games: {latest.get('GP', 'N/A')}")

        except Exception as e:
            print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("ENDPOINT VERIFICATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_player_career_stats()
