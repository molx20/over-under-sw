"""
Turnover vs Defense Pressure Module

Analyzes team turnover rates by opponent defensive pressure tier and location.
Used to understand how teams handle pressure from defenses that force turnovers.

Provides turnover splits by:
- 3 defense pressure tiers (elite/average/low) × 2 locations (home/away)
"""

import sqlite3
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
    from api.utils.turnover_pressure_tiers import get_turnover_pressure_tier
except ImportError:
    from db_config import get_db_path
    from turnover_pressure_tiers import get_turnover_pressure_tier

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_turnover_pressure_tiers():
    """Return all turnover pressure tier names"""
    return ['elite', 'average', 'low']


def get_team_turnover_vs_defense_pressure(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get turnover splits by opponent defensive pressure tier and location.

    Aggregates team's turnover rates across 6 buckets:
    - Home vs Elite pressure defenses (1-10)
    - Home vs Average pressure defenses (11-20)
    - Home vs Low pressure defenses (21-30)
    - Away vs Elite pressure defenses
    - Away vs Average pressure defenses
    - Away vs Low pressure defenses

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dictionary with team info, season average turnovers, and splits by tier/location.
        Returns None if team not found or no data available.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'season_avg_turnovers': 12.5,
            'splits': {
                'elite': {
                    'home_turnovers': 13.2,
                    'home_games': 8,
                    'away_turnovers': 14.1,
                    'away_games': 7
                },
                'average': { ... },
                'low': { ... }
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

        # Step 2: Get opponent turnover forcing ranks for all games (ordered by date DESC for last10)
        # Join team_game_logs with opponent's team_season_stats to get their TOV forced rank
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        cursor.execute('''
            SELECT
                tgl.game_date,
                tgl.is_home,
                tgl.turnovers as team_turnovers,
                opp_stats.opp_tov_rank as opponent_tov_forced_rank
            FROM team_game_logs tgl
            LEFT JOIN team_season_stats opp_stats
                ON tgl.opponent_team_id = opp_stats.team_id
                AND opp_stats.season = ?
                AND opp_stats.split_type = 'overall'
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                AND tgl.turnovers IS NOT NULL
                AND tgl.game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY tgl.game_date DESC
        ''', (season, team_id, season))

        games = cursor.fetchall()

        # Step 3: Calculate both season and last10 stats
        # Season: all games
        season_splits = {
            'elite': {'home_turnovers': [], 'away_turnovers': []},
            'average': {'home_turnovers': [], 'away_turnovers': []},
            'low': {'home_turnovers': [], 'away_turnovers': []}
        }

        # Last10: only most recent 10 games
        last10_splits = {
            'elite': {'home_turnovers': [], 'away_turnovers': []},
            'average': {'home_turnovers': [], 'away_turnovers': []},
            'low': {'home_turnovers': [], 'away_turnovers': []}
        }

        # Calculate season avg and last10 avg turnovers
        all_tovs = [g['team_turnovers'] for g in games if g['team_turnovers'] is not None]
        last10_tovs = [g['team_turnovers'] for g in games[:10] if g['team_turnovers'] is not None]

        team_info['season_avg_turnovers'] = round(sum(all_tovs) / len(all_tovs), 1) if all_tovs else 0
        team_info['last10_avg_turnovers'] = round(sum(last10_tovs) / len(last10_tovs), 1) if last10_tovs else 0

        # Update all field aliases for both season and last10
        team_info['overall_avg_turnovers'] = team_info['season_avg_turnovers']
        team_info['season_avg_tov'] = team_info['season_avg_turnovers']
        team_info['avg_turnovers'] = team_info['season_avg_turnovers']

        # Add last10 aliases
        team_info['last10_avg_tov'] = team_info['last10_avg_turnovers']

        for idx, game in enumerate(games):
            opp_tov_rank = game['opponent_tov_forced_rank']
            pressure_tier = get_turnover_pressure_tier(opp_tov_rank)

            if not pressure_tier:
                continue

            location_key = 'home_turnovers' if game['is_home'] else 'away_turnovers'

            # Add to season splits (all games)
            season_splits[pressure_tier][location_key].append(game['team_turnovers'])

            # Add to last10 splits (only first 10 games, which are most recent due to DESC order)
            if idx < 10:
                last10_splits[pressure_tier][location_key].append(game['team_turnovers'])

        # Step 4: Calculate averages and game counts for season
        result_splits = {}
        for tier in get_all_turnover_pressure_tiers():
            home_tovs = season_splits[tier]['home_turnovers']
            away_tovs = season_splits[tier]['away_turnovers']

            result_splits[tier] = {
                'home_turnovers': round(sum(home_tovs) / len(home_tovs), 1) if home_tovs else None,
                'home_games': len(home_tovs),
                'away_turnovers': round(sum(away_tovs) / len(away_tovs), 1) if away_tovs else None,
                'away_games': len(away_tovs)
            }

        team_info['splits'] = result_splits

        # Step 5: Calculate averages and game counts for last10
        last10_result_splits = {}
        for tier in get_all_turnover_pressure_tiers():
            home_tovs = last10_splits[tier]['home_turnovers']
            away_tovs = last10_splits[tier]['away_turnovers']

            last10_result_splits[tier] = {
                'home_turnovers': round(sum(home_tovs) / len(home_tovs), 1) if home_tovs else None,
                'home_games': len(home_tovs),
                'away_turnovers': round(sum(away_tovs) / len(away_tovs), 1) if away_tovs else None,
                'away_games': len(away_tovs)
            }

        team_info['splits_last10'] = last10_result_splits

        return team_info

    except Exception as e:
        logger.error(f'Error getting turnover vs defense pressure for team {team_id}: {e}')
        return None

    finally:
        conn.close()
