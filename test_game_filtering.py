"""
Test script to verify game filtering logic

Tests:
1. Game classifier correctly identifies game types
2. Database has game_type column populated
3. Filtering returns only Regular Season + NBA Cup games
4. Summer League games are excluded
"""
import os
import sys
import sqlite3

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from api.utils.game_classifier import classify_game, filter_eligible_games, get_game_type_label


def test_game_classifier():
    """Test the game classification logic"""
    print("="*60)
    print("TEST 1: Game Classifier")
    print("="*60)

    test_cases = [
        ('0022501209', '2025-12-12', 'NBA Cup', True),           # Regular season in Dec = NBA Cup period
        ('0022501159', '2025-04-09', 'Regular Season', True),    # Regular season in April
        ('0022400001', '2024-10-22', 'Regular Season', True),    # Regular season in Oct
        ('1322400011', '2024-07-10', 'Summer League', False),    # Summer League
        ('1522400065', '2024-07-20', 'Summer League', False),    # Summer League
        ('0012400001', '2024-10-01', 'Preseason', False),        # Preseason
        ('0032400001', '2025-02-15', 'All-Star', False),         # All-Star
        ('0042400001', '2025-04-15', 'Playoffs', False),         # Playoffs
    ]

    all_passed = True
    for game_id, game_date, expected_type, expected_eligible in test_cases:
        result = classify_game(game_id, game_date)
        game_type = result['game_type']
        is_eligible = result['is_eligible']

        status = "✓" if (game_type == expected_type.lower().replace(' ', '_') and is_eligible == expected_eligible) else "✗"
        if status == "✗":
            all_passed = False

        print(f"{status} {game_id} ({game_date})")
        print(f"   Expected: {expected_type} (eligible={expected_eligible})")
        print(f"   Got: {game_type} (eligible={is_eligible})")

    print(f"\n{'PASS' if all_passed else 'FAIL'}: Game classifier tests")
    return all_passed


def test_database_schema():
    """Test that database has game_type column"""
    print("\n" + "="*60)
    print("TEST 2: Database Schema")
    print("="*60)

    db_path = os.path.join(os.path.dirname(__file__), 'api/data/nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check todays_games
    cursor.execute("PRAGMA table_info(todays_games)")
    columns = [row['name'] for row in cursor.fetchall()]
    has_game_type_todays = 'game_type' in columns
    print(f"{'✓' if has_game_type_todays else '✗'} todays_games has game_type column: {has_game_type_todays}")

    # Check team_game_logs
    cursor.execute("PRAGMA table_info(team_game_logs)")
    columns = [row['name'] for row in cursor.fetchall()]
    has_game_type_logs = 'game_type' in columns
    print(f"{'✓' if has_game_type_logs else '✗'} team_game_logs has game_type column: {has_game_type_logs}")

    conn.close()

    all_passed = has_game_type_todays and has_game_type_logs
    print(f"\n{'PASS' if all_passed else 'FAIL'}: Database schema tests")
    return all_passed


def test_database_population():
    """Test that game_type is populated"""
    print("\n" + "="*60)
    print("TEST 3: Database Population")
    print("="*60)

    db_path = os.path.join(os.path.dirname(__file__), 'api/data/nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check todays_games population
    cursor.execute("SELECT COUNT(*) as total FROM todays_games")
    total_todays = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as populated FROM todays_games WHERE game_type IS NOT NULL")
    populated_todays = cursor.fetchone()['populated']

    print(f"todays_games: {populated_todays}/{total_todays} populated ({100*populated_todays//total_todays if total_todays > 0 else 0}%)")

    # Check team_game_logs population
    cursor.execute("SELECT COUNT(*) as total FROM team_game_logs WHERE season = '2025-26'")
    total_logs = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as populated FROM team_game_logs WHERE season = '2025-26' AND game_type IS NOT NULL")
    populated_logs = cursor.fetchone()['populated']

    print(f"team_game_logs (2025-26): {populated_logs}/{total_logs} populated ({100*populated_logs//total_logs if total_logs > 0 else 0}%)")

    # Show breakdown by game type
    cursor.execute('''
        SELECT game_type, COUNT(*) as count
        FROM team_game_logs
        WHERE season = '2025-26'
        GROUP BY game_type
        ORDER BY count DESC
    ''')
    print("\nGame type breakdown (team_game_logs):")
    for row in cursor.fetchall():
        print(f"  {row['game_type']}: {row['count']}")

    conn.close()

    all_passed = (populated_todays == total_todays) and (populated_logs == total_logs)
    print(f"\n{'PASS' if all_passed else 'FAIL'}: Database population tests")
    return all_passed


def test_filtering_logic():
    """Test that filtering excludes Summer League"""
    print("\n" + "="*60)
    print("TEST 4: Filtering Logic")
    print("="*60)

    db_path = os.path.join(os.path.dirname(__file__), 'api/data/nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all games
    cursor.execute("SELECT game_id, game_date, game_type FROM team_game_logs WHERE season = '2025-26'")
    rows = cursor.fetchall()

    games = [{'game_id': row['game_id'], 'game_date': row['game_date'], 'game_type': row['game_type']} for row in rows]

    conn.close()

    # Apply filtering
    result = filter_eligible_games(games)
    filtered = result['filtered_games']
    stats = result['stats']

    print(f"Total games: {stats['unfiltered_count']}")
    print(f"Filtered (eligible): {stats['filtered_count']}")
    print(f"  Regular Season: {stats['regular_season_count']}")
    print(f"  NBA Cup: {stats['nba_cup_count']}")
    print(f"Excluded: {stats['excluded_count']}")
    if stats['excluded_types']:
        for game_type, count in stats['excluded_types'].items():
            print(f"  - {game_type}: {count}")

    # Verify no Summer League in filtered results
    has_summer_league = any(g.get('game_type') == 'Summer League' for g in filtered)
    has_preseason = any(g.get('game_type') == 'Preseason' for g in filtered)

    print(f"\n{'✓' if not has_summer_league else '✗'} Summer League excluded: {not has_summer_league}")
    print(f"{'✓' if not has_preseason else '✗'} Preseason excluded: {not has_preseason}")

    all_passed = not has_summer_league and not has_preseason
    print(f"\n{'PASS' if all_passed else 'FAIL'}: Filtering logic tests")
    return all_passed


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("GAME FILTERING TEST SUITE")
    print("="*60 + "\n")

    results = []
    results.append(("Game Classifier", test_game_classifier()))
    results.append(("Database Schema", test_database_schema()))
    results.append(("Database Population", test_database_population()))
    results.append(("Filtering Logic", test_filtering_logic()))

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results:
        print(f"{'✓ PASS' if passed else '✗ FAIL'}: {test_name}")

    all_passed = all(passed for _, passed in results)
    print(f"\n{'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
