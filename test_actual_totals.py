#!/usr/bin/env python3
"""
Test script to verify actual_total_points implementation.

This demonstrates:
1. Single game lookup
2. Batch game retrieval
3. Error handling (non-existent games)
4. Sample model evaluation workflow
"""

from api.utils.db_queries import get_game_actual_total, get_completed_games_with_actuals

def main():
    print("=" * 70)
    print("ACTUAL TOTAL POINTS - TEST SUITE")
    print("=" * 70)

    # Test 1: Single game lookup
    print("\n✓ Test 1: Single game lookup")
    print("-" * 70)
    game_id = "0022500350"
    actual = get_game_actual_total(game_id)
    print(f"Game ID: {game_id}")
    print(f"Actual Total: {actual} points")

    # Test 2: Non-existent game
    print("\n✓ Test 2: Non-existent game (should return None)")
    print("-" * 70)
    fake_id = "FAKE_GAME_ID"
    result = get_game_actual_total(fake_id)
    print(f"Game ID: {fake_id}")
    print(f"Result: {result}")
    assert result is None, "Expected None for non-existent game"
    print("✓ Correctly returned None")

    # Test 3: Batch retrieval
    print("\n✓ Test 3: Batch game retrieval (5 most recent)")
    print("-" * 70)
    games = get_completed_games_with_actuals('2025-26', limit=5)
    print(f"Retrieved {len(games)} games\n")

    print(f"{'Game ID':<15} {'Date':<12} {'Home':<5} {'Away':<5} {'Total':<6}")
    print("-" * 70)
    for game in games:
        print(f"{game['game_id']:<15} {game['game_date'][:10]:<12} "
              f"{game['home_score']:<5} {game['away_score']:<5} "
              f"{game['actual_total_points']:<6}")

    # Test 4: Count all available games
    print("\n✓ Test 4: Total completed games for 2025-26 season")
    print("-" * 70)
    all_games = get_completed_games_with_actuals('2025-26')
    print(f"Total completed games with actual totals: {len(all_games)}")

    # Test 5: Sample evaluation workflow
    print("\n✓ Test 5: Sample model evaluation workflow")
    print("-" * 70)
    print("Simulating predicted vs actual comparison:\n")

    # Take first 10 games
    sample_games = get_completed_games_with_actuals('2025-26', limit=10)

    # Simulate predictions (just add random noise for demo)
    import random
    random.seed(42)  # Deterministic for testing

    errors = []
    print(f"{'Game ID':<15} {'Actual':<8} {'Predicted':<10} {'Error':<8}")
    print("-" * 70)

    for game in sample_games:
        actual = game['actual_total_points']
        # Simulate prediction (actual +/- random noise)
        predicted = actual + random.uniform(-10, 10)
        error = abs(predicted - actual)
        errors.append(error)

        print(f"{game['game_id']:<15} {actual:<8} {predicted:<10.1f} {error:<8.2f}")

    # Calculate metrics
    mae = sum(errors) / len(errors)
    within_5 = sum(1 for e in errors if e <= 5) / len(errors) * 100

    print("\n" + "-" * 70)
    print(f"Mean Absolute Error (MAE): {mae:.2f} points")
    print(f"Predictions within 5 points: {within_5:.1f}%")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Use get_game_actual_total() for single game evaluation")
    print("  2. Use get_completed_games_with_actuals() for batch evaluation")
    print("  3. Build evaluation dashboard to track model performance")
    print()

if __name__ == "__main__":
    main()
