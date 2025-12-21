"""
Test script for box score stats syncing.

This tests the new box score fetching functionality that adds:
- steals, blocks
- offensive/defensive rebounds breakdown
- points_off_turnovers, fast_break_points, points_in_paint, second_chance_points
"""

import sqlite3
from api.utils.sync_nba_data import sync_game_logs

def test_box_score_sync():
    """Test syncing game logs with box score stats."""

    print("=" * 70)
    print("BOX SCORE STATS SYNC TEST")
    print("=" * 70)

    # Sync last 3 games for a couple teams (reduces API calls)
    print("\n📥 Syncing last 3 games for LAL and BOS...")
    print("   (This will take ~30-60 seconds due to rate limiting)")

    team_ids = [1610612747, 1610612738]  # LAL and BOS
    records_synced, error = sync_game_logs(
        season='2025-26',  # Current season
        team_ids=team_ids,
        last_n_games=3
    )

    if error:
        print(f"\n❌ Error during sync: {error}")
        return

    print(f"\n✅ Synced {records_synced} game logs")

    # Query the database to verify box score stats were saved
    conn = sqlite3.connect('api/data/nba_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            game_id, team_id, game_date, team_pts,
            fgm, fga,
            offensive_rebounds, defensive_rebounds,
            steals, blocks,
            points_off_turnovers, fast_break_points, points_in_paint, second_chance_points
        FROM team_game_logs
        WHERE team_id IN (?, ?)
        ORDER BY game_date DESC
        LIMIT 6
    """, (1610612747, 1610612738))

    games = cursor.fetchall()

    print("\n" + "=" * 70)
    print("BOX SCORE STATS VERIFICATION")
    print("=" * 70)

    for game in games:
        print(f"\n📊 Game {game['game_id']} - Team {game['team_id']} - {game['game_date']}")
        print(f"   Points: {game['team_pts']}")
        print(f"   FGM/FGA: {game['fgm']}/{game['fga']}")
        print(f"   Rebounds: O:{game['offensive_rebounds']} D:{game['defensive_rebounds']}")
        print(f"   Defense: {game['steals']} STL, {game['blocks']} BLK")
        print(f"   Scoring Breakdown:")
        print(f"     - Fast Break: {game['fast_break_points']} pts")
        print(f"     - Paint: {game['points_in_paint']} pts")
        print(f"     - Off Turnovers: {game['points_off_turnovers']} pts")
        print(f"     - Second Chance: {game['second_chance_points']} pts")

        # Validate data
        missing_fields = []
        if game['steals'] is None:
            missing_fields.append('steals')
        if game['blocks'] is None:
            missing_fields.append('blocks')
        if game['points_off_turnovers'] is None:
            missing_fields.append('points_off_turnovers')
        if game['fast_break_points'] is None:
            missing_fields.append('fast_break_points')
        if game['points_in_paint'] is None:
            missing_fields.append('points_in_paint')
        if game['second_chance_points'] is None:
            missing_fields.append('second_chance_points')

        if missing_fields:
            print(f"   ⚠️  Missing fields: {', '.join(missing_fields)}")
        else:
            print(f"   ✅ All box score fields populated")

    conn.close()

    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    test_box_score_sync()
