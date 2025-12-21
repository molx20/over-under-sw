#!/usr/bin/env python3
"""
Run predictions for December 8, 2024 games with new contextual profile enhancements.
"""

import sys
sys.path.append('/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.prediction_engine import predict_game_total
from api.utils.db_queries import get_todays_games
from datetime import datetime

def main():
    print("=" * 80)
    print("DECEMBER 8, 2024 - NBA GAME PREDICTIONS")
    print("Running with NEW Contextual Profile Enhancements")
    print("=" * 80)
    print()

    # Get today's games
    season = '2025-26'
    date_str = '2024-12-08'

    games = get_todays_games(season, date_str)

    if not games:
        print(f"No games found for {date_str}")
        return

    print(f"Found {len(games)} games for {date_str}\n")

    for i, game in enumerate(games, 1):
        print(f"\n{'='*80}")
        print(f"GAME {i}: {game['away_team']} @ {game['home_team']}")
        print(f"{'='*80}")

        try:
            # Run prediction
            result = predict_game_total(
                home_team=game['home_team'],
                away_team=game['away_team'],
                season=season,
                betting_line=None  # Let it calculate
            )

            if result and 'predicted_total' in result:
                print(f"\n{'='*80}")
                print(f"PREDICTION SUMMARY:")
                print(f"  Predicted Total: {result['predicted_total']:.1f}")
                print(f"  Home: {result['breakdown']['home_projected']:.1f}")
                print(f"  Away: {result['breakdown']['away_projected']:.1f}")
                print(f"  Recommendation: {result['recommendation']}")
                print(f"{'='*80}")
            else:
                print(f"\n⚠️  Could not generate prediction for this game")

        except Exception as e:
            print(f"\n❌ Error predicting game: {e}")
            import traceback
            traceback.print_exc()

        print()

if __name__ == '__main__':
    main()
