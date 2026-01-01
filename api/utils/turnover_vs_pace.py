"""
Turnover vs Pace Module

Analyzes team turnover rates by game pace tier and location.
Used to understand how teams handle the ball in slow/normal/fast-paced games.

Provides turnover splits by:
- 3 pace tiers (slow/normal/fast) × 2 locations (home/away)

Pace tiers based on pace (possessions per 48 minutes):
- Slow: < 96 pace
- Normal: 96-101 pace
- Fast: > 101 pace
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


def get_pace_tier(pace: float) -> Optional[str]:
    """
    Convert pace value into pace tier.

    Args:
        pace: Pace (possessions per 48 minutes)

    Returns:
        'slow': < 96 pace
        'normal': 96-101 pace
        'fast': > 101 pace
        None: if pace is invalid
    """
    if pace is None or pace <= 0:
        return None

    if pace < 96:
        return 'slow'
    elif pace <= 101:
        return 'normal'
    else:
        return 'fast'


def get_all_pace_tiers():
    """Return all pace tier names"""
    return ['slow', 'normal', 'fast']


def get_team_turnover_vs_pace(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get turnover splits by game pace tier and location.

    Aggregates team's turnover rates across 6 buckets:
    - Home in Slow pace games (< 96 poss)
    - Home in Normal pace games (96-101 poss)
    - Home in Fast pace games (> 101 poss)
    - Away in Slow pace games
    - Away in Normal pace games
    - Away in Fast pace games

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dictionary with team info, season average turnovers, and splits by pace/location.
        Returns None if team not found or no data available.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'season_avg_turnovers': 12.5,
            'splits': {
                'slow': {
                    'home_turnovers': 11.8,
                    'home_games': 6,
                    'away_turnovers': 12.3,
                    'away_games': 5
                },
                'normal': { ... },
                'fast': { ... }
            }
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Get team info and season average turnovers
        cursor.execute('''
            SELECT
                t.team_id,
                t.team_abbreviation,
                t.full_name,
                tss.turnovers as season_avg_turnovers
            FROM nba_teams t
            LEFT JOIN team_season_stats tss
                ON t.team_id = tss.team_id
                AND tss.season = ?
                AND tss.split_type = 'overall'
            WHERE t.team_id = ?
        ''', (season, team_id))

        team_row = cursor.fetchone()

        if not team_row:
            logger.warning(f'Team {team_id} not found')
            return None

        team_info = {
            'team_id': team_row['team_id'],
            'team_abbreviation': team_row['team_abbreviation'],
            'full_name': team_row['full_name'],
            'season': season,
            'season_avg_turnovers': team_row['season_avg_turnovers'] or 0,
            # SAFE MODE ADDITION: Field aliases for frontend compatibility (no frontend changes needed)
            'overall_avg_turnovers': team_row['season_avg_turnovers'] or 0,  # Frontend expects this field name
            'season_avg_tov': team_row['season_avg_turnovers'] or 0,          # Alternative field name
            'avg_turnovers': team_row['season_avg_turnovers'] or 0            # Alternative field name
        }

        # Step 2: Get all games with pace data
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        cursor.execute('''
            SELECT
                is_home,
                turnovers as team_turnovers,
                pace
            FROM team_game_logs
            WHERE team_id = ?
                AND season = ?
                AND turnovers IS NOT NULL
                AND pace IS NOT NULL
                AND pace > 0
                AND game_type IN ('Regular Season', 'NBA Cup')
        ''', (team_id, season))

        games = cursor.fetchall()

        # Step 3: Group games by pace tier and location
        splits = {
            'slow': {'home_turnovers': [], 'away_turnovers': []},
            'normal': {'home_turnovers': [], 'away_turnovers': []},
            'fast': {'home_turnovers': [], 'away_turnovers': []}
        }

        for game in games:
            pace = game['pace']
            pace_tier = get_pace_tier(pace)

            if not pace_tier:
                continue

            location_key = 'home_turnovers' if game['is_home'] else 'away_turnovers'
            splits[pace_tier][location_key].append(game['team_turnovers'])

        # Step 4: Calculate averages and game counts
        result_splits = {}
        for tier in get_all_pace_tiers():
            home_tovs = splits[tier]['home_turnovers']
            away_tovs = splits[tier]['away_turnovers']

            result_splits[tier] = {
                'home_turnovers': round(sum(home_tovs) / len(home_tovs), 1) if home_tovs else None,
                'home_games': len(home_tovs),
                'away_turnovers': round(sum(away_tovs) / len(away_tovs), 1) if away_tovs else None,
                'away_games': len(away_tovs)
            }

        team_info['splits'] = result_splits

        return team_info

    except Exception as e:
        logger.error(f'Error getting turnover vs pace for team {team_id}: {e}')
        return None

    finally:
        conn.close()
