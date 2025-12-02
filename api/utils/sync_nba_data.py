"""
NBA Data Synchronization Module

⚠️  WARNING: This is the ONLY module allowed to call nba_api.
⚠️  DO NOT import nba_api in request handlers.
⚠️  For request-time data access, use db_queries.py.

This module handles all background data syncing from NBA API to SQLite.
It should be called by:
1. External cron job (cron-job.org)
2. Manual admin endpoint (with secret token auth)
3. Deployment/startup script (optional one-time sync)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import sqlite3
import time

# THIS IS THE ONLY MODULE ALLOWED TO IMPORT nba_api
from nba_api.stats.endpoints import (
    teamdashboardbygeneralsplits,
    teamgamelogs,
)
from nba_api.stats.static import teams
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import centralized database configuration
try:
    from api.utils.db_config import get_db_path
    from api.utils.sync_lock import sync_lock, SyncLockError
except ImportError:
    from db_config import get_db_path
    from sync_lock import sync_lock, SyncLockError

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')

# NBA CDN endpoint for games
NBA_CDN_SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

# Rate limiting
MIN_REQUEST_INTERVAL = 0.6  # 600ms between requests (100 req/min max)
_last_request_time = 0

# ============================================================================
# RATE LIMITING & ERROR HANDLING
# ============================================================================

def _rate_limit():
    """Enforce rate limit between nba_api calls"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        sleep_time = MIN_REQUEST_INTERVAL - elapsed
        logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)
    _last_request_time = time.time()


def _safe_api_call(func, *args, max_retries=3, **kwargs):
    """
    Wrapper for safe nba_api calls with retries

    Args:
        func: API function to call
        *args: Positional arguments
        max_retries: Maximum retry attempts
        **kwargs: Keyword arguments

    Returns:
        API response or None on failure
    """
    for attempt in range(max_retries):
        try:
            _rate_limit()
            result = func(*args, **kwargs)
            logger.debug(f"API call succeeded: {func.__name__ if hasattr(func, '__name__') else 'unknown'}")
            return result
        except Exception as e:
            logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                backoff = (attempt + 1) * 2  # 2s, 4s, 6s
                time.sleep(backoff)
            else:
                logger.error(f"API call failed after {max_retries} attempts")
                return None

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory and proper timeout/WAL mode"""
    conn = sqlite3.connect(
        NBA_DATA_DB_PATH,
        timeout=30.0,  # Wait up to 30 seconds for lock
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency (allows simultaneous reads/writes)
    conn.execute("PRAGMA journal_mode=WAL")

    # Set busy timeout at the connection level as well
    conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds in milliseconds

    return conn


def _log_sync_start(sync_type: str, season: Optional[str] = None,
                   triggered_by: str = 'manual') -> int:
    """
    Log sync operation start

    Returns:
        sync_id for tracking this operation
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute('''
                    INSERT INTO data_sync_log (sync_type, season, status, started_at, triggered_by)
                    VALUES (?, ?, 'started', ?, ?)
                ''', (sync_type, season, datetime.now(timezone.utc).isoformat(), triggered_by))
                sync_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Started sync: type={sync_type}, id={sync_id}")
                return sync_id

            except sqlite3.Error as db_error:
                conn.rollback()
                if attempt < max_retries - 1:
                    logger.warning(f"Database error logging sync start (attempt {attempt + 1}/{max_retries}): {db_error}")
                    time.sleep(1)
                else:
                    logger.error(f"Failed to log sync start after {max_retries} attempts: {db_error}")
                    raise
            finally:
                conn.close()

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error logging sync start (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(1)
            else:
                logger.error(f"Failed to log sync start after {max_retries} attempts")
                raise


def _log_sync_complete(sync_id: int, records_synced: int,
                      error_message: Optional[str] = None):
    """Log sync operation completion"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()

            try:
                # Get start time to calculate duration
                cursor.execute('SELECT started_at FROM data_sync_log WHERE id = ?', (sync_id,))
                row = cursor.fetchone()
                start_time = datetime.fromisoformat(row['started_at'])
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()

                status = 'success' if error_message is None else 'failed'
                cursor.execute('''
                    UPDATE data_sync_log
                    SET status = ?, records_synced = ?, error_message = ?,
                        completed_at = ?, duration_seconds = ?
                    WHERE id = ?
                ''', (status, records_synced, error_message,
                      datetime.now(timezone.utc).isoformat(), duration, sync_id))

                conn.commit()
                logger.info(f"Completed sync: id={sync_id}, status={status}, records={records_synced}, duration={duration:.1f}s")
                break  # Success, exit retry loop

            except sqlite3.Error as db_error:
                conn.rollback()
                if attempt < max_retries - 1:
                    logger.warning(f"Database error logging sync completion (attempt {attempt + 1}/{max_retries}): {db_error}")
                    time.sleep(1)  # Wait before retry
                else:
                    logger.error(f"Failed to log sync completion after {max_retries} attempts: {db_error}")
            finally:
                conn.close()

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Error logging sync completion (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(1)
            else:
                logger.error(f"Failed to log sync completion after {max_retries} attempts: {e}")

# ============================================================================
# SYNC FUNCTIONS (Called by cron or admin endpoint)
# ============================================================================

def sync_teams(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """
    Sync NBA teams data

    Returns:
        (records_synced, error_message)
    """
    try:
        with sync_lock('teams', timeout=5.0, wait=True):
            return _sync_teams_impl(season)
    except SyncLockError as e:
        error_msg = f"Sync already in progress: {str(e)}"
        logger.warning(error_msg)
        return 0, error_msg


def _sync_teams_impl(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """Internal implementation of sync_teams (wrapped by sync_lock)"""
    sync_id = _log_sync_start('teams', season)

    try:
        # Get teams from nba_api static endpoint (no rate limiting needed)
        all_teams = teams.get_teams()

        if not all_teams:
            raise Exception("Failed to fetch teams from nba_api")

        conn = _get_db_connection()
        cursor = conn.cursor()

        # Upsert teams
        synced_at = datetime.now(timezone.utc).isoformat()
        for team in all_teams:
            cursor.execute('''
                INSERT OR REPLACE INTO nba_teams (
                    team_id, team_abbreviation, full_name, city, state,
                    year_founded, last_updated, season
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                team['id'], team['abbreviation'], team['full_name'],
                team.get('city', ''), team.get('state', ''),
                team.get('year_founded'), synced_at, season
            ))

        conn.commit()
        conn.close()

        _log_sync_complete(sync_id, len(all_teams))
        logger.info(f"Synced {len(all_teams)} teams")
        return len(all_teams), None

    except Exception as e:
        error_msg = f"Teams sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(error_msg)
        return 0, error_msg


def sync_season_stats(season: str = '2025-26',
                     team_ids: Optional[List[int]] = None) -> Tuple[int, Optional[str]]:
    """
    Sync team season statistics with home/away splits and rankings

    Args:
        season: Season string (e.g., '2024-25')
        team_ids: Optional list of specific team IDs to sync (None = all teams)

    Returns:
        (records_synced, error_message)
    """
    try:
        with sync_lock('season_stats', timeout=10.0, wait=True):
            return _sync_season_stats_impl(season, team_ids)
    except SyncLockError as e:
        error_msg = f"Sync already in progress: {str(e)}"
        logger.warning(error_msg)
        return 0, error_msg


def _sync_season_stats_impl(season: str = '2025-26',
                            team_ids: Optional[List[int]] = None) -> Tuple[int, Optional[str]]:
    """Internal implementation of sync_season_stats (wrapped by sync_lock)"""
    sync_id = _log_sync_start('season_stats', season)

    try:
        # Get all teams if not specified
        if team_ids is None:
            all_teams = teams.get_teams()
            team_ids = [t['id'] for t in all_teams]

        conn = _get_db_connection()
        cursor = conn.cursor()
        synced_at = datetime.now(timezone.utc).isoformat()

        records_synced = 0
        stats_data = []  # Collect for ranking computation

        # Fetch stats for each team
        for team_id in team_ids:
            logger.info(f"Fetching stats for team {team_id}")

            # Get traditional stats with splits
            stats_endpoint = _safe_api_call(
                teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits,
                team_id=team_id,
                season=season,
                per_mode_detailed='PerGame',
                measure_type_detailed_defense='Base'
            )

            if not stats_endpoint:
                logger.warning(f"Skipping team {team_id}: failed to fetch stats")
                continue

            # Get all dataframes
            # Index 0: Overall (GROUP_VALUE = season year)
            # Index 1: Home/Road splits (GROUP_VALUE = 'Home'/'Road')
            all_dfs = stats_endpoint.get_data_frames()
            overall_df = all_dfs[0]
            splits_df = all_dfs[1] if len(all_dfs) > 1 else None

            # Get advanced stats
            advanced_endpoint = _safe_api_call(
                teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits,
                team_id=team_id,
                season=season,
                measure_type_detailed_defense='Advanced'
            )

            advanced_dfs = advanced_endpoint.get_data_frames() if advanced_endpoint else None
            advanced_overall_df = advanced_dfs[0] if advanced_dfs and len(advanced_dfs) > 0 else None
            advanced_splits_df = advanced_dfs[1] if advanced_dfs and len(advanced_dfs) > 1 else None

            # Get opponent stats
            opponent_endpoint = _safe_api_call(
                teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits,
                team_id=team_id,
                season=season,
                measure_type_detailed_defense='Opponent'
            )

            opponent_dfs = opponent_endpoint.get_data_frames() if opponent_endpoint else None
            opponent_overall_df = opponent_dfs[0] if opponent_dfs and len(opponent_dfs) > 0 else None
            opponent_splits_df = opponent_dfs[1] if opponent_dfs and len(opponent_dfs) > 1 else None

            # Process each split
            splits_to_process = [
                ('overall', overall_df, season, advanced_overall_df, opponent_overall_df),
                ('home', splits_df, 'Home', advanced_splits_df, opponent_splits_df),
                ('away', splits_df, 'Road', advanced_splits_df, opponent_splits_df)
            ]

            for db_split_type, source_df, group_value, adv_df, opp_df in splits_to_process:
                if source_df is None:
                    continue

                # Find the row with matching GROUP_VALUE
                split_row = source_df[source_df['GROUP_VALUE'] == group_value]
                if len(split_row) == 0:
                    continue

                split_row = split_row.iloc[0]

                # Get corresponding advanced row
                adv_row = None
                if adv_df is not None:
                    adv_split = adv_df[adv_df['GROUP_VALUE'] == group_value]
                    if len(adv_split) > 0:
                        adv_row = adv_split.iloc[0]

                # Get corresponding opponent row
                opp_row = None
                opp_ppg = 0
                if opp_df is not None:
                    opp_split = opp_df[opp_df['GROUP_VALUE'] == group_value]
                    if len(opp_split) > 0:
                        opp_row = opp_split.iloc[0]
                        # Opponent stats: OPP_PTS is total, need to divide by GP for per-game
                        opp_pts_total = opp_row.get('OPP_PTS', 0)
                        games_played = opp_row.get('GP', 1)  # Avoid division by zero
                        opp_ppg = opp_pts_total / games_played if games_played > 0 else 0

                # Insert into database
                # Convert pandas/numpy types to Python native types to avoid BLOB storage
                cursor.execute('''
                    INSERT OR REPLACE INTO team_season_stats (
                        team_id, season, split_type,
                        games_played, wins, losses,
                        ppg, opp_ppg, fg_pct, fg3_pct, ft_pct,
                        rebounds, assists, steals, blocks, turnovers,
                        off_rtg, def_rtg, net_rtg, pace,
                        true_shooting_pct, efg_pct,
                        synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    int(team_id), season, db_split_type,
                    int(split_row.get('GP', 0)),
                    int(split_row.get('W', 0)),
                    int(split_row.get('L', 0)),
                    float(split_row.get('PTS', 0)),
                    float(opp_ppg),
                    float(split_row.get('FG_PCT', 0)),
                    float(split_row.get('FG3_PCT', 0)),
                    float(split_row.get('FT_PCT', 0)),
                    float(split_row.get('REB', 0)),
                    float(split_row.get('AST', 0)),
                    float(split_row.get('STL', 0)),
                    float(split_row.get('BLK', 0)),
                    float(split_row.get('TOV', 0)),
                    float(adv_row.get('OFF_RATING', 0) if adv_row is not None else 0),
                    float(adv_row.get('DEF_RATING', 0) if adv_row is not None else 0),
                    float(adv_row.get('NET_RATING', 0) if adv_row is not None else 0),
                    float(adv_row.get('PACE', 0) if adv_row is not None else 0),
                    float(adv_row.get('TS_PCT', 0) if adv_row is not None else 0),
                    float(adv_row.get('EFG_PCT', 0) if adv_row is not None else 0),
                    synced_at
                ))

                records_synced += 1

                # Collect overall stats for ranking
                if db_split_type == 'overall':
                    stats_data.append({
                        'team_id': team_id,
                        'ppg': split_row.get('PTS', 0),
                        'opp_ppg': opp_ppg,
                        'fg_pct': split_row.get('FG_PCT', 0),
                        'fg3_pct': split_row.get('FG3_PCT', 0),
                        'ft_pct': split_row.get('FT_PCT', 0),
                        'off_rtg': adv_row.get('OFF_RATING', 0) if adv_row is not None else 0,
                        'def_rtg': adv_row.get('DEF_RATING', 0) if adv_row is not None else 0,
                        'net_rtg': adv_row.get('NET_RATING', 0) if adv_row is not None else 0,
                        'pace': adv_row.get('PACE', 0) if adv_row is not None else 0,
                    })

        # Compute rankings for overall stats
        _compute_and_save_rankings(cursor, stats_data, season)

        # Update league averages
        _update_league_averages(cursor, stats_data, season)

        conn.commit()
        conn.close()

        _log_sync_complete(sync_id, records_synced)
        logger.info(f"Synced {records_synced} stat records for {len(team_ids)} teams")
        return records_synced, None

    except Exception as e:
        error_msg = f"Season stats sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return 0, error_msg


def sync_game_logs(season: str = '2025-26',
                   team_ids: Optional[List[int]] = None,
                   last_n_games: int = 10) -> Tuple[int, Optional[str]]:
    """
    Sync team game logs (last N games)

    Args:
        season: Season string
        team_ids: Optional list of specific team IDs (None = all teams)
        last_n_games: Number of recent games to fetch per team

    Returns:
        (records_synced, error_message)
    """
    try:
        with sync_lock('game_logs', timeout=10.0, wait=True):
            return _sync_game_logs_impl(season, team_ids, last_n_games)
    except SyncLockError as e:
        error_msg = f"Sync already in progress: {str(e)}"
        logger.warning(error_msg)
        return 0, error_msg


def _calculate_team_possessions_simple(game_data: dict) -> float:
    """
    Calculate one team's possessions using a simplified formula.
    Used for offensive/defensive rating calculations.

    Args:
        game_data: Dictionary with keys 'fga', 'fta', 'oreb', 'tov'

    Returns:
        Estimated possessions for the team
    """
    return (
        game_data['fga'] +
        (0.44 * game_data['fta']) -
        game_data['oreb'] +
        game_data['tov']
    )


def _calculate_nba_possessions(team1_data: dict, team2_data: dict) -> tuple:
    """
    Calculate possessions using NBA's official formula that accounts for
    offensive rebounds more accurately.

    This is the formula NBA uses for their official pace statistics.

    Args:
        team1_data: Dictionary with FGA, FGM, FTA, OREB, DREB, TOV for team 1
        team2_data: Dictionary with FGA, FGM, FTA, OREB, DREB, TOV for team 2

    Returns:
        Tuple of (team1_possessions, team2_possessions)
    """
    # Extract team 1 stats
    t1_fga = team1_data.get('fga', 0)
    t1_fgm = team1_data.get('fgm', 0)
    t1_fta = team1_data.get('fta', 0)
    t1_oreb = team1_data.get('oreb', 0)
    t1_dreb = team1_data.get('dreb', 0)
    t1_tov = team1_data.get('tov', 0)

    # Extract team 2 stats
    t2_fga = team2_data.get('fga', 0)
    t2_fgm = team2_data.get('fgm', 0)
    t2_fta = team2_data.get('fta', 0)
    t2_oreb = team2_data.get('oreb', 0)
    t2_dreb = team2_data.get('dreb', 0)
    t2_tov = team2_data.get('tov', 0)

    # NBA's official possession formula
    # Possessions = FGA + 0.4*FTA - 1.07*(OREB/(OREB+Opp_DREB))*(FGA-FGM) + TOV

    # Team 1 possessions
    oreb_factor_1 = 0
    if (t1_oreb + t2_dreb) > 0:
        oreb_factor_1 = t1_oreb / (t1_oreb + t2_dreb)

    poss_1 = (
        t1_fga +
        (0.4 * t1_fta) -
        (1.07 * oreb_factor_1 * (t1_fga - t1_fgm)) +
        t1_tov
    )

    # Team 2 possessions
    oreb_factor_2 = 0
    if (t2_oreb + t1_dreb) > 0:
        oreb_factor_2 = t2_oreb / (t2_oreb + t1_dreb)

    poss_2 = (
        t2_fga +
        (0.4 * t2_fta) -
        (1.07 * oreb_factor_2 * (t2_fga - t2_fgm)) +
        t2_tov
    )

    return (poss_1, poss_2)


def _calculate_game_pace(teams_data: list) -> float:
    """
    Calculate game pace from both teams' data using NBA's official formula.

    Game pace represents the number of possessions per 48 minutes,
    calculated as the average of both teams' possessions using the
    NBA's official possession formula.

    Args:
        teams_data: List of game data dictionaries (ideally 2 teams)

    Returns:
        Game pace (possessions per 48 minutes)
    """
    if len(teams_data) < 2:
        # Only one team's data available - fall back to simplified formula
        logger.warning(f"Only {len(teams_data)} team(s) available for pace calculation, using simplified formula")
        return _calculate_team_possessions_simple(teams_data[0])

    # Use NBA's official possession formula
    poss1, poss2 = _calculate_nba_possessions(teams_data[0], teams_data[1])

    # Game pace = average of both teams' possessions
    # Both teams should have similar possessions; averaging accounts for small differences
    game_pace = (poss1 + poss2) / 2

    return game_pace


def _sync_game_logs_impl(season: str = '2025-26',
                         team_ids: Optional[List[int]] = None,
                         last_n_games: int = 10) -> Tuple[int, Optional[str]]:
    """Internal implementation of sync_game_logs (wrapped by sync_lock)"""
    sync_id = _log_sync_start('game_logs', season)

    try:
        if team_ids is None:
            all_teams = teams.get_teams()
            team_ids = [t['id'] for t in all_teams]

        conn = _get_db_connection()
        cursor = conn.cursor()
        synced_at = datetime.now(timezone.utc).isoformat()

        records_synced = 0

        # PHASE 1: Collect all game data for all teams first
        # This allows us to calculate game pace using both teams' data
        game_data_by_id = {}  # game_id -> list of team data dicts

        for team_id in team_ids:
            logger.info(f"Fetching game logs for team {team_id}")

            # Use teamgamelogs endpoint with last_n_games parameter
            gamelogs = _safe_api_call(
                teamgamelogs.TeamGameLogs,
                team_id_nullable=team_id,
                season_nullable=season,
                season_type_nullable='Regular Season',
                last_n_games_nullable=last_n_games
            )

            if not gamelogs:
                logger.warning(f"Skipping team {team_id}: failed to fetch game logs")
                continue

            games_df = gamelogs.get_data_frames()[0]

            for _, game in games_df.iterrows():
                game_id = str(game.get('GAME_ID'))

                # Parse matchup to determine home/away and opponent
                matchup = game.get('MATCHUP', '')
                is_home = ' vs. ' in matchup
                if ' vs. ' in matchup:
                    opponent_abbr = matchup.split(' vs. ')[1]
                elif ' @ ' in matchup:
                    opponent_abbr = matchup.split(' @ ')[1]
                else:
                    opponent_abbr = None

                # Get opponent team_id
                opponent_team_id = None
                if opponent_abbr:
                    cursor.execute(
                        'SELECT team_id FROM nba_teams WHERE team_abbreviation = ?',
                        (opponent_abbr,)
                    )
                    opp_row = cursor.fetchone()
                    if opp_row:
                        opponent_team_id = opp_row['team_id']

                # Calculate stats from available data
                team_pts = float(game.get('PTS', 0))
                plus_minus = float(game.get('PLUS_MINUS', 0))
                opp_pts = team_pts - plus_minus

                # Store game data temporarily for pace calculation
                # Calculate DREB from total rebounds - offensive rebounds
                total_reb = int(game.get('REB', 0))
                oreb = float(game.get('OREB', 0))
                dreb = total_reb - oreb

                game_info = {
                    'team_id': int(team_id),
                    'game_date': str(game.get('GAME_DATE')),
                    'matchup': matchup,
                    'is_home': is_home,
                    'opponent_team_id': opponent_team_id,
                    'opponent_abbr': opponent_abbr,
                    'team_pts': team_pts,
                    'opp_pts': opp_pts,
                    'win_loss': str(game.get('WL', '')),
                    'fga': float(game.get('FGA', 0)),
                    'fgm': float(game.get('FGM', 0)),  # Field goals made
                    'fta': float(game.get('FTA', 0)),
                    'oreb': oreb,
                    'dreb': dreb,  # Defensive rebounds
                    'tov': float(game.get('TOV', 0)),
                    'fg_pct': float(game.get('FG_PCT', 0)),
                    'fg3_pct': float(game.get('FG3_PCT', 0)),
                    'ft_pct': float(game.get('FT_PCT', 0)),
                    'rebounds': total_reb,
                    'assists': int(game.get('AST', 0)),
                    'turnovers': int(game.get('TOV', 0)),
                }

                if game_id not in game_data_by_id:
                    game_data_by_id[game_id] = []
                game_data_by_id[game_id].append(game_info)

        # PHASE 2: Calculate game pace and insert records
        logger.info(f"Processing {len(game_data_by_id)} unique games with game pace calculation")

        for game_id, teams_data in game_data_by_id.items():
            # Calculate game pace once per game using both teams' data
            game_pace = _calculate_game_pace(teams_data)

            # Verify teams_data structure
            team_ids_in_game = [td['team_id'] for td in teams_data]
            if len(team_ids_in_game) != len(set(team_ids_in_game)):
                logger.warning(f"Game {game_id}: Duplicate team IDs detected! {team_ids_in_game}")

            # Insert game logs for each team with the same game pace
            for game_data in teams_data:
                team_id = game_data['team_id']
                team_pts = game_data['team_pts']
                opp_pts = game_data['opp_pts']

                # Calculate team-specific possessions for ratings using simplified formula
                team_poss = _calculate_team_possessions_simple(game_data)

                # Calculate ratings (per 100 possessions) using team possessions
                off_rating = (team_pts / team_poss * 100) if team_poss > 0 else 0
                def_rating = (opp_pts / team_poss * 100) if team_poss > 0 else 0

                # Insert game log with game pace (not team possessions)
                cursor.execute('''
                    INSERT OR REPLACE INTO team_game_logs (
                        game_id, team_id, game_date, season,
                        matchup, is_home, opponent_team_id, opponent_abbr,
                        team_pts, opp_pts, win_loss,
                        off_rating, def_rating, pace,
                        fg_pct, fg3_pct, ft_pct,
                        rebounds, assists, turnovers,
                        synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    int(team_id),
                    game_data['game_date'],
                    season,
                    game_data['matchup'],
                    1 if game_data['is_home'] else 0,
                    int(game_data['opponent_team_id']) if game_data['opponent_team_id'] else None,
                    game_data['opponent_abbr'],
                    int(team_pts),
                    int(opp_pts),
                    game_data['win_loss'],
                    float(off_rating),
                    float(def_rating),
                    float(game_pace),  # Game pace (same for both teams)
                    game_data['fg_pct'],
                    game_data['fg3_pct'],
                    game_data['ft_pct'],
                    game_data['rebounds'],
                    game_data['assists'],
                    game_data['turnovers'],
                    synced_at
                ))

                records_synced += 1

        conn.commit()
        conn.close()

        _log_sync_complete(sync_id, records_synced)
        logger.info(f"Synced {records_synced} game logs")
        return records_synced, None

    except Exception as e:
        error_msg = f"Game logs sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return 0, error_msg


def sync_todays_games(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """
    Sync today's games from NBA CDN scoreboard

    Returns:
        (records_synced, error_message)
    """
    try:
        with sync_lock('todays_games', timeout=5.0, wait=True):
            return _sync_todays_games_impl(season)
    except SyncLockError as e:
        error_msg = f"Sync already in progress: {str(e)}"
        logger.warning(error_msg)
        return 0, error_msg


def _sync_todays_games_impl(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """
    Internal implementation of sync_todays_games (wrapped by sync_lock)

    Syncs today's AND tomorrow's games to handle timezone edge cases.
    """
    sync_id = _log_sync_start('todays_games', season)

    try:
        from datetime import timedelta

        # Define Eastern Time (UTC-5, fixed offset for determinism)
        et_tz = timezone(timedelta(hours=-5))

        # Calculate current times for logging
        utc_now = datetime.now(timezone.utc)
        mt_now = datetime.now(timezone(timedelta(hours=-7)))
        et_now = datetime.now(et_tz)

        # Log all timezone contexts for debugging
        logger.info(f"[SYNC] UTC now: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[SYNC] MT  now: {mt_now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[SYNC] ET  now: {et_now.strftime('%Y-%m-%d %H:%M:%S')}")

        # Fetch today's AND tomorrow's games (handles timezone edge cases)
        today_et = et_now.strftime('%Y-%m-%d')
        tomorrow_et = (et_now + timedelta(days=1)).strftime('%Y-%m-%d')

        logger.info(f"[SYNC] Syncing all games from CDN (current ET date: {today_et})")

        # Fetch from NBA CDN (more reliable than stats.nba.com)
        # Note: NBA CDN typically returns today's and some upcoming games
        response = requests.get(NBA_CDN_SCOREBOARD_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data or 'scoreboard' not in data:
            raise Exception("Invalid CDN response: missing scoreboard data")

        scoreboard = data['scoreboard']
        games = scoreboard.get('games', [])

        conn = _get_db_connection()
        cursor = conn.cursor()
        synced_at = datetime.now(timezone.utc).isoformat()

        try:
            # Clear all existing games (we'll re-sync whatever CDN returns)
            # This keeps the database fresh with only current/upcoming games
            cursor.execute('DELETE FROM todays_games')

            records_synced = 0

            for game in games:
                game_id = game.get('gameId', '')

                # Filter by season (only 2025-26 games)
                if not _is_current_season_game(game_id, season):
                    continue

                # Extract game date from gameCode (format: "YYYYMMDD/AWYHOM")
                game_code = game.get('gameCode', '')
                if '/' in game_code:
                    date_str = game_code.split('/')[0]  # Extract YYYYMMDD
                    if len(date_str) == 8:
                        game_date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        logger.warning(f"Invalid gameCode date format: {game_code}, skipping")
                        continue
                else:
                    logger.warning(f"Invalid gameCode format: {game_code}, skipping")
                    continue

                # Sync all games returned by CDN (they manage what's current/relevant)

                home_team = game.get('homeTeam', {})
                away_team = game.get('awayTeam', {})

                # Use INSERT OR REPLACE to handle any duplicate key conflicts
                cursor.execute('''
                    INSERT OR REPLACE INTO todays_games (
                        game_id, game_date, season,
                        home_team_id, home_team_name, home_team_score,
                        away_team_id, away_team_name, away_team_score,
                        game_status_text, game_status_code, game_time_utc,
                        synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    game_date,
                    season,
                    home_team.get('teamId'),
                    home_team.get('teamTricode', 'UNK'),
                    home_team.get('score', 0),
                    away_team.get('teamId'),
                    away_team.get('teamTricode', 'UNK'),
                    away_team.get('score', 0),
                    game.get('gameStatusText', ''),
                    game.get('gameStatus', 1),
                    game.get('gameTimeUTC', ''),
                    synced_at
                ))

                records_synced += 1

            conn.commit()
        except sqlite3.Error as db_error:
            conn.rollback()
            logger.error(f"Database error during todays_games sync: {db_error}")
            raise
        finally:
            conn.close()

        _log_sync_complete(sync_id, records_synced)
        logger.info(f"[SYNC] Saved {records_synced} games from CDN into SQLite")
        return records_synced, None

    except Exception as e:
        error_msg = f"Today's games sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return 0, error_msg


def sync_team_profiles(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """
    Sync team prediction profiles (compute metrics, classify, map to weights)

    Args:
        season: Season string

    Returns:
        (records_synced, error_message)
    """
    try:
        with sync_lock('team_profiles', timeout=10.0, wait=True):
            return _sync_team_profiles_impl(season)
    except SyncLockError as e:
        error_msg = f"Sync already in progress: {str(e)}"
        logger.warning(error_msg)
        return 0, error_msg


def _sync_team_profiles_impl(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """Internal implementation of sync_team_profiles (wrapped by sync_lock)"""
    sync_id = _log_sync_start('team_profiles', season)

    try:
        from api.utils.team_profile_classifier import compute_league_references, create_team_profile
        from api.utils.db_queries import upsert_team_profile

        conn = _get_db_connection()
        cursor = conn.cursor()

        # Step 1: Compute league references
        logger.info(f"Computing league references for {season}")
        league_refs = compute_league_references(cursor, season)

        if not league_refs:
            error_msg = "Failed to compute league references (insufficient data)"
            _log_sync_complete(sync_id, 0, error_msg)
            logger.error(error_msg)
            conn.close()
            return 0, error_msg

        # Step 2: Get all teams
        cursor.execute('SELECT team_id FROM nba_teams WHERE season = ?', (season,))
        team_ids = [row[0] for row in cursor.fetchall()]

        logger.info(f"Creating profiles for {len(team_ids)} teams")

        profiles_synced = 0

        # Step 3: Create profile for each team
        for team_id in team_ids:
            try:
                profile = create_team_profile(cursor, team_id, season, league_refs)

                if profile:
                    # Save to database using separate connection (avoid nesting issues)
                    upsert_team_profile(profile)
                    profiles_synced += 1
                else:
                    # Team doesn't have enough data yet
                    logger.info(f"Skipping profile for team {team_id} (insufficient data)")

            except Exception as e:
                logger.error(f"Error creating profile for team {team_id}: {e}")
                # Continue with other teams

        conn.close()

        _log_sync_complete(sync_id, profiles_synced)
        logger.info(f"Synced {profiles_synced} team profiles")
        return profiles_synced, None

    except Exception as e:
        error_msg = f"Team profiles sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return 0, error_msg


def sync_scoring_vs_pace(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """
    Sync team scoring vs pace splits (compute scoring averages by pace bucket)

    Args:
        season: Season string

    Returns:
        (records_synced, error_message)
    """
    try:
        with sync_lock('scoring_vs_pace', timeout=10.0, wait=True):
            return _sync_scoring_vs_pace_impl(season)
    except SyncLockError as e:
        error_msg = f"Sync already in progress: {str(e)}"
        logger.warning(error_msg)
        return 0, error_msg


def _sync_scoring_vs_pace_impl(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """Internal implementation of sync_scoring_vs_pace (wrapped by sync_lock)"""
    sync_id = _log_sync_start('scoring_vs_pace', season)

    try:
        from api.utils.db_queries import get_pace_bucket, upsert_team_scoring_vs_pace
        from api.utils.pace_constants import MIN_GAMES_PER_BUCKET
        from datetime import datetime, timezone

        conn = _get_db_connection()
        cursor = conn.cursor()

        # Get all teams
        cursor.execute('SELECT team_id FROM nba_teams WHERE season = ?', (season,))
        team_ids = [row[0] for row in cursor.fetchall()]

        logger.info(f"Computing scoring vs pace for {len(team_ids)} teams")

        records_synced = 0

        # For each team, compute scoring by pace bucket
        for team_id in team_ids:
            try:
                # Fetch all game logs with pace data
                cursor.execute('''
                    SELECT team_pts, pace
                    FROM team_game_logs
                    WHERE team_id = ? AND season = ?
                        AND team_pts IS NOT NULL
                        AND pace IS NOT NULL
                ''', (team_id, season))

                games = cursor.fetchall()

                if not games:
                    logger.info(f"Team {team_id} has no game logs with pace data, skipping")
                    continue

                # Classify games into pace buckets and calculate averages
                buckets = {'slow': [], 'normal': [], 'fast': []}

                for game in games:
                    team_pts = game[0]
                    pace = game[1]
                    bucket = get_pace_bucket(pace)
                    buckets[bucket].append(team_pts)

                # Save each bucket if it has enough games
                updated_at = datetime.now(timezone.utc).isoformat()

                for bucket_name, points_list in buckets.items():
                    if len(points_list) >= MIN_GAMES_PER_BUCKET:
                        avg_points = sum(points_list) / len(points_list)
                        games_count = len(points_list)

                        # Use separate connection for upsert (avoid nesting issues)
                        upsert_team_scoring_vs_pace(
                            team_id=team_id,
                            season=season,
                            pace_bucket=bucket_name,
                            avg_points=avg_points,
                            games=games_count,
                            updated_at=updated_at
                        )

                        records_synced += 1
                        logger.info(
                            f"Team {team_id} {bucket_name} pace: {avg_points:.1f} PPG "
                            f"({games_count} games)"
                        )
                    else:
                        logger.info(
                            f"Team {team_id} {bucket_name} pace: insufficient games "
                            f"({len(points_list)} < {MIN_GAMES_PER_BUCKET})"
                        )

            except Exception as e:
                logger.error(f"Error computing scoring vs pace for team {team_id}: {e}")
                # Continue with other teams

        conn.close()

        _log_sync_complete(sync_id, records_synced)
        logger.info(f"Synced {records_synced} scoring vs pace records")
        return records_synced, None

    except Exception as e:
        error_msg = f"Scoring vs pace sync failed: {str(e)}"
        _log_sync_complete(sync_id, 0, error_msg)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return 0, error_msg


def sync_all(season: str = '2025-26', triggered_by: str = 'manual') -> Dict:
    """
    Full data sync (teams, stats, game logs, today's games)

    This is the main entry point called by cron or admin endpoint.

    Args:
        season: Season string
        triggered_by: 'cron', 'manual', or 'startup'

    Returns:
        Dict with sync results
    """
    try:
        # Use a longer timeout for full sync (up to 5 minutes)
        with sync_lock('full', timeout=300.0, wait=False):
            return _sync_all_impl(season, triggered_by)
    except SyncLockError as e:
        logger.warning(f"Full sync blocked: {str(e)}")
        return {
            'success': False,
            'error': f'Another sync operation is already in progress: {str(e)}',
            'teams': 0,
            'season_stats': 0,
            'game_logs': 0,
            'todays_games': 0,
            'team_profiles': 0,
            'scoring_vs_pace': 0,
            'total_records': 0,
            'errors': [str(e)]
        }


def _sync_all_impl(season: str = '2025-26', triggered_by: str = 'manual') -> Dict:
    """Internal implementation of sync_all (wrapped by sync_lock)"""
    start_time = time.time()
    sync_id = _log_sync_start('full', season, triggered_by)

    results = {
        'success': True,
        'teams': 0,
        'season_stats': 0,
        'game_logs': 0,
        'todays_games': 0,
        'team_profiles': 0,
        'scoring_vs_pace': 0,
        'total_records': 0,
        'errors': []
    }

    logger.info(f"Starting full data sync for {season} (triggered by: {triggered_by})")

    # Sync teams - call internal implementation directly (we already have the lock)
    teams_count, teams_error = _sync_teams_impl(season)
    results['teams'] = teams_count
    if teams_error:
        results['errors'].append(teams_error)
        results['success'] = False

    # Sync season stats
    stats_count, stats_error = _sync_season_stats_impl(season)
    results['season_stats'] = stats_count
    if stats_error:
        results['errors'].append(stats_error)
        results['success'] = False

    # Sync game logs
    logs_count, logs_error = _sync_game_logs_impl(season, last_n_games=10)
    results['game_logs'] = logs_count
    if logs_error:
        results['errors'].append(logs_error)
        results['success'] = False

    # Sync today's games
    games_count, games_error = _sync_todays_games_impl(season)
    results['todays_games'] = games_count
    if games_error:
        results['errors'].append(games_error)
        results['success'] = False

    # Sync team profiles (after game logs so we have fresh data)
    profiles_count, profiles_error = _sync_team_profiles_impl(season)
    results['team_profiles'] = profiles_count
    if profiles_error:
        results['errors'].append(profiles_error)
        # Don't fail entire sync if profiles fail (predictions have fallback)

    # Sync scoring vs pace (after game logs so we have fresh data)
    pace_count, pace_error = _sync_scoring_vs_pace_impl(season)
    results['scoring_vs_pace'] = pace_count
    if pace_error:
        results['errors'].append(pace_error)
        # Don't fail entire sync if pace splits fail (predictions have fallback)

    # Calculate totals
    results['total_records'] = (
        results['teams'] + results['season_stats'] +
        results['game_logs'] + results['todays_games'] +
        results['team_profiles'] + results['scoring_vs_pace']
    )
    results['duration_seconds'] = time.time() - start_time

    # Log completion
    error_msg = '; '.join(results['errors']) if results['errors'] else None
    _log_sync_complete(sync_id, results['total_records'], error_msg)

    logger.info(f"Full sync completed: {results['total_records']} records in {results['duration_seconds']:.1f}s")

    return results

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _is_current_season_game(game_id: str, season: str) -> bool:
    """Check if game ID matches current season"""
    # NBA game IDs: 00[Season][GameNumber]
    # Season 2025-26 uses prefix '00225' or '0022500'
    valid_prefixes = ['001225', '0022500', '002250', '00225', '003225', '004225']
    return any(str(game_id).startswith(prefix) for prefix in valid_prefixes)


def _compute_and_save_rankings(cursor, stats_data: List[Dict], season: str):
    """Compute rankings and update database"""
    if not stats_data:
        return

    # Stats where higher is better
    stats_high = ['ppg', 'fg_pct', 'fg3_pct', 'ft_pct', 'off_rtg', 'net_rtg', 'pace']
    # Stats where lower is better
    stats_low = ['opp_ppg', 'def_rtg']

    # Rank high stats (descending)
    for stat in stats_high:
        sorted_teams = sorted(stats_data, key=lambda x: x[stat], reverse=True)
        for rank, team in enumerate(sorted_teams, start=1):
            cursor.execute(f'''
                UPDATE team_season_stats
                SET {stat}_rank = ?
                WHERE team_id = ? AND season = ? AND split_type = 'overall'
            ''', (rank, team['team_id'], season))

    # Rank low stats (ascending)
    for stat in stats_low:
        sorted_teams = sorted(stats_data, key=lambda x: x[stat])
        for rank, team in enumerate(sorted_teams, start=1):
            cursor.execute(f'''
                UPDATE team_season_stats
                SET {stat}_rank = ?
                WHERE team_id = ? AND season = ? AND split_type = 'overall'
            ''', (rank, team['team_id'], season))


def _update_league_averages(cursor, stats_data: List[Dict], season: str):
    """Calculate and save league averages"""
    if not stats_data:
        return

    n = len(stats_data)
    averages = {
        'ppg': sum(t['ppg'] for t in stats_data) / n,
        'pace': sum(t['pace'] for t in stats_data) / n,
        'off_rtg': sum(t['off_rtg'] for t in stats_data) / n,
        'def_rtg': sum(t['def_rtg'] for t in stats_data) / n,
        'fg_pct': sum(t['fg_pct'] for t in stats_data) / n,
        'fg3_pct': sum(t['fg3_pct'] for t in stats_data) / n,
        'ft_pct': sum(t['ft_pct'] for t in stats_data) / n,
    }

    cursor.execute('''
        INSERT OR REPLACE INTO league_averages (
            season, ppg, pace, off_rtg, def_rtg, fg_pct, fg3_pct, ft_pct, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        season,
        averages['ppg'],
        averages['pace'],
        averages['off_rtg'],
        averages['def_rtg'],
        averages['fg_pct'],
        averages['fg3_pct'],
        averages['ft_pct'],
        datetime.now(timezone.utc).isoformat()
    ))


def get_last_sync_status(sync_type: Optional[str] = None) -> Optional[Dict]:
    """
    Get status of last sync operation

    Args:
        sync_type: Optional filter by sync type

    Returns:
        Dict with sync status or None
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if sync_type:
        cursor.execute('''
            SELECT * FROM data_sync_log
            WHERE sync_type = ?
            ORDER BY started_at DESC
            LIMIT 1
        ''', (sync_type,))
    else:
        cursor.execute('''
            SELECT * FROM data_sync_log
            ORDER BY started_at DESC
            LIMIT 1
        ''')

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return dict(row)


if __name__ == '__main__':
    # Example usage for manual testing
    print("Starting manual sync...")
    result = sync_all(season='2025-26', triggered_by='manual')
    print(f"\nSync Results:")
    print(f"  Success: {result['success']}")
    print(f"  Teams: {result['teams']}")
    print(f"  Season Stats: {result['season_stats']}")
    print(f"  Game Logs: {result['game_logs']}")
    print(f"  Today's Games: {result['todays_games']}")
    print(f"  Total Records: {result['total_records']}")
    print(f"  Duration: {result['duration_seconds']:.1f}s")
    if result['errors']:
        print(f"  Errors: {', '.join(result['errors'])}")
