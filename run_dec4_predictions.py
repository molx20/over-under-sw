#!/usr/bin/env python3
"""
Run predictions for December 4th, 2025 NBA games
"""

import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.db_queries import get_todays_games, get_team_stats, get_team_last_n_games
from api.utils.prediction_engine import predict_game_total

def run_predictions():
    print("=" * 100)
    print("NBA OVER/UNDER PREDICTIONS - DECEMBER 4TH, 2025")
    print("=" * 100)
    print()

    # Get today's games
    games = get_todays_games('2025-26')

    if not games:
        print("No games found for today.")
        return

    print(f"Found {len(games)} games:\n")

    results = []

    for i, game in enumerate(games, 1):
        home_id = game['home_team_id']
        away_id = game['away_team_id']
        home_abbr = game['home_team_name']
        away_abbr = game['away_team_name']
        actual_total = game['home_team_score'] + game['away_team_score']

        print(f"\n{'=' * 100}")
        print(f"GAME {i}: {away_abbr} @ {home_abbr}")
        print(f"{'=' * 100}")
        print(f"Actual Score: {away_abbr} {game['away_team_score']}, {home_abbr} {game['home_team_score']}")
        print(f"Actual Total: {actual_total}")
        print()

        # Get team data
        home_stats = get_team_stats(home_id)
        away_stats = get_team_stats(away_id)
        home_recent = get_team_last_n_games(home_id, n=5)
        away_recent = get_team_last_n_games(away_id, n=5)

        home_data = {
            'stats': home_stats,
            'advanced': home_stats.get('advanced', {}),
            'opponent': home_stats.get('opponent', {}),
            'recent_games': home_recent
        }

        away_data = {
            'stats': away_stats,
            'advanced': away_stats.get('advanced', {}),
            'opponent': away_stats.get('opponent', {}),
            'recent_games': away_recent
        }

        # Use actual total as betting line for reference
        betting_line = actual_total

        try:
            # Run prediction
            result = predict_game_total(
                home_data=home_data,
                away_data=away_data,
                betting_line=betting_line,
                home_team_id=home_id,
                away_team_id=away_id,
                home_team_abbr=home_abbr,
                away_team_abbr=away_abbr,
                season='2025-26'
            )

            predicted_total = result['predicted_total']
            prediction_error = predicted_total - actual_total

            print(f"\n{'─' * 100}")
            print(f"PREDICTION RESULTS:")
            print(f"{'─' * 100}")
            print(f"Predicted Total: {predicted_total:.1f}")
            print(f"Actual Total:    {actual_total}")
            print(f"Error:           {prediction_error:+.1f} points")
            print(f"Accuracy:        {abs(prediction_error):.1f} pts off")

            results.append({
                'game': f"{away_abbr} @ {home_abbr}",
                'predicted': predicted_total,
                'actual': actual_total,
                'error': prediction_error,
                'abs_error': abs(prediction_error)
            })

        except Exception as e:
            print(f"\nError running prediction: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n\n{'=' * 100}")
    print("SUMMARY - ALL GAMES")
    print(f"{'=' * 100}\n")

    if results:
        print(f"{'Game':<25} {'Predicted':>12} {'Actual':>12} {'Error':>12} {'Abs Error':>12}")
        print(f"{'-' * 25} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12}")

        for r in results:
            print(f"{r['game']:<25} {r['predicted']:>12.1f} {r['actual']:>12} {r['error']:>+12.1f} {r['abs_error']:>12.1f}")

        avg_error = sum(r['error'] for r in results) / len(results)
        mae = sum(r['abs_error'] for r in results) / len(results)

        print(f"\n{'-' * 100}")
        print(f"Average Error:        {avg_error:+.2f} points")
        print(f"Mean Absolute Error:  {mae:.2f} points")
        print(f"Games Predicted:      {len(results)}")
        print(f"{'=' * 100}\n")

if __name__ == '__main__':
    run_predictions()
