"""
Assists Splits Module

Aggregates team assist performance by opponent ball-movement defense tier and location.
Provides defense-adjusted home/away assist splits for visualization and analysis.

This module queries team_game_logs and joins with opponent assists allowed rankings
to compute average assists per game in 6 buckets:
- 3 ball-movement defense tiers (elite/average/bad) × 2 locations (home/away)

Elite ball-movement defense = ranks 1-10 (allows few assists)
Average ball-movement defense = ranks 11-20
Weak ball-movement defense = ranks 21-30 (allows many assists)
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


def get_ball_movement_defense_tier(opp_assists_rank: Optional[int]) -> Optional[str]:
    """
    Classify opponent's ball-movement defense tier based on assists allowed rank.

    Lower rank = fewer assists allowed = better ball-movement defense
    Higher rank = more assists allowed = weaker ball-movement defense

    Args:
        opp_assists_rank: Opponent's assists allowed rank (1-30)

    Returns:
        'elite', 'average', or 'bad' based on rank
        Returns None if rank is invalid/missing
    """
    if opp_assists_rank is None:
        return None

    if 1 <= opp_assists_rank <= 10:
        return 'elite'  # Elite ball-movement defense (allows few assists)
    elif 11 <= opp_assists_rank <= 20:
        return 'average'
    elif 21 <= opp_assists_rank <= 30:
        return 'bad'  # Weak ball-movement defense (allows many assists)

    return None


def get_all_ball_movement_defense_tiers():
    """Return all valid ball-movement defense tier labels"""
    return ['elite', 'average', 'bad']


def get_team_assists_splits(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get ball-movement defense-adjusted home/away assist splits for a team.

    Aggregates team's assist performance across 6 buckets:
    - Home vs Elite ball-movement defenses (allows few assists)
    - Home vs Average ball-movement defenses
    - Home vs Bad ball-movement defenses (allows many assists)
    - Away vs Elite ball-movement defenses
    - Away vs Average ball-movement defenses
    - Away vs Bad ball-movement defenses

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dictionary with team info, season average AST/G, and splits by tier/location.
        Returns None if team not found or no data available.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'season_avg_ast': 27.5,
            'splits': {
                'elite': {
                    'home_ast': 26.2,
                    'home_games': 8,
                    'away_ast': 25.3,
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
        # Step 1: Get team info and season average AST/G
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
            logger.warning(f"Team {team_id} not found in database")
            conn.close()
            return None

        team_info = {
            'team_id': team_row['team_id'],
            'team_abbreviation': team_row['team_abbreviation'],
            'full_name': team_row['full_name'],
            'season': season,
            'season_avg_ast': team_row['season_avg_ast'],
            # SAFE MODE ADDITION: Field aliases for frontend compatibility (no frontend changes needed)
            'overall_avg_assists': team_row['season_avg_ast'],  # Frontend expects assists per game
            'avg_assists': team_row['season_avg_ast']            # Alternative field name
        }

        # Step 2: Fetch game logs with opponent assists allowed rankings
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        cursor.execute('''
            SELECT
                tgl.is_home,
                tgl.assists,
                tgl.opp_assists,
                tss_opp.opp_assists_rank
            FROM team_game_logs tgl
            LEFT JOIN team_season_stats tss_opp
                ON tgl.opponent_team_id = tss_opp.team_id
                AND tgl.season = tss_opp.season
                AND tss_opp.split_type = 'overall'
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                AND tgl.assists IS NOT NULL
                AND tgl.opp_assists IS NOT NULL
                AND tgl.game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY tgl.game_date DESC
        ''', (team_id, season))

        game_logs = cursor.fetchall()

        # Step 2.5: Calculate season and last10 home/away splits for assists
        all_asts = [g['assists'] for g in game_logs if g['assists'] is not None]
        last10_asts = [g['assists'] for g in game_logs[:10] if g['assists'] is not None]

        home_asts = [g['assists'] for g in game_logs if g['assists'] is not None and g['is_home'] == 1]
        away_asts = [g['assists'] for g in game_logs if g['assists'] is not None and g['is_home'] == 0]
        last10_home_asts = [g['assists'] for g in game_logs[:10] if g['assists'] is not None and g['is_home'] == 1]
        last10_away_asts = [g['assists'] for g in game_logs[:10] if g['assists'] is not None and g['is_home'] == 0]

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

        # DEFENSIVE: Opponent assists (assists allowed)
        all_opp_asts = [g['opp_assists'] for g in game_logs if g['opp_assists'] is not None]
        last10_opp_asts = [g['opp_assists'] for g in game_logs[:10] if g['opp_assists'] is not None]

        home_opp_asts = [g['opp_assists'] for g in game_logs if g['opp_assists'] is not None and g['is_home'] == 1]
        away_opp_asts = [g['opp_assists'] for g in game_logs if g['opp_assists'] is not None and g['is_home'] == 0]
        last10_home_opp_asts = [g['opp_assists'] for g in game_logs[:10] if g['opp_assists'] is not None and g['is_home'] == 1]
        last10_away_opp_asts = [g['opp_assists'] for g in game_logs[:10] if g['opp_assists'] is not None and g['is_home'] == 0]

        team_info['season_avg_opp_ast'] = round(sum(all_opp_asts) / len(all_opp_asts), 1) if all_opp_asts else 0
        team_info['last10_avg_opp_ast'] = round(sum(last10_opp_asts) / len(last10_opp_asts), 1) if last10_opp_asts else 0

        # Home/Away splits for defensive
        team_info['season_avg_opp_ast_home'] = round(sum(home_opp_asts) / len(home_opp_asts), 1) if home_opp_asts else 0
        team_info['season_avg_opp_ast_away'] = round(sum(away_opp_asts) / len(away_opp_asts), 1) if away_opp_asts else 0
        team_info['last10_avg_opp_ast_home'] = round(sum(last10_home_opp_asts) / len(last10_home_opp_asts), 1) if last10_home_opp_asts else 0
        team_info['last10_avg_opp_ast_away'] = round(sum(last10_away_opp_asts) / len(last10_away_opp_asts), 1) if last10_away_opp_asts else 0

        # Defensive field aliases
        team_info['overall_avg_opp_assists'] = team_info['season_avg_opp_ast']

        # Step 3: Aggregate games by tier and location
        # Initialize buckets: {tier: {home: [ast], away: [ast]}}
        buckets = {
            tier: {'home': [], 'away': []}
            for tier in get_all_ball_movement_defense_tiers()
        }

        for game in game_logs:
            opp_ast_rank = game['opp_assists_rank']
            tier = get_ball_movement_defense_tier(opp_ast_rank)

            # Skip games where opponent ball-movement tier can't be determined
            if tier is None:
                logger.debug(f"Skipping game with missing opponent opp_assists_rank: {opp_ast_rank}")
                continue

            location = 'home' if game['is_home'] == 1 else 'away'
            buckets[tier][location].append(game['assists'])

        # Step 4: Calculate averages and build response structure
        splits = {}
        for tier in get_all_ball_movement_defense_tiers():
            home_games = buckets[tier]['home']
            away_games = buckets[tier]['away']

            splits[tier] = {
                'home_ast': round(sum(home_games) / len(home_games), 1) if home_games else None,
                'home_games': len(home_games),
                'away_ast': round(sum(away_games) / len(away_games), 1) if away_games else None,
                'away_games': len(away_games)
            }

        team_info['splits'] = splits
        conn.close()

        logger.info(f"Generated assist splits for team {team_id} ({team_info['team_abbreviation']}) - {season}")
        return team_info

    except Exception as e:
        logger.error(f"Error generating assist splits for team {team_id}: {e}")
        conn.close()
        return None
