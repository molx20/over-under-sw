"""
Recent Form Features Module

Computes team recent form metrics from last N games for use in predictions.
Uses team_game_history table if available, falls back to NBA API.

Features computed:
- Recent offensive/defensive ratings vs season averages
- Recent PPG for/against
- Recent pace
- Deltas from season norms (positive = team is hot, negative = cold)
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import sqlite3
import os

# Import NBA data fetcher (now from db_queries - SQLite only, no live API calls)
try:
    from api.utils.db_queries import get_team_last_n_games, get_team_stats_with_ranks
except ImportError:
    from db_queries import get_team_last_n_games, get_team_stats_with_ranks

# Database path for team game history
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions.db')


def compute_recent_form_features(
    team_tricode: str,
    as_of_date: str,
    n: int = 10,
    team_id: Optional[int] = None,
    season: str = '2025-26'
) -> Dict:
    """
    Compute recent form features for a team

    Args:
        team_tricode: Team abbreviation (e.g., 'BOS', 'LAL')
        as_of_date: Date to compute features as of (YYYY-MM-DD format)
        n: Number of recent games to analyze (default 10)
        team_id: NBA team ID (optional, for API fallback)
        season: Season string (e.g., '2025-26')

    Returns:
        Dict containing:
        - recent_off_rtg: Average offensive rating over last N games
        - recent_def_rtg: Average defensive rating
        - recent_ppg_for: Average points scored
        - recent_ppg_against: Average points allowed
        - recent_pace: Average pace
        - season_off_rtg: Season-long offensive rating
        - season_def_rtg: Season-long defensive rating
        - season_pace: Season-long pace
        - recent_off_delta: recent_off_rtg - season_off_rtg (+ = hot, - = cold)
        - recent_def_delta: recent_def_rtg - season_def_rtg (- = improving)
        - recent_pace_delta: recent_pace - season_pace
        - games_found: Number of games actually used
        - data_quality: 'excellent' (10+ games), 'good' (5-9), 'poor' (<5)

    Example:
        >>> features = compute_recent_form_features('BOS', '2025-11-20', n=10)
        >>> features['recent_off_delta']
        -2.9  # Offense cooled off from season average
    """
    print(f'[recent_form] Computing recent form for {team_tricode} as of {as_of_date}, last {n} games')

    # Try to get from database first
    recent_games = _get_recent_games_from_db(team_tricode, as_of_date, n)

    # If insufficient data, fall back to NBA API
    if len(recent_games) < 5 and team_id:
        print(f'[recent_form] Only found {len(recent_games)} games in DB, fetching from NBA API')
        recent_games = _get_recent_games_from_api(team_id, n, season)

    # If still no data, return zeros with warning
    if len(recent_games) == 0:
        print(f'[recent_form] WARNING: No recent games found for {team_tricode}')
        return _empty_form_features(team_tricode, n)

    # Calculate recent averages
    recent_off_rtg = _safe_avg([g.get('off_rtg') for g in recent_games])
    recent_def_rtg = _safe_avg([g.get('def_rtg') for g in recent_games])
    recent_ppg_for = _safe_avg([g.get('points_scored') or g.get('PTS') for g in recent_games])
    recent_ppg_against = _safe_avg([g.get('points_allowed') for g in recent_games])
    recent_pace = _safe_avg([g.get('pace') or g.get('PACE') for g in recent_games])

    # Get season averages from team rankings cache
    season_stats = _get_season_stats(team_tricode, season)

    # Compute deltas
    recent_off_delta = recent_off_rtg - season_stats['off_rtg']
    recent_def_delta = recent_def_rtg - season_stats['def_rtg']
    recent_pace_delta = recent_pace - season_stats['pace']

    # Assess data quality
    if len(recent_games) >= 10:
        quality = 'excellent'
    elif len(recent_games) >= 5:
        quality = 'good'
    else:
        quality = 'poor'

    print(f'[recent_form] {team_tricode}: Found {len(recent_games)} games, quality={quality}')
    print(f'[recent_form] {team_tricode}: OFF delta={recent_off_delta:.1f}, DEF delta={recent_def_delta:.1f}')

    return {
        'team_tricode': team_tricode,
        'recent_off_rtg': round(recent_off_rtg, 1),
        'recent_def_rtg': round(recent_def_rtg, 1),
        'recent_ppg_for': round(recent_ppg_for, 1),
        'recent_ppg_against': round(recent_ppg_against, 1) if recent_ppg_against else 0.0,
        'recent_pace': round(recent_pace, 1),
        'season_off_rtg': round(season_stats['off_rtg'], 1),
        'season_def_rtg': round(season_stats['def_rtg'], 1),
        'season_pace': round(season_stats['pace'], 1),
        'recent_off_delta': round(recent_off_delta, 1),
        'recent_def_delta': round(recent_def_delta, 1),
        'recent_pace_delta': round(recent_pace_delta, 1),
        'games_found': len(recent_games),
        'data_quality': quality
    }


def _get_recent_games_from_db(team_tricode: str, as_of_date: str, n: int) -> list:
    """Get recent games from team_game_history table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                points_scored, points_allowed,
                off_rtg, def_rtg, pace,
                game_date
            FROM team_game_history
            WHERE team_tricode = ? AND game_date < ?
            ORDER BY game_date DESC
            LIMIT ?
        ''', (team_tricode, as_of_date, n))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'points_scored': row[0],
                'points_allowed': row[1],
                'off_rtg': row[2],
                'def_rtg': row[3],
                'pace': row[4],
                'game_date': row[5]
            }
            for row in rows
        ]
    except sqlite3.OperationalError:
        # Table doesn't exist yet (pre-migration)
        return []


def _get_recent_games_from_api(team_id: int, n: int, season: str) -> list:
    """Fallback to NBA API if database doesn't have enough games"""
    try:
        games = get_team_last_n_games(team_id, n=n, season=season)
        return games if games else []
    except Exception as e:
        print(f'[recent_form] Error fetching from NBA API: {e}')
        return []


def _get_season_stats(team_tricode: str, season: str) -> Dict:
    """
    Get season-long stats from team_rankings cache

    Returns dict with off_rtg, def_rtg, pace
    """
    try:
        # Get team ID from database
        from api.utils.db_queries import get_team_by_abbreviation
        team_data = get_team_by_abbreviation(team_tricode)

        if not team_data:
            print(f'[recent_form] WARNING: Could not find team {team_tricode}')
            return {'off_rtg': 115.0, 'def_rtg': 115.0, 'pace': 100.0}  # League averages

        team_id = team_data['id']

        # Get from database
        rankings = get_team_stats_with_ranks(team_id, season)

        if rankings and rankings.get('stats'):
            return {
                'off_rtg': rankings['stats']['off_rtg']['value'],
                'def_rtg': rankings['stats']['def_rtg']['value'],
                'pace': rankings['stats']['pace']['value']
            }
        else:
            print(f'[recent_form] WARNING: No season stats found for {team_tricode}, using defaults')
            return {'off_rtg': 115.0, 'def_rtg': 115.0, 'pace': 100.0}

    except Exception as e:
        print(f'[recent_form] Error getting season stats: {e}')
        return {'off_rtg': 115.0, 'def_rtg': 115.0, 'pace': 100.0}


def _safe_avg(values: list) -> float:
    """Calculate average, filtering out None values"""
    valid = [v for v in values if v is not None and v != 0]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def _empty_form_features(team_tricode: str, n: int) -> Dict:
    """Return empty/zero features when no data available"""
    return {
        'team_tricode': team_tricode,
        'recent_off_rtg': 0.0,
        'recent_def_rtg': 0.0,
        'recent_ppg_for': 0.0,
        'recent_ppg_against': 0.0,
        'recent_pace': 0.0,
        'season_off_rtg': 0.0,
        'season_def_rtg': 0.0,
        'season_pace': 0.0,
        'recent_off_delta': 0.0,
        'recent_def_rtg': 0.0,
        'recent_pace_delta': 0.0,
        'games_found': 0,
        'data_quality': 'none'
    }


def get_last_n_opponents_avg_ranks(team_tricode: str, as_of_date: str, n: int = 5) -> Dict:
    """
    Get average opponent ranks from a team's last N games

    This is used for the opponent-profile adjustment layer to understand
    whether a team's recent performance was against strong/weak opponents.

    Args:
        team_tricode: Team abbreviation (e.g., 'BOS', 'LAL')
        as_of_date: Only consider games before this date (YYYY-MM-DD)
        n: Number of recent games to analyze (default 5)

    Returns:
        Dict with:
            - avg_ppg_rank: Average PPG rank of last N opponents (1-30, lower = better offense)
            - avg_pace_rank: Average Pace rank of last N opponents (1-30, lower = faster)
            - avg_off_rtg_rank: Average Off Rating rank (1-30, lower = better offense)
            - avg_def_rtg_rank: Average Def Rating rank (1-30, lower = better defense)
            - games_found: How many games had rank data
            - opponents: List of opponent details for debugging

    Example:
        >>> get_last_n_opponents_avg_ranks('BOS', '2025-11-20', n=5)
        {
            'avg_ppg_rank': 12.4,
            'avg_pace_rank': 8.6,
            'avg_off_rtg_rank': 11.2,
            'avg_def_rtg_rank': 15.8,
            'games_found': 5,
            'opponents': [
                {'tricode': 'LAL', 'ppg_rank': 15, 'pace_rank': 3, ...},
                ...
            ]
        }
    """
    import sqlite3

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query last N games with opponent rank data
        cursor.execute('''
            SELECT
                opponent_tricode,
                opp_ppg_rank,
                opp_pace_rank,
                opp_off_rtg_rank,
                opp_def_rtg_rank,
                game_date
            FROM team_game_history
            WHERE team_tricode = ?
              AND game_date < ?
              AND opp_ppg_rank IS NOT NULL
            ORDER BY game_date DESC
            LIMIT ?
        ''', (team_tricode, as_of_date, n))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print(f'[recent_form] No opponent rank data found for {team_tricode}')
            return {
                'avg_ppg_rank': None,
                'avg_pace_rank': None,
                'avg_off_rtg_rank': None,
                'avg_def_rtg_rank': None,
                'games_found': 0,
                'opponents': []
            }

        # Extract opponent details
        opponents = []
        ppg_ranks = []
        pace_ranks = []
        off_ranks = []
        def_ranks = []

        for row in rows:
            opp = {
                'tricode': row['opponent_tricode'],
                'ppg_rank': row['opp_ppg_rank'],
                'pace_rank': row['opp_pace_rank'],
                'off_rtg_rank': row['opp_off_rtg_rank'],
                'def_rtg_rank': row['opp_def_rtg_rank'],
                'game_date': row['game_date']
            }
            opponents.append(opp)

            if row['opp_ppg_rank']:
                ppg_ranks.append(row['opp_ppg_rank'])
            if row['opp_pace_rank']:
                pace_ranks.append(row['opp_pace_rank'])
            if row['opp_off_rtg_rank']:
                off_ranks.append(row['opp_off_rtg_rank'])
            if row['opp_def_rtg_rank']:
                def_ranks.append(row['opp_def_rtg_rank'])

        # Compute averages
        return {
            'avg_ppg_rank': _safe_avg(ppg_ranks) if ppg_ranks else None,
            'avg_pace_rank': _safe_avg(pace_ranks) if pace_ranks else None,
            'avg_off_rtg_rank': _safe_avg(off_ranks) if off_ranks else None,
            'avg_def_rtg_rank': _safe_avg(def_ranks) if def_ranks else None,
            'games_found': len(rows),
            'opponents': opponents[:5]  # Return max 5 for display
        }

    except Exception as e:
        print(f'[recent_form] Error querying opponent ranks: {e}')
        return {
            'avg_ppg_rank': None,
            'avg_pace_rank': None,
            'avg_off_rtg_rank': None,
            'avg_def_rtg_rank': None,
            'games_found': 0,
            'opponents': []
        }
