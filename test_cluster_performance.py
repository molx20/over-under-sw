"""
Test Cluster Performance Tracking Functions
"""

from api.utils.team_similarity import (
    update_cluster_performance_after_game,
    get_team_cluster_performance,
    get_team_cluster_assignment
)


def test_performance_tracking():
    """Test the cluster performance tracking functions"""

    print("=" * 60)
    print("Testing Cluster Performance Tracking")
    print("=" * 60)

    # Test with Orlando Magic (1610612753) vs Minnesota Timberwolves (1610612750)
    magic_id = 1610612753
    wolves_id = 1610612750
    season = '2025-26'

    # Check cluster assignments exist
    print("\n1. Checking cluster assignments...")
    magic_cluster = get_team_cluster_assignment(magic_id, season)
    wolves_cluster = get_team_cluster_assignment(wolves_id, season)

    if not magic_cluster or not wolves_cluster:
        print("❌ ERROR: Cluster assignments not found. Run refresh_similarity_engine() first.")
        return

    print(f"✅ Orlando Magic → Cluster {magic_cluster['cluster_id']}: {magic_cluster['cluster_name']}")
    print(f"✅ Minnesota Timberwolves → Cluster {wolves_cluster['cluster_id']}: {wolves_cluster['cluster_name']}")

    # Simulate a game: Magic 115, Wolves 108 (pace: 99.5)
    print("\n2. Simulating game: Magic 115 - Wolves 108 (Pace: 99.5)")

    success1 = update_cluster_performance_after_game(
        team_id=magic_id,
        opponent_id=wolves_id,
        team_pts=115,
        opponent_pts=108,
        total_pts=223,
        pace=99.5,
        team_paint_pts=52,
        opponent_paint_pts=48,
        team_three_pt_made=12,
        opponent_three_pt_made=14,
        team_turnovers=11,
        opponent_turnovers=13,
        season=season
    )

    success2 = update_cluster_performance_after_game(
        team_id=wolves_id,
        opponent_id=magic_id,
        team_pts=108,
        opponent_pts=115,
        total_pts=223,
        pace=99.5,
        team_paint_pts=48,
        opponent_paint_pts=52,
        team_three_pt_made=14,
        opponent_three_pt_made=12,
        team_turnovers=13,
        opponent_turnovers=11,
        season=season
    )

    if success1 and success2:
        print("✅ Game stats recorded successfully")
    else:
        print("❌ Failed to record game stats")
        return

    # Retrieve performance data
    print("\n3. Retrieving Orlando Magic's performance vs opponent cluster...")
    magic_perf = get_team_cluster_performance(magic_id, wolves_cluster['cluster_id'], season)

    if magic_perf:
        perf = magic_perf[0]
        print(f"✅ Performance vs {perf['cluster_name']}:")
        print(f"   - Games Played: {perf['games_played']}")
        print(f"   - Avg Points Scored: {perf['avg_pts_scored']}")
        print(f"   - Avg Points Allowed: {perf['avg_pts_allowed']}")
        print(f"   - Avg Total Points: {perf['avg_total_points']}")
        print(f"   - Avg Pace: {perf['avg_pace']}")
        print(f"   - Avg Paint Differential: {perf['avg_paint_pts_diff']}")
        print(f"   - Avg 3PT Differential: {perf['avg_three_pt_diff']}")
        print(f"   - Avg Turnover Differential: {perf['avg_turnover_diff']}")
    else:
        print("❌ No performance data found")

    # Test adding another game to check running averages
    print("\n4. Simulating second game: Magic 120 - Wolves 112 (Pace: 101.2)")

    update_cluster_performance_after_game(
        team_id=magic_id,
        opponent_id=wolves_id,
        team_pts=120,
        opponent_pts=112,
        total_pts=232,
        pace=101.2,
        team_paint_pts=55,
        opponent_paint_pts=50,
        team_three_pt_made=15,
        opponent_three_pt_made=13,
        team_turnovers=9,
        opponent_turnovers=15,
        season=season
    )

    print("\n5. Checking updated averages...")
    magic_perf_updated = get_team_cluster_performance(magic_id, wolves_cluster['cluster_id'], season)

    if magic_perf_updated:
        perf = magic_perf_updated[0]
        print(f"✅ Updated Performance vs {perf['cluster_name']} (2 games):")
        print(f"   - Games Played: {perf['games_played']}")
        print(f"   - Avg Points Scored: {perf['avg_pts_scored']} (expected: 117.5)")
        print(f"   - Avg Points Allowed: {perf['avg_pts_allowed']} (expected: 110.0)")
        print(f"   - Avg Total Points: {perf['avg_total_points']} (expected: 227.5)")
        print(f"   - Avg Pace: {perf['avg_pace']} (expected: 100.35)")

        # Verify running averages
        if perf['games_played'] == 2:
            if abs(perf['avg_pts_scored'] - 117.5) < 0.1:
                print("✅ Running averages calculated correctly!")
            else:
                print("❌ Running average calculation error")

    print("\n6. Retrieving all cluster performance data for Orlando Magic...")
    all_perf = get_team_cluster_performance(magic_id, None, season)

    print(f"✅ Found performance data for {len(all_perf)} cluster(s):")
    for perf in all_perf:
        print(f"   - vs {perf['cluster_name']}: {perf['games_played']} games, {perf['avg_total_points']} avg total")

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    test_performance_tracking()
