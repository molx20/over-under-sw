"""
Assists vs Pace Module

Analyzes team assist rates by game pace tier and location.
Used to understand how teams facilitate ball movement in slow/normal/fast-paced games.

Provides assist splits by:
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


def get_team_assists_vs_pace(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get assist splits by game pace tier and location.

    Aggregates team's assist performance across 6 buckets:
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
        Dictionary with team info, season average assists, and splits by pace/location.
        Returns None if team not found or no data available.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'season_avg_ast': 27.5,
            'splits': {
                'slow': {
                    'home_ast': 26.8,
                    'home_games': 6,
                    'away_ast': 25.3,
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
        # Step 1: Get team info and season average assists
        cursor.execute('''
            SELECT
                t.team_id,
                t.team_abbreviation,
                t.full_name,
                tss.assists as season_avg_ast
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
            'season_avg_ast': team_row['season_avg_ast'] or 0,
            # Field aliases for frontend compatibility
            'overall_avg_assists': team_row['season_avg_ast'] or 0
        }

        # Step 2: Get all games with pace data (ordered by date DESC for last10)
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        cursor.execute('''
            SELECT
                game_date,
                is_home,
                assists as team_assists,
                pace
            FROM team_game_logs
            WHERE team_id = ?
                AND season = ?
                AND assists IS NOT NULL
                AND pace IS NOT NULL
                AND pace > 0
                AND game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY game_date DESC
        ''', (team_id, season))

        games = cursor.fetchall()

        # Step 2.5: Calculate season and last10 home/away splits for assists
        all_asts = [g['team_assists'] for g in games if g['team_assists'] is not None]
        last10_asts = [g['team_assists'] for g in games[:10] if g['team_assists'] is not None]

        home_asts = [g['team_assists'] for g in games if g['team_assists'] is not None and g['is_home'] == 1]
        away_asts = [g['team_assists'] for g in games if g['team_assists'] is not None and g['is_home'] == 0]
        last10_home_asts = [g['team_assists'] for g in games[:10] if g['team_assists'] is not None and g['is_home'] == 1]
        last10_away_asts = [g['team_assists'] for g in games[:10] if g['team_assists'] is not None and g['is_home'] == 0]

        # Update season_avg_ast from actual game logs (more accurate than team_season_stats)
        team_info['season_avg_ast'] = round(sum(all_asts) / len(all_asts), 1) if all_asts else 0
        team_info['last10_avg_ast'] = round(sum(last10_asts) / len(last10_asts), 1) if last10_asts else 0

        # Home/Away splits
        team_info['season_avg_ast_home'] = round(sum(home_asts) / len(home_asts), 1) if home_asts else 0
        team_info['season_avg_ast_away'] = round(sum(away_asts) / len(away_asts), 1) if away_asts else 0
        team_info['last10_avg_ast_home'] = round(sum(last10_home_asts) / len(last10_home_asts), 1) if last10_home_asts else 0
        team_info['last10_avg_ast_away'] = round(sum(last10_away_asts) / len(last10_away_asts), 1) if last10_away_asts else 0

        # Update field aliases
        team_info['overall_avg_assists'] = team_info['season_avg_ast']

        # Step 3: Group games by pace tier and location
        splits = {
            'slow': {'home_ast': [], 'away_ast': []},
            'normal': {'home_ast': [], 'away_ast': []},
            'fast': {'home_ast': [], 'away_ast': []}
        }

        for game in games:
            pace = game['pace']
            pace_tier = get_pace_tier(pace)

            if not pace_tier:
                continue

            location_key = 'home_ast' if game['is_home'] else 'away_ast'
            splits[pace_tier][location_key].append(game['team_assists'])

        # Step 4: Calculate averages and game counts
        result_splits = {}
        for tier in get_all_pace_tiers():
            home_asts = splits[tier]['home_ast']
            away_asts = splits[tier]['away_ast']

            result_splits[tier] = {
                'home_ast': round(sum(home_asts) / len(home_asts), 1) if home_asts else None,
                'home_games': len(home_asts),
                'away_ast': round(sum(away_asts) / len(away_asts), 1) if away_asts else None,
                'away_games': len(away_asts)
            }

        team_info['splits'] = result_splits

        return team_info

    except Exception as e:
        logger.error(f'Error getting assists vs pace for team {team_id}: {e}')
        return None

    finally:
        conn.close()
