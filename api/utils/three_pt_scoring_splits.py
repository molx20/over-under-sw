"""
Three-Point Scoring Splits Module

Aggregates team 3PT scoring performance by opponent 3PT defense tier and location.
Provides defense-adjusted home/away 3PT scoring splits for visualization and analysis.

This module queries team_game_logs and joins with opponent 3PT defensive rankings
to compute average 3PT points scored in 6 buckets:
- 3 3PT defense tiers (elite/average/bad) × 2 locations (home/away)
"""

import sqlite3
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
    from api.utils.three_pt_defense_tiers import get_3pt_defense_tier
except ImportError:
    from db_config import get_db_path
    from three_pt_defense_tiers import get_3pt_defense_tier

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_3pt_defense_tiers():
    """Return all 3PT defense tier names"""
    return ['elite', 'average', 'bad']


def get_team_three_pt_scoring_splits(team_id: int, season: str = '2025-26') -> Optional[Dict]:
    """
    Get 3PT defense-adjusted home/away 3PT scoring splits for a team.

    Aggregates team's 3PT scoring performance across 6 buckets:
    - Home vs Elite 3PT defenses
    - Home vs Average 3PT defenses
    - Home vs Bad 3PT defenses
    - Away vs Elite 3PT defenses
    - Away vs Average 3PT defenses
    - Away vs Bad 3PT defenses

    Args:
        team_id: NBA team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dictionary with team info, season average 3PT PPG, and splits by tier/location.
        Returns None if team not found or no data available.

    Response Structure:
        {
            'team_id': 1610612738,
            'team_abbreviation': 'BOS',
            'full_name': 'Boston Celtics',
            'season': '2025-26',
            'season_avg_three_pt_ppg': 42.5,
            'splits': {
                'elite': {
                    'home_three_pt_ppg': 40.2,
                    'home_games': 8,
                    'away_three_pt_ppg': 38.3,
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
        # Step 1: Get team info and season average 3PT PPG
        cursor.execute('''
            SELECT
                t.team_id,
                t.team_abbreviation,
                t.full_name,
                tss.three_pt_ppg as season_avg_three_pt_ppg,
                tss.fg3m,
                tss.fg3_pct
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
            'season_avg_three_pt_ppg': team_row['season_avg_three_pt_ppg'],
            # SAFE MODE ADDITION: Field aliases for frontend compatibility (no frontend changes needed)
            'overall_avg_fg3m': team_row['fg3m'],           # Frontend expects 3PM per game
            'season_avg_fg3m': team_row['fg3m'],            # Alternative field name
            'overall_avg_fg3_pct': team_row['fg3_pct'],     # Frontend expects 3P%
            'season_avg_fg3_pct': team_row['fg3_pct']       # Alternative field name
        }

        # Step 2: Fetch game logs with opponent 3PT defensive rankings
        # FILTER: Only Regular Season + NBA Cup (exclude Summer League, preseason, etc.)
        cursor.execute('''
            SELECT
                tgl.is_home,
                tgl.fg3m,
                tgl.fg3a,
                tgl.opp_fg3m,
                tgl.opp_fg3a,
                tss_opp.opp_fg3_pct_rank
            FROM team_game_logs tgl
            LEFT JOIN team_season_stats tss_opp
                ON tgl.opponent_team_id = tss_opp.team_id
                AND tgl.season = tss_opp.season
                AND tss_opp.split_type = 'overall'
            WHERE tgl.team_id = ?
                AND tgl.season = ?
                AND tgl.fg3m IS NOT NULL
                AND tgl.fg3a IS NOT NULL
                AND tgl.opp_fg3m IS NOT NULL
                AND tgl.opp_fg3a IS NOT NULL
                AND tgl.game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY tgl.game_date DESC
        ''', (team_id, season))

        game_logs = cursor.fetchall()

        # Step 2.5: Calculate season and last10 home/away splits for 3PT stats
        all_fg3m = [g['fg3m'] for g in game_logs]
        all_fg3a = [g['fg3a'] for g in game_logs]
        last10_fg3m = [g['fg3m'] for g in game_logs[:10]]
        last10_fg3a = [g['fg3a'] for g in game_logs[:10]]

        home_fg3m = [g['fg3m'] for g in game_logs if g['is_home'] == 1]
        home_fg3a = [g['fg3a'] for g in game_logs if g['is_home'] == 1]
        away_fg3m = [g['fg3m'] for g in game_logs if g['is_home'] == 0]
        away_fg3a = [g['fg3a'] for g in game_logs if g['is_home'] == 0]

        last10_home_fg3m = [g['fg3m'] for g in game_logs[:10] if g['is_home'] == 1]
        last10_home_fg3a = [g['fg3a'] for g in game_logs[:10] if g['is_home'] == 1]
        last10_away_fg3m = [g['fg3m'] for g in game_logs[:10] if g['is_home'] == 0]
        last10_away_fg3a = [g['fg3a'] for g in game_logs[:10] if g['is_home'] == 0]

        # 3PT Makes (3PM)
        team_info['season_avg_fg3m'] = round(sum(all_fg3m) / len(all_fg3m), 1) if all_fg3m else 0
        team_info['last10_avg_fg3m'] = round(sum(last10_fg3m) / len(last10_fg3m), 1) if last10_fg3m else 0
        team_info['season_avg_fg3m_home'] = round(sum(home_fg3m) / len(home_fg3m), 1) if home_fg3m else 0
        team_info['season_avg_fg3m_away'] = round(sum(away_fg3m) / len(away_fg3m), 1) if away_fg3m else 0
        team_info['last10_avg_fg3m_home'] = round(sum(last10_home_fg3m) / len(last10_home_fg3m), 1) if last10_home_fg3m else 0
        team_info['last10_avg_fg3m_away'] = round(sum(last10_away_fg3m) / len(last10_away_fg3m), 1) if last10_away_fg3m else 0

        # 3PT Percentage (3P%)
        team_info['season_avg_fg3_pct'] = round((sum(all_fg3m) / sum(all_fg3a) * 100), 1) if all_fg3a and sum(all_fg3a) > 0 else 0
        team_info['last10_avg_fg3_pct'] = round((sum(last10_fg3m) / sum(last10_fg3a) * 100), 1) if last10_fg3a and sum(last10_fg3a) > 0 else 0
        team_info['season_avg_fg3_pct_home'] = round((sum(home_fg3m) / sum(home_fg3a) * 100), 1) if home_fg3a and sum(home_fg3a) > 0 else 0
        team_info['season_avg_fg3_pct_away'] = round((sum(away_fg3m) / sum(away_fg3a) * 100), 1) if away_fg3a and sum(away_fg3a) > 0 else 0
        team_info['last10_avg_fg3_pct_home'] = round((sum(last10_home_fg3m) / sum(last10_home_fg3a) * 100), 1) if last10_home_fg3a and sum(last10_home_fg3a) > 0 else 0
        team_info['last10_avg_fg3_pct_away'] = round((sum(last10_away_fg3m) / sum(last10_away_fg3a) * 100), 1) if last10_away_fg3a and sum(last10_away_fg3a) > 0 else 0

        # Update field aliases
        team_info['overall_avg_fg3m'] = team_info['season_avg_fg3m']
        team_info['overall_avg_fg3_pct'] = team_info['season_avg_fg3_pct']

        # DEFENSIVE: Opponent 3PT stats (3PT allowed)
        all_opp_fg3m = [g['opp_fg3m'] for g in game_logs]
        all_opp_fg3a = [g['opp_fg3a'] for g in game_logs]
        last10_opp_fg3m = [g['opp_fg3m'] for g in game_logs[:10]]
        last10_opp_fg3a = [g['opp_fg3a'] for g in game_logs[:10]]

        home_opp_fg3m = [g['opp_fg3m'] for g in game_logs if g['is_home'] == 1]
        home_opp_fg3a = [g['opp_fg3a'] for g in game_logs if g['is_home'] == 1]
        away_opp_fg3m = [g['opp_fg3m'] for g in game_logs if g['is_home'] == 0]
        away_opp_fg3a = [g['opp_fg3a'] for g in game_logs if g['is_home'] == 0]

        last10_home_opp_fg3m = [g['opp_fg3m'] for g in game_logs[:10] if g['is_home'] == 1]
        last10_home_opp_fg3a = [g['opp_fg3a'] for g in game_logs[:10] if g['is_home'] == 1]
        last10_away_opp_fg3m = [g['opp_fg3m'] for g in game_logs[:10] if g['is_home'] == 0]
        last10_away_opp_fg3a = [g['opp_fg3a'] for g in game_logs[:10] if g['is_home'] == 0]

        # Opponent 3PT Makes (3PM allowed)
        team_info['season_avg_opp_fg3m'] = round(sum(all_opp_fg3m) / len(all_opp_fg3m), 1) if all_opp_fg3m else 0
        team_info['last10_avg_opp_fg3m'] = round(sum(last10_opp_fg3m) / len(last10_opp_fg3m), 1) if last10_opp_fg3m else 0
        team_info['season_avg_opp_fg3m_home'] = round(sum(home_opp_fg3m) / len(home_opp_fg3m), 1) if home_opp_fg3m else 0
        team_info['season_avg_opp_fg3m_away'] = round(sum(away_opp_fg3m) / len(away_opp_fg3m), 1) if away_opp_fg3m else 0
        team_info['last10_avg_opp_fg3m_home'] = round(sum(last10_home_opp_fg3m) / len(last10_home_opp_fg3m), 1) if last10_home_opp_fg3m else 0
        team_info['last10_avg_opp_fg3m_away'] = round(sum(last10_away_opp_fg3m) / len(last10_away_opp_fg3m), 1) if last10_away_opp_fg3m else 0

        # Opponent 3PT Percentage (3P% allowed)
        team_info['season_avg_opp_fg3_pct'] = round((sum(all_opp_fg3m) / sum(all_opp_fg3a) * 100), 1) if all_opp_fg3a and sum(all_opp_fg3a) > 0 else 0
        team_info['last10_avg_opp_fg3_pct'] = round((sum(last10_opp_fg3m) / sum(last10_opp_fg3a) * 100), 1) if last10_opp_fg3a and sum(last10_opp_fg3a) > 0 else 0
        team_info['season_avg_opp_fg3_pct_home'] = round((sum(home_opp_fg3m) / sum(home_opp_fg3a) * 100), 1) if home_opp_fg3a and sum(home_opp_fg3a) > 0 else 0
        team_info['season_avg_opp_fg3_pct_away'] = round((sum(away_opp_fg3m) / sum(away_opp_fg3a) * 100), 1) if away_opp_fg3a and sum(away_opp_fg3a) > 0 else 0
        team_info['last10_avg_opp_fg3_pct_home'] = round((sum(last10_home_opp_fg3m) / sum(last10_home_opp_fg3a) * 100), 1) if last10_home_opp_fg3a and sum(last10_home_opp_fg3a) > 0 else 0
        team_info['last10_avg_opp_fg3_pct_away'] = round((sum(last10_away_opp_fg3m) / sum(last10_away_opp_fg3a) * 100), 1) if last10_away_opp_fg3a and sum(last10_away_opp_fg3a) > 0 else 0

        # Defensive field aliases
        team_info['overall_avg_opp_fg3m'] = team_info['season_avg_opp_fg3m']
        team_info['overall_avg_opp_fg3_pct'] = team_info['season_avg_opp_fg3_pct']

        # Step 3: Aggregate games by 3PT defense tier and location
        # Initialize buckets: {tier: {home: [3pt_pts], away: [3pt_pts]}}
        buckets = {
            tier: {'home': [], 'away': []}
            for tier in get_all_3pt_defense_tiers()
        }

        for game in game_logs:
            three_pt_def_rank = game['opp_fg3_pct_rank']
            tier = get_3pt_defense_tier(three_pt_def_rank)

            # Skip games where opponent 3PT defense tier can't be determined
            if tier is None:
                logger.debug(f"Skipping game with missing opponent opp_fg3_pct_rank: {three_pt_def_rank}")
                continue

            location = 'home' if game['is_home'] == 1 else 'away'
            three_pt_pts = game['fg3m'] * 3  # Convert 3PM to points
            buckets[tier][location].append(three_pt_pts)

        # Step 4: Calculate averages and build response structure
        splits = {}
        for tier in get_all_3pt_defense_tiers():
            home_games = buckets[tier]['home']
            away_games = buckets[tier]['away']

            splits[tier] = {
                'home_three_pt_ppg': round(sum(home_games) / len(home_games), 1) if home_games else None,
                'home_games': len(home_games),
                'away_three_pt_ppg': round(sum(away_games) / len(away_games), 1) if away_games else None,
                'away_games': len(away_games)
            }

        team_info['splits'] = splits
        conn.close()

        logger.info(f"Generated 3PT scoring splits for team {team_id} ({team_info['team_abbreviation']}) - {season}")
        return team_info

    except Exception as e:
        logger.error(f"Error generating 3PT scoring splits for team {team_id}: {e}")
        conn.close()
        return None
