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
except ImportError:
    from db_config import get_db_path

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
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _log_sync_start(sync_type: str, season: Optional[str] = None,
                   triggered_by: str = 'manual') -> int:
    """
    Log sync operation start

    Returns:
        sync_id for tracking this operation
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO data_sync_log (sync_type, season, status, started_at, triggered_by)
        VALUES (?, ?, 'started', ?, ?)
    ''', (sync_type, season, datetime.now(timezone.utc).isoformat(), triggered_by))
    sync_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Started sync: type={sync_type}, id={sync_id}")
    return sync_id


def _log_sync_complete(sync_id: int, records_synced: int,
                      error_message: Optional[str] = None):
    """Log sync operation completion"""
    conn = _get_db_connection()
    cursor = conn.cursor()

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
    conn.close()
    logger.info(f"Completed sync: id={sync_id}, status={status}, records={records_synced}, duration={duration:.1f}s")

# ============================================================================
# SYNC FUNCTIONS (Called by cron or admin endpoint)
# ============================================================================

def sync_teams(season: str = '2025-26') -> Tuple[int, Optional[str]]:
    """
    Sync NBA teams data

    Returns:
        (records_synced, error_message)
    """
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
    sync_id = _log_sync_start('game_logs', season)

    try:
        if team_ids is None:
            all_teams = teams.get_teams()
            team_ids = [t['id'] for t in all_teams]

        conn = _get_db_connection()
        cursor = conn.cursor()
        synced_at = datetime.now(timezone.utc).isoformat()

        records_synced = 0

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

                # Insert game log
                # Convert pandas/numpy types to Python native types to avoid BLOB storage
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
                    str(game.get('GAME_ID')),
                    int(team_id),
                    str(game.get('GAME_DATE')),
                    season,
                    matchup,
                    1 if is_home else 0,
                    int(opponent_team_id) if opponent_team_id else None,
                    opponent_abbr,
                    int(game.get('PTS', 0)),
                    int(game.get('OPP_PTS', 0)),
                    str(game.get('WL', '')),
                    float(game.get('OFF_RATING', 0)),
                    float(game.get('DEF_RATING', 0)),
                    float(game.get('PACE', 0)),
                    float(game.get('FG_PCT', 0)),
                    float(game.get('FG3_PCT', 0)),
                    float(game.get('FT_PCT', 0)),
                    int(game.get('REB', 0)),
                    int(game.get('AST', 0)),
                    int(game.get('TOV', 0)),
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
    sync_id = _log_sync_start('todays_games', season)

    try:
        # Fetch from NBA CDN (more reliable than stats.nba.com)
        response = requests.get(NBA_CDN_SCOREBOARD_URL, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data or 'scoreboard' not in data:
            raise Exception("Invalid CDN response: missing scoreboard data")

        scoreboard = data['scoreboard']
        games = scoreboard.get('games', [])
        game_date = scoreboard.get('gameDate', datetime.now().strftime('%Y-%m-%d'))

        conn = _get_db_connection()
        cursor = conn.cursor()
        synced_at = datetime.now(timezone.utc).isoformat()

        # Clear today's games for this date
        cursor.execute('DELETE FROM todays_games WHERE game_date = ?', (game_date,))

        records_synced = 0

        for game in games:
            game_id = game.get('gameId', '')

            # Filter by season (only 2025-26 games)
            if not _is_current_season_game(game_id, season):
                continue

            home_team = game.get('homeTeam', {})
            away_team = game.get('awayTeam', {})

            cursor.execute('''
                INSERT INTO todays_games (
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
        conn.close()

        _log_sync_complete(sync_id, records_synced)
        logger.info(f"Synced {records_synced} games for {game_date}")
        return records_synced, None

    except Exception as e:
        error_msg = f"Today's games sync failed: {str(e)}"
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
    start_time = time.time()
    sync_id = _log_sync_start('full', season, triggered_by)

    results = {
        'success': True,
        'teams': 0,
        'season_stats': 0,
        'game_logs': 0,
        'todays_games': 0,
        'total_records': 0,
        'errors': []
    }

    logger.info(f"Starting full data sync for {season} (triggered by: {triggered_by})")

    # Sync teams
    teams_count, teams_error = sync_teams(season)
    results['teams'] = teams_count
    if teams_error:
        results['errors'].append(teams_error)
        results['success'] = False

    # Sync season stats
    stats_count, stats_error = sync_season_stats(season)
    results['season_stats'] = stats_count
    if stats_error:
        results['errors'].append(stats_error)
        results['success'] = False

    # Sync game logs
    logs_count, logs_error = sync_game_logs(season, last_n_games=10)
    results['game_logs'] = logs_count
    if logs_error:
        results['errors'].append(logs_error)
        results['success'] = False

    # Sync today's games
    games_count, games_error = sync_todays_games(season)
    results['todays_games'] = games_count
    if games_error:
        results['errors'].append(games_error)
        results['success'] = False

    # Calculate totals
    results['total_records'] = (
        results['teams'] + results['season_stats'] +
        results['game_logs'] + results['todays_games']
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
