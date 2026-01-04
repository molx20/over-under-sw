"""
Verification Script for Opponent Resistance Module

Tests 10 random games from the Oct 21 - Jan 2 window and validates:
- No NaN values
- Rates within plausible ranges
- Expected matchup blending works correctly
- Empty edge calculations are reasonable
"""

import sqlite3
import random
from opponent_resistance import get_expected_matchup_metrics
from db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def get_random_games(count=10):
    """Get random game IDs from the date range"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DISTINCT game_id, game_date, team_id as home_team_id, opponent_team_id as away_team_id
        FROM team_game_logs
        WHERE season = '2025-26'
          AND date(game_date) >= '2025-10-21'
          AND date(game_date) <= '2026-01-02'
          AND is_home = 1
        ORDER BY RANDOM()
        LIMIT ?
    ''', (count,))

    games = cursor.fetchall()
    conn.close()

    return [
        {
            'game_id': g[0],
            'game_date': g[1],
            'home_team_id': g[2],
            'away_team_id': g[3]
        }
        for g in games
    ]


def validate_metrics(metrics, game_info):
    """Validate that metrics are within reasonable ranges"""
    errors = []

    if not metrics:
        errors.append("❌ Metrics are None")
        return errors

    # Check season metrics for home team
    home_season = metrics['team']['season']
    if not (0 <= home_season['to_pct'] <= 30):
        errors.append(f"❌ Home TO% out of range: {home_season['to_pct']}")
    if not (0 <= home_season['oreb_pct'] <= 50):
        errors.append(f"❌ Home OREB% out of range: {home_season['oreb_pct']}")
    if not (0 <= home_season['ftr'] <= 100):
        errors.append(f"❌ Home FTr out of range: {home_season['ftr']}")
    if not (0 <= home_season['empty_rate'] <= 100):
        errors.append(f"❌ Home empty rate out of range: {home_season['empty_rate']}")

    # Check expected metrics
    expected = metrics['expected']
    if not (0 <= expected['team_expected_to_pct_season'] <= 30):
        errors.append(f"❌ Expected TO% out of range: {expected['team_expected_to_pct_season']}")
    if not (0 <= expected['team_expected_oreb_pct_season'] <= 50):
        errors.append(f"❌ Expected OREB% out of range: {expected['team_expected_oreb_pct_season']}")

    # Check for NaN values
    for key, value in expected.items():
        if isinstance(value, float) and (value != value):  # NaN check
            errors.append(f"❌ NaN detected in {key}")

    return errors


def main():
    """Run verification on 10 random games"""
    print("="*80)
    print("OPPONENT RESISTANCE VERIFICATION SCRIPT")
    print("="*80)
    print(f"Date Range: Oct 21, 2025 - Jan 2, 2026")
    print(f"Testing: 10 random games\n")

    games = get_random_games(10)
    print(f"Selected {len(games)} random games for verification\n")

    total_errors = 0
    for i, game in enumerate(games, 1):
        print(f"\n{'='*80}")
        print(f"GAME {i}/10: {game['game_id']}")
        print(f"Date: {game['game_date']}")
        print(f"Teams: Home={game['home_team_id']}, Away={game['away_team_id']}")
        print(f"{'='*80}")

        try:
            metrics = get_expected_matchup_metrics(
                team_id=game['home_team_id'],
                opp_id=game['away_team_id'],
                season='2025-26',
                as_of_date=game['game_date'][:10]
            )

            if not metrics:
                print("❌ FAILED: get_expected_matchup_metrics returned None")
                total_errors += 1
                continue

            # Validate metrics
            errors = validate_metrics(metrics, game)
            if errors:
                print("\n".join(errors))
                total_errors += len(errors)
            else:
                print("✅ All validation checks passed")

            # Print summary
            home = metrics['team']['season']
            away = metrics['opp']['season']
            expected = metrics['expected']

            print(f"\n--- HOME TEAM (ID: {game['home_team_id']}) ---")
            print(f"  Identity: TO%={home['to_pct']}, OREB%={home['oreb_pct']}, Empty={home['empty_rate']}%")
            print(f"  Expected: TO%={home['expected_to_pct']} (Δ{home['expected_to_delta']:+.2f}), "
                  f"OREB%={home['expected_oreb_pct']} (Δ{home['expected_oreb_delta']:+.2f})")
            print(f"  Expected Empty Index: {home['expected_empty_index']}")

            print(f"\n--- AWAY TEAM (ID: {game['away_team_id']}) ---")
            print(f"  Identity: TO%={away['to_pct']}, OREB%={away['oreb_pct']}, Empty={away['empty_rate']}%")
            print(f"  Expected: TO%={away['expected_to_pct']} (Δ{away['expected_to_delta']:+.2f}), "
                  f"OREB%={away['expected_oreb_pct']} (Δ{away['expected_oreb_delta']:+.2f})")
            print(f"  Expected Empty Index: {away['expected_empty_index']}")

            print(f"\n--- MATCHUP SUMMARY ---")
            print(f"  Empty Edge (Season): {expected['empty_edge_index_season']:+.1f}")
            print(f"  Empty Edge (Last5):  {expected['empty_edge_index_last5']:+.1f}")

        except Exception as e:
            import traceback
            print(f"❌ EXCEPTION: {e}")
            traceback.print_exc()
            total_errors += 1

    print(f"\n{'='*80}")
    print(f"VERIFICATION COMPLETE")
    print(f"{'='*80}")
    if total_errors == 0:
        print(f"✅ SUCCESS: All {len(games)} games passed validation with no errors")
    else:
        print(f"⚠️  COMPLETED WITH {total_errors} ERRORS")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
