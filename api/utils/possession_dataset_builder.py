"""
Possession Dataset Builder Module

Transforms team_game_logs into possession-focused analysis dataset for pattern discovery.

Date Range: Oct 21, 2025 - Jan 1, 2026 (season-aware)
Output: ~40 columns per team-game with opportunity edge, PPP, conversion scores

Key Metrics:
- Opportunity Edge: (-TO) + OREB + (0.44*FTA) - measures extra possession opportunities
- PPP (Points Per Possession): points / possessions - direct scoring efficiency
- Conversion Score: Weighted blend of TO%, OREB%, FTr normalized to 0-100
- Empty Possessions: Possessions without points scored
"""

import sqlite3
import pandas as pd
from typing import Dict, Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Import existing utilities
try:
    from api.utils.db_config import get_db_path
    from api.utils.empty_possessions_calculator import (
        calculate_possessions,
        safe_divide,
        normalize_to_pct,
        normalize_oreb_pct,
        normalize_ftr,
        calculate_team_conversion_score
    )
except ImportError:
    from db_config import get_db_path
    from empty_possessions_calculator import (
        calculate_possessions,
        safe_divide,
        normalize_to_pct,
        normalize_oreb_pct,
        normalize_ftr,
        calculate_team_conversion_score
    )

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_season_dates(season: str, start_date: str, end_date: str) -> tuple:
    """
    Parse and validate season-aware dates.

    Season spans calendar years (e.g., '2025-26' means Oct 2025 - Jun 2026).

    Args:
        season: Season string (e.g., '2025-26')
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        Tuple of (start_year, start_month, start_day, end_year, end_month, end_day)

    Example:
        For season '2025-26' with Oct 21 - Jan 1:
        - Oct 21 is in 2025 (first year of season)
        - Jan 1 is in 2026 (second year of season)
    """
    # Extract season years
    season_parts = season.split('-')
    first_year = int('20' + season_parts[0]) if len(season_parts[0]) == 2 else int(season_parts[0])
    second_year = int('20' + season_parts[1]) if len(season_parts[1]) == 2 else int(season_parts[1])

    # Parse start date
    start_parts = start_date.split('-')
    start_month = int(start_parts[1])
    start_day = int(start_parts[2])

    # Parse end date
    end_parts = end_date.split('-')
    end_month = int(end_parts[1])
    end_day = int(end_parts[2])

    # Determine year based on month (Oct-Dec = first year, Jan-Sep = second year)
    start_year = first_year if start_month >= 10 else second_year
    end_year = first_year if end_month >= 10 else second_year

    logger.info(f"[possession_dataset_builder] Season {season}: {start_year}-{start_month:02d}-{start_day:02d} to {end_year}-{end_month:02d}-{end_day:02d}")

    return (start_year, start_month, start_day, end_year, end_month, end_day)


def build_possession_dataset(
    season: str = '2025-26',
    start_date: str = '2024-10-21',  # Will be converted to 2025-10-21 for '2025-26' season
    end_date: str = '2026-01-01',
    output_format: str = 'dataframe'
) -> Union[pd.DataFrame, str]:
    """
    Build possession-focused analysis dataset from team_game_logs.

    CRITICAL: Date range is season-aware. For season '2025-26':
    - Oct 21 means Oct 21, 2025 (first year of season)
    - Jan 1 means Jan 1, 2026 (second year of season)

    Args:
        season: Season string (e.g., '2025-26')
        start_date: Start date (YYYY-MM-DD format, year will be adjusted based on season)
        end_date: End date (YYYY-MM-DD format, year will be adjusted based on season)
        output_format: 'dataframe', 'csv', or 'json'

    Returns:
        DataFrame with ~40 columns per team-game:

        Identifiers:
        - game_id, team_id, opponent_id, game_date, is_home, win_loss

        Raw Stats:
        - FGA, FGM, FTA, FTM, OREB, DREB, TO, points, assists

        Possessions:
        - possessions (FGA + 0.44*FTA - OREB + TO)
        - opp_possessions

        Opportunity Metrics:
        - opportunity_edge: (-TO) + OREB + (0.44*FTA)
        - opp_opportunity_edge
        - opportunity_diff: team_edge - opp_edge

        Efficiency Metrics:
        - ppp: points / possessions (direct scoring efficiency)
        - empty_possessions: possessions with no points scored
        - empty_rate: empty_possessions / possessions
        - conversion_score: Weighted TO%/OREB%/FTr blend (0-100)

        Core Levers (as percentages):
        - TO_pct: (TO / possessions) * 100
        - OREB_pct: (OREB / (OREB + opp_DREB)) * 100
        - FTr: (FTA / FGA) * 100

        Game Context:
        - pace: (possessions + opp_possessions) / 2
        - off_rating: (points / possessions) * 100
        - def_rating: (opp_points / opp_possessions) * 100

        Opponent Context:
        - opp_TO_pct, opp_OREB_pct, opp_FTr, opp_pace

        Outcome:
        - plus_minus, game_win (boolean)
    """
    try:
        # Parse season-aware dates
        start_year, start_month, start_day, end_year, end_month, end_day = _parse_season_dates(
            season, start_date, end_date
        )

        # Build season-aware date strings
        season_start_date = f"{start_year}-{start_month:02d}-{start_day:02d}"
        season_end_date = f"{end_year}-{end_month:02d}-{end_day:02d}"

        logger.info(f"[possession_dataset_builder] Building dataset for {season_start_date} to {season_end_date}")

        conn = _get_db_connection()

        # Query team_game_logs with date filter
        query = """
            SELECT
                game_id,
                team_id,
                opponent_team_id as opponent_id,
                game_date,
                matchup,
                win_loss,
                team_pts as points,
                fga,
                fgm,
                fta,
                ftm,
                offensive_rebounds as oreb,
                defensive_rebounds as dreb,
                turnovers as tov,
                assists,
                (team_pts - opp_pts) as plus_minus,
                opp_pts as opp_points,
                opp_fga,
                opp_fta,
                opp_offensive_rebounds as opp_oreb,
                opp_defensive_rebounds as opp_dreb,
                opp_turnovers as opp_tov,
                possessions,
                opp_possessions,
                pace,
                off_rating,
                def_rating,
                opp_pace
            FROM team_game_logs
            WHERE season = ?
                AND game_date >= ?
                AND game_date <= ?
                AND game_type IN ('Regular Season', 'NBA Cup')
            ORDER BY game_date ASC, game_id ASC
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(season, season_start_date, season_end_date)
        )

        conn.close()

        if df.empty:
            logger.warning(f"[possession_dataset_builder] No games found for {season} between {season_start_date} and {season_end_date}")
            return df if output_format == 'dataframe' else None

        logger.info(f"[possession_dataset_builder] Loaded {len(df)} team-game records ({len(df)//2} games)")

        # Determine home/away
        df['is_home'] = df['matchup'].str.contains('vs.').fillna(False).astype(int)

        # Calculate possessions (using existing formula)
        df['possessions'] = df.apply(
            lambda row: calculate_possessions(
                row['fga'], row['fta'], row['oreb'], row['tov']
            ),
            axis=1
        )

        df['opp_possessions'] = df.apply(
            lambda row: calculate_possessions(
                row['opp_fga'], row['opp_fta'], row['opp_oreb'], row['opp_tov']
            ),
            axis=1
        )

        # Calculate opportunity edge (CRITICAL FIX #2)
        # opportunity_edge = (-TO) + OREB + (0.44*FTA)
        df['opportunity_edge'] = (-df['tov']) + df['oreb'] + (0.44 * df['fta'])
        df['opp_opportunity_edge'] = (-df['opp_tov']) + df['opp_oreb'] + (0.44 * df['opp_fta'])
        df['opportunity_diff'] = df['opportunity_edge'] - df['opp_opportunity_edge']

        # Calculate core levers (as percentages)
        df['TO_pct'] = df.apply(
            lambda row: (safe_divide(row['tov'], row['possessions'], decimals=6) * 100) if row['possessions'] else None,
            axis=1
        )

        df['OREB_pct'] = df.apply(
            lambda row: (safe_divide(row['oreb'], row['oreb'] + row['opp_dreb'], decimals=6) * 100)
                if (row['oreb'] + row['opp_dreb']) > 0 else None,
            axis=1
        )

        df['FTr'] = df.apply(
            lambda row: (safe_divide(row['fta'], row['fga'], decimals=6) * 100) if row['fga'] > 0 else None,
            axis=1
        )

        # Calculate opponent levers
        df['opp_TO_pct'] = df.apply(
            lambda row: (safe_divide(row['opp_tov'], row['opp_possessions'], decimals=6) * 100) if row['opp_possessions'] else None,
            axis=1
        )

        df['opp_OREB_pct'] = df.apply(
            lambda row: (safe_divide(row['opp_oreb'], row['opp_oreb'] + row['dreb'], decimals=6) * 100)
                if (row['opp_oreb'] + row['dreb']) > 0 else None,
            axis=1
        )

        df['opp_FTr'] = df.apply(
            lambda row: (safe_divide(row['opp_fta'], row['opp_fga'], decimals=6) * 100) if row['opp_fga'] > 0 else None,
            axis=1
        )

        # Calculate PPP (CRITICAL FIX #3 - separate from conversion_score)
        df['ppp'] = df.apply(
            lambda row: safe_divide(row['points'], row['possessions'], decimals=3) if row['possessions'] else None,
            axis=1
        )

        df['opp_ppp'] = df.apply(
            lambda row: safe_divide(row['opp_points'], row['opp_possessions'], decimals=3) if row['opp_possessions'] else None,
            axis=1
        )

        # Calculate empty possessions
        # Simplified: possessions where team scored 0 points (game-level approximation)
        # Note: True empty possession calculation requires play-by-play data
        df['empty_rate'] = df.apply(
            lambda row: safe_divide(
                row['possessions'] - (row['points'] / 1.08),  # Rough approximation
                row['possessions'],
                decimals=3
            ) if row['possessions'] else None,
            axis=1
        )

        # Calculate conversion score (CRITICAL FIX #3 - keep separate from PPP)
        df['conversion_score'] = df.apply(
            lambda row: calculate_team_conversion_score(
                normalize_to_pct(row['TO_pct']),
                normalize_oreb_pct(row['OREB_pct']),
                normalize_ftr(row['FTr'])
            ) if all([row['TO_pct'], row['OREB_pct'], row['FTr']]) else None,
            axis=1
        )

        # Calculate game context
        df['pace'] = (df['possessions'] + df['opp_possessions']) / 2

        df['off_rating'] = df.apply(
            lambda row: (safe_divide(row['points'], row['possessions'], decimals=3) * 100) if row['possessions'] else None,
            axis=1
        )

        df['def_rating'] = df.apply(
            lambda row: (safe_divide(row['opp_points'], row['opp_possessions'], decimals=3) * 100) if row['opp_possessions'] else None,
            axis=1
        )

        # Calculate game outcome
        df['game_win'] = (df['plus_minus'] > 0).astype(int)

        # Round numeric columns for readability
        numeric_cols = [
            'possessions', 'opp_possessions', 'opportunity_edge', 'opp_opportunity_edge',
            'opportunity_diff', 'TO_pct', 'OREB_pct', 'FTr', 'opp_TO_pct', 'opp_OREB_pct',
            'opp_FTr', 'ppp', 'opp_ppp', 'empty_rate', 'conversion_score',
            'pace', 'off_rating', 'def_rating'
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].round(2)

        logger.info(f"[possession_dataset_builder] Dataset built successfully: {len(df)} rows, {len(df.columns)} columns")

        # Output format
        if output_format == 'dataframe':
            return df
        elif output_format == 'csv':
            output_path = '/Users/malcolmlittle/NBA OVER UNDER SW/analysis/outputs/findings/possession_dataset.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"[possession_dataset_builder] CSV saved to {output_path}")
            return output_path
        elif output_format == 'json':
            output_path = '/Users/malcolmlittle/NBA OVER UNDER SW/analysis/outputs/findings/possession_dataset.json'
            df.to_json(output_path, orient='records', indent=2)
            logger.info(f"[possession_dataset_builder] JSON saved to {output_path}")
            return output_path
        else:
            logger.warning(f"[possession_dataset_builder] Unknown output format: {output_format}, returning dataframe")
            return df

    except Exception as e:
        logger.error(f"[possession_dataset_builder] Error building dataset: {e}")
        import traceback
        traceback.print_exc()
        return None
