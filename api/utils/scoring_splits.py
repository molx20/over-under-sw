"""
Scoring Splits Module

Aggregates team scoring performance by opponent defense tier and location.
Provides defense-adjusted home/away scoring splits for visualization and analysis.

This module queries team_game_logs and joins with opponent defensive rankings
to compute average points scored in 6 buckets:
- 3 defense tiers (elite/average/bad) × 2 locations (home/away)
"""

import sqlite3
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
    from api.utils.defense_tiers import get_defense_tier, get_all_defense_tiers
except ImportError:
    from db_config import get_db_path
    from defense_tiers import get_defense_tier, get_all_defense_tiers

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_team_scoring_splits(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get defense-adjusted home/away scoring splits for a team.

    Aggregates team's scoring performance across 6 buckets:
    - Home vs Elite defenses
    - Home vs Average defenses
    - Home vs Bad defenses
    - Away vs Elite defenses
    - Away vs Average defenses
    - Away vs Bad defenses

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dictionary with team info, season average PPG, and splits by tier/location.
        Returns None if team not found or no data available.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'season_avg_ppg': 117.5,
            'splits': {
                'elite': {
                    'home_ppg': 115.2,
                    'home_games': 8,
                    'away_ppg': 112.3,
                    'away_games': 7
                },
                'average': { ... },
                'bad': { ... }
            }
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Get team info and season average PPG, rebounds, turnovers
        cursor.execute('''
            SELECT
                t.team_id,
                t.team_abbreviation,
                t.full_name,
                tss.ppg as season_avg_ppg,
                tss.rebounds,
                tss.turnovers
            FROM nba_teams t
            LEFT JOIN team_season_stats tss
                ON t.team_id = tss.team_id
                AND tss.season = ?
                AND tss.split_type = 'overall'
            WHERE t.team_id = ?
        ''', (season, team_id))

        team_row = cursor.fetchone()

        if not team_row:
            logger.warning(f"Team {team_id} not found in database")
            conn.close()
            return None

        team_info = {
            'team_id': team_row['team_id'],
            'team_abbreviation': team_row['team_abbreviation'],
            'full_name': team_row['full_name'],
            'season': season,
            'season_avg_ppg': team_row['season_avg_ppg'],
            # SAFE MODE ADDITION: Field aliases for frontend compatibility (no frontend changes needed)
            'overall_avg_points': team_row['season_avg_ppg'],  # Frontend expects this field name
            'season_avg_pts': team_row['season_avg_ppg'],      # Alternative frontend field name
            # SAFE MODE ADDITION: Turnovers field aliases
            'overall_avg_turnovers': team_row['turnovers'],    # Frontend expects TOV/G
            'season_avg_tov': team_row['turnovers'],           # Alternative field name
            'avg_turnovers': team_row['turnovers'],            # Alternative field name
            # SAFE MODE ADDITION: Rebounds field aliases
            'overall_avg_rebounds': team_row['rebounds'],      # Frontend expects RPG
            'season_avg_reb': team_row['rebounds'],            # Alternative field name
            'avg_rebounds': team_row['rebounds']                # Alternative field name
        }

        # SAFE MODE ADDITION: Calculate offensive/defensive rebounds from game logs
        # (team_season_stats doesn't have these broken down)
        cursor.execute('''
            SELECT
                AVG(offensive_rebounds) as avg_oreb,
                AVG(defensive_rebounds) as avg_dreb
            FROM team_game_logs
            WHERE team_id = ?
                AND season = ?
                AND game_type IN ('Regular Season', 'NBA Cup')
                AND offensive_rebounds IS NOT NULL
                AND defensive_rebounds IS NOT NULL
        ''', (team_id, season))

        reb_row = cursor.fetchone()
        if reb_row:
            team_info['overall_avg_offensive_rebounds'] = round(reb_row['avg_oreb'], 1) if reb_row['avg_oreb'] else 0
            team_info['season_avg_oreb'] = round(reb_row['avg_oreb'], 1) if reb_row['avg_oreb'] else 0
            team_info['avg_offensive_rebounds'] = round(reb_row['avg_oreb'], 1) if reb_row['avg_oreb'] else 0
            team_info['overall_avg_defensive_rebounds'] = round(reb_row['avg_dreb'], 1) if reb_row['avg_dreb'] else 0
            team_info['season_avg_dreb'] = round(reb_row['avg_dreb'], 1) if reb_row['avg_dreb'] else 0
            team_info['avg_defensive_rebounds'] = round(reb_row['avg_dreb'], 1) if reb_row['avg_dreb'] else 0

        # Step 2: Fetch game logs with opponent defensive rankings
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        cursor.execute('''
            SELECT
                tgl.is_home,
                tgl.team_pts,
                tss_opp.def_rtg_rank
            FROM team_game_logs tgl
            LEFT JOIN team_season_stats tss_opp
                ON tgl.opponent_team_id = tss_opp.team_id
                AND tgl.season = tss_opp.season
                AND tss_opp.split_type = 'overall'
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                AND tgl.team_pts IS NOT NULL
                AND tgl.game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY tgl.game_date DESC
        ''', (team_id, season))

        game_logs = cursor.fetchall()

        # Step 3: Aggregate games by tier and location
        # Initialize buckets: {tier: {home: [pts], away: [pts]}}
        buckets = {
            tier: {'home': [], 'away': []}
            for tier in get_all_defense_tiers()
        }

        for game in game_logs:
            def_rank = game['def_rtg_rank']
            tier = get_defense_tier(def_rank)

            # Skip games where opponent defense tier can't be determined
            if tier is None:
                logger.debug(f"Skipping game with missing opponent def_rtg_rank: {def_rank}")
                continue

            location = 'home' if game['is_home'] == 1 else 'away'
            buckets[tier][location].append(game['team_pts'])

        # Step 4: Calculate averages and build response structure
        splits = {}
        for tier in get_all_defense_tiers():
            home_games = buckets[tier]['home']
            away_games = buckets[tier]['away']

            splits[tier] = {
                'home_ppg': round(sum(home_games) / len(home_games), 1) if home_games else None,
                'home_games': len(home_games),
                'away_ppg': round(sum(away_games) / len(away_games), 1) if away_games else None,
                'away_games': len(away_games)
            }

        team_info['splits'] = splits
        conn.close()

        logger.info(f"Generated scoring splits for team {team_id} ({team_info['team_abbreviation']}) - {season}")
        return team_info

    except Exception as e:
        logger.error(f"Error generating scoring splits for team {team_id}: {e}")
        conn.close()
        return None


def get_split_summary_stats(splits_data: Dict) -> Dict:
    """
    Calculate summary statistics from splits data.

    Useful for understanding the overall distribution of scoring across
    different contexts.

    Args:
        splits_data: Output from get_team_scoring_splits()

    Returns:
        Dictionary with summary stats:
        - total_games: Total games across all valid buckets
        - valid_buckets: Number of buckets with data
        - highest_ppg: Highest scoring bucket
        - lowest_ppg: Lowest scoring bucket
        - ppg_range: Difference between highest and lowest
    """
    if not splits_data or 'splits' not in splits_data:
        return {}

    all_ppgs = []
    total_games = 0
    valid_buckets = 0

    for tier, tier_data in splits_data['splits'].items():
        for location in ['home', 'away']:
            ppg_key = f'{location}_ppg'
            games_key = f'{location}_games'

            ppg = tier_data.get(ppg_key)
            games = tier_data.get(games_key, 0)

            if ppg is not None and games > 0:
                all_ppgs.append(ppg)
                total_games += games
                valid_buckets += 1

    if not all_ppgs:
        return {
            'total_games': 0,
            'valid_buckets': 0,
            'highest_ppg': None,
            'lowest_ppg': None,
            'ppg_range': None
        }

    highest = max(all_ppgs)
    lowest = min(all_ppgs)

    return {
        'total_games': total_games,
        'valid_buckets': valid_buckets,
        'highest_ppg': round(highest, 1),
        'lowest_ppg': round(lowest, 1),
        'ppg_range': round(highest - lowest, 1)
    }
