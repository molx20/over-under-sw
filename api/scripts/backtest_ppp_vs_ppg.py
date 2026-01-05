"""
Backtest PPP vs PPG Projections

Compares Points Per Possession (PPP) and Points Per Game (PPG) projection methods
on historical games to determine which approach is more accurate.

Usage:
    python -m api.scripts.backtest_ppp_vs_ppg --start 2025-10-21 --end 2026-01-03
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.utils.prediction_engine_v5 import predict_total_for_game_v5
from api.utils.prediction_engine_v5_ppp import predict_total_for_game_v5_ppp
from api.utils.db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def backtest_predictions(
    season: str = '2025-26',
    start_date: str = '2025-10-21',
    end_date: str = '2026-01-03',
    min_games_before: int = 10
) -> pd.DataFrame:
    """
    Backtest both PPG and PPP projections on historical games.

    For each game:
    1. Run PPG projection as-of game date
    2. Run PPP projection as-of game date
    3. Compare to actual total
    4. Track error metrics

    Args:
        season: NBA season
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        min_games_before: Minimum games each team must have played before game

    Returns:
        DataFrame with backtest results
    """
    print("\n" + "=" * 80)
    print("BACKTESTING PPP VS PPG PROJECTIONS")
    print("=" * 80)
    print(f"Season: {season}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Min Games Before: {min_games_before}")
    print()

    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get all completed games in date range
    cursor.execute('''
        SELECT
            game_id,
            game_date,
            MAX(CASE WHEN is_home = 1 THEN team_id END) as home_team_id,
            MAX(CASE WHEN is_home = 0 THEN team_id END) as away_team_id
        FROM team_game_logs
        WHERE season = ? AND game_date >= ? AND game_date <= ?
        GROUP BY game_id
        HAVING COUNT(*) = 2
        ORDER BY game_date
    ''', (season, start_date, end_date))

    games = cursor.fetchall()
    total_games = len(games)

    print(f"Found {total_games} completed games\n")

    results = []
    skipped = 0
    errors = 0

    for idx, game in enumerate(games, 1):
        if idx % 25 == 0:
            print(f"  Progress: {idx}/{total_games} ({(idx/total_games)*100:.1f}%)...")

        game_id = game['game_id']
        game_date = game['game_date']
        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']

        # Get actual total
        cursor.execute('''
            SELECT SUM(team_pts) as actual_total
            FROM team_game_logs
            WHERE game_id = ?
        ''', (game_id,))
        actual_row = cursor.fetchone()
        actual_total = actual_row['actual_total'] if actual_row else None

        if not actual_total:
            skipped += 1
            continue

        # Check if teams have enough games before this game
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM team_game_logs
            WHERE team_id = ? AND season = ? AND game_date < ?
        ''', (home_team_id, season, game_date))
        home_games = cursor.fetchone()['count']

        cursor.execute('''
            SELECT COUNT(*) as count
            FROM team_game_logs
            WHERE team_id = ? AND season = ? AND game_date < ?
        ''', (away_team_id, season, game_date))
        away_games = cursor.fetchone()['count']

        if home_games < min_games_before or away_games < min_games_before:
            skipped += 1
            continue

        # Run both projections as-of game date
        try:
            ppg_result = predict_total_for_game_v5(
                home_team_id, away_team_id,
                season=season, as_of_date=game_date
            )
            ppg_predicted = ppg_result['predicted_total']
            ppg_home = ppg_result['home_projected']
            ppg_away = ppg_result['away_projected']
            ppg_pace = ppg_result['breakdown']['projected_pace']
        except Exception as e:
            errors += 1
            ppg_predicted = None
            ppg_home = None
            ppg_away = None
            ppg_pace = None

        try:
            ppp_result = predict_total_for_game_v5_ppp(
                home_team_id, away_team_id,
                season=season, as_of_date=game_date
            )
            ppp_predicted = ppp_result['predicted_total']
            ppp_home = ppp_result['home_projected']
            ppp_away = ppp_result['away_projected']
            ppp_pace = ppp_result['projected_possessions']
        except Exception as e:
            errors += 1
            ppp_predicted = None
            ppp_home = None
            ppp_away = None
            ppp_pace = None

        if ppg_predicted and ppp_predicted:
            ppg_error = abs(ppg_predicted - actual_total)
            ppp_error = abs(ppp_predicted - actual_total)

            results.append({
                'game_id': game_id,
                'game_date': game_date,
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'actual_total': actual_total,
                'ppg_predicted': ppg_predicted,
                'ppp_predicted': ppp_predicted,
                'ppg_home': ppg_home,
                'ppg_away': ppg_away,
                'ppp_home': ppp_home,
                'ppp_away': ppp_away,
                'projected_pace': ppg_pace,
                'ppg_error': ppg_error,
                'ppp_error': ppp_error,
                'ppg_over_under': 'over' if ppg_predicted > actual_total else 'under',
                'ppp_over_under': 'over' if ppp_predicted > actual_total else 'under',
                'winner': 'ppp' if ppp_error < ppg_error else 'ppg',
                'delta': ppp_predicted - ppg_predicted
            })

    conn.close()

    print(f"\n✅ Backtest complete!")
    print(f"  Total games: {total_games}")
    print(f"  Analyzed: {len(results)}")
    print(f"  Skipped (insufficient data): {skipped}")
    print(f"  Errors: {errors}")

    return pd.DataFrame(results)


def calculate_metrics(results_df: pd.DataFrame) -> Dict:
    """
    Calculate comparison metrics.

    Metrics:
    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Squared Error)
    - False Over Rate
    - PPP Win Rate
    - Average Delta
    """
    if len(results_df) == 0:
        return {'error': 'No results to analyze'}

    ppg_mae = results_df['ppg_error'].mean()
    ppp_mae = results_df['ppp_error'].mean()

    ppg_rmse = np.sqrt((results_df['ppg_error'] ** 2).mean())
    ppp_rmse = np.sqrt((results_df['ppp_error'] ** 2).mean())

    ppg_false_over = (results_df['ppg_over_under'] == 'over').sum() / len(results_df)
    ppp_false_over = (results_df['ppp_over_under'] == 'over').sum() / len(results_df)

    ppp_win_rate = (results_df['winner'] == 'ppp').sum() / len(results_df)

    avg_delta = results_df['delta'].mean()

    return {
        'ppg': {
            'mae': round(ppg_mae, 2),
            'rmse': round(ppg_rmse, 2),
            'over_rate': round(ppg_false_over * 100, 1)
        },
        'ppp': {
            'mae': round(ppp_mae, 2),
            'rmse': round(ppp_rmse, 2),
            'over_rate': round(ppp_false_over * 100, 1)
        },
        'comparison': {
            'ppp_win_rate': round(ppp_win_rate * 100, 1),
            'avg_delta': round(avg_delta, 2),
            'mae_improvement': round(((ppg_mae - ppp_mae) / ppg_mae) * 100, 1),
            'total_games': len(results_df)
        }
    }


def analyze_high_pace_games(results_df: pd.DataFrame, pace_threshold: float = 102) -> Dict:
    """
    Analyze PPP vs PPG performance in high-pace games.

    Hypothesis: PPP should reduce false overs in high-pace scenarios.

    Args:
        results_df: Backtest results
        pace_threshold: Pace threshold for "high pace" games

    Returns:
        Dict with high-pace analysis
    """
    high_pace = results_df[results_df['projected_pace'] >= pace_threshold]

    if len(high_pace) == 0:
        return {'error': f'No games with pace >= {pace_threshold}'}

    ppg_over_rate = (high_pace['ppg_over_under'] == 'over').sum() / len(high_pace)
    ppp_over_rate = (high_pace['ppp_over_under'] == 'over').sum() / len(high_pace)

    ppg_mae = high_pace['ppg_error'].mean()
    ppp_mae = high_pace['ppp_error'].mean()

    avg_actual = high_pace['actual_total'].mean()
    avg_ppg_pred = high_pace['ppg_predicted'].mean()
    avg_ppp_pred = high_pace['ppp_predicted'].mean()

    return {
        'total_games': len(high_pace),
        'pace_threshold': pace_threshold,
        'ppg': {
            'over_rate': round(ppg_over_rate * 100, 1),
            'mae': round(ppg_mae, 2),
            'avg_predicted': round(avg_ppg_pred, 1)
        },
        'ppp': {
            'over_rate': round(ppp_over_rate * 100, 1),
            'mae': round(ppp_mae, 2),
            'avg_predicted': round(avg_ppp_pred, 1)
        },
        'actual_avg': round(avg_actual, 1),
        'over_rate_reduction': round((ppg_over_rate - ppp_over_rate) * 100, 1)
    }


def print_metrics(metrics: Dict, high_pace_metrics: Dict):
    """Print formatted metrics report"""
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)

    print(f"\n📊 Overall Performance ({metrics['comparison']['total_games']} games):")
    print("-" * 80)
    print(f"{'Metric':<20} {'PPG':>15} {'PPP':>15} {'Improvement':>20}")
    print("-" * 80)
    print(f"{'MAE':<20} {metrics['ppg']['mae']:>15.2f} {metrics['ppp']['mae']:>15.2f} {metrics['comparison']['mae_improvement']:>19.1f}%")
    print(f"{'RMSE':<20} {metrics['ppg']['rmse']:>15.2f} {metrics['ppp']['rmse']:>15.2f} {'':>20}")
    print(f"{'Over Rate':<20} {metrics['ppg']['over_rate']:>14.1f}% {metrics['ppp']['over_rate']:>14.1f}% {'':>20}")
    print(f"{'PPP Win Rate':<20} {'':>15} {metrics['comparison']['ppp_win_rate']:>14.1f}% {'':>20}")
    print(f"{'Avg Delta (PPP-PPG)':<20} {'':>15} {metrics['comparison']['avg_delta']:>14.2f} {'':>20}")

    if 'error' not in high_pace_metrics:
        print(f"\n🏃 High-Pace Games (>= {high_pace_metrics['pace_threshold']} possessions, {high_pace_metrics['total_games']} games):")
        print("-" * 80)
        print(f"{'Metric':<20} {'PPG':>15} {'PPP':>15} {'Difference':>20}")
        print("-" * 80)
        print(f"{'Over Rate':<20} {high_pace_metrics['ppg']['over_rate']:>14.1f}% {high_pace_metrics['ppp']['over_rate']:>14.1f}% {high_pace_metrics['over_rate_reduction']:>19.1f}%")
        print(f"{'MAE':<20} {high_pace_metrics['ppg']['mae']:>15.2f} {high_pace_metrics['ppp']['mae']:>15.2f} {'':>20}")
        print(f"{'Avg Predicted':<20} {high_pace_metrics['ppg']['avg_predicted']:>15.1f} {high_pace_metrics['ppp']['avg_predicted']:>15.1f} {'':>20}")
        print(f"{'Actual Avg':<20} {high_pace_metrics['actual_avg']:>15.1f} {'':>15} {'':>20}")

    print("\n" + "=" * 80)

    # Interpretation
    print("\n💡 Interpretation:")
    if metrics['ppp']['mae'] < metrics['ppg']['mae']:
        improvement = metrics['comparison']['mae_improvement']
        print(f"  ✅ PPP is MORE accurate than PPG ({improvement:.1f}% improvement in MAE)")
    else:
        print(f"  ❌ PPG is more accurate than PPP")

    if metrics['comparison']['ppp_win_rate'] > 50:
        print(f"  ✅ PPP wins on {metrics['comparison']['ppp_win_rate']:.1f}% of games")
    else:
        print(f"  ❌ PPG wins on {100 - metrics['comparison']['ppp_win_rate']:.1f}% of games")

    if metrics['comparison']['avg_delta'] > 0:
        print(f"  ⚠️  PPP projects {metrics['comparison']['avg_delta']:.1f} points higher on average")
    else:
        print(f"  ⚠️  PPP projects {abs(metrics['comparison']['avg_delta']):.1f} points lower on average")


def main():
    parser = argparse.ArgumentParser(description='Backtest PPP vs PPG projections')
    parser.add_argument('--season', default='2025-26', help='NBA season')
    parser.add_argument('--start', default='2025-10-21', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2026-01-03', help='End date (YYYY-MM-DD)')
    parser.add_argument('--min-games', type=int, default=10, help='Minimum games before prediction')
    parser.add_argument('--output', help='Output CSV file path')
    parser.add_argument('--pace-threshold', type=float, default=102, help='High pace threshold')

    args = parser.parse_args()

    # Run backtest
    results_df = backtest_predictions(
        season=args.season,
        start_date=args.start,
        end_date=args.end,
        min_games_before=args.min_games
    )

    if len(results_df) == 0:
        print("\n❌ No results to analyze")
        return

    # Calculate metrics
    metrics = calculate_metrics(results_df)
    high_pace_metrics = analyze_high_pace_games(results_df, pace_threshold=args.pace_threshold)

    # Print results
    print_metrics(metrics, high_pace_metrics)

    # Save to CSV if requested
    if args.output:
        results_df.to_csv(args.output, index=False)
        print(f"\n💾 Results saved to: {args.output}")


if __name__ == '__main__':
    main()
