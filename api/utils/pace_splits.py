"""
Pace Splits Module

Fetches team scoring splits by pace bucket (slow/normal/fast) for both home and away games.
"""

import sqlite3
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
except ImportError:
    from db_config import get_db_path

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_team_pace_splits(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get pace-based home/away scoring splits for a team.

    Args:
        team_id: Team's NBA ID
        season: Season string

    Returns:
        Dict with team info and pace bucket splits:
        {
            'team_id': 1610612744,
            'team_abbreviation': 'GSW',
            'full_name': 'Golden State Warriors',
            'season_avg_ppg': 115.0,
            'pace_splits': {
                'slow': {
                    'home_ppg': 90.5,
                    'away_ppg': 85.2,
                    'home_games': 5,
                    'away_games': 5
                },
                'normal': {...},
                'fast': {...}
            }
        }
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Get team info
        cursor.execute('''
            SELECT team_id, team_abbreviation, full_name
            FROM nba_teams
            WHERE team_id = ? AND season = ?
        ''', (team_id, season))

        team_row = cursor.fetchone()
        if not team_row:
            logger.warning(f'Team {team_id} not found for season {season}')
            conn.close()
            return None

        # Get season average PPG
        cursor.execute('''
            SELECT ppg
            FROM team_season_stats
            WHERE team_id = ? AND season = ? AND split_type = 'overall'
        ''', (team_id, season))

        ppg_row = cursor.fetchone()
        season_avg_ppg = ppg_row['ppg'] if ppg_row and ppg_row['ppg'] else None

        # Get all game logs with pace data
        cursor.execute('''
            SELECT team_pts, pace, is_home
            FROM team_game_logs
            WHERE team_id = ? AND season = ?
                AND team_pts IS NOT NULL
                AND pace IS NOT NULL
        ''', (team_id, season))

        games = cursor.fetchall()
        conn.close()

        if not games:
            logger.warning(f'No game logs found for team {team_id}')
            return None

        # Classify games into pace buckets and split by location
        from api.utils.db_queries import get_pace_bucket

        buckets = {
            'slow': {'home': [], 'away': []},
            'normal': {'home': [], 'away': []},
            'fast': {'home': [], 'away': []}
        }

        for game in games:
            team_pts = game['team_pts']
            pace = game['pace']
            is_home = bool(game['is_home'])

            bucket = get_pace_bucket(pace)
            location = 'home' if is_home else 'away'
            buckets[bucket][location].append(team_pts)

        # Calculate averages for each bucket and location
        pace_splits = {}

        for bucket_name in ['slow', 'normal', 'fast']:
            home_games = buckets[bucket_name]['home']
            away_games = buckets[bucket_name]['away']

            pace_splits[bucket_name] = {
                'home_ppg': sum(home_games) / len(home_games) if home_games else None,
                'away_ppg': sum(away_games) / len(away_games) if away_games else None,
                'home_games': len(home_games),
                'away_games': len(away_games)
            }

        return {
            'team_id': team_row['team_id'],
            'team_abbreviation': team_row['team_abbreviation'],
            'full_name': team_row['full_name'],
            'season_avg_ppg': season_avg_ppg,
            'pace_splits': pace_splits
        }

    except Exception as e:
        logger.error(f'Error fetching pace splits for team {team_id}: {e}')
        import traceback
        traceback.print_exc()
        return None
