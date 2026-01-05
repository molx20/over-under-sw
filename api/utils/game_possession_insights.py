"""
Game Possession Insights Module

Generates game-level possession insights for the "Possession Insights" tab.
Provides 4 sections of analysis:
1. What drives this matchup (Top 3 possession drivers)
2. Spread/Margin lens (Opportunity differential percentile)
3. Total lens (Combined empty possessions)
4. Prop lanes (Rebounds/FT/Assists lanes)

Possession-only metrics. NO shooting splits, NO ORTG/DRTG labels, NO pace archetypes.
"""

import sqlite3
import pandas as pd
import json
import hashlib
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Import existing modules
try:
    from api.utils.db_config import get_db_path
    from api.utils.possession_dataset_builder import build_possession_dataset
    from api.utils.ppp_aggregator import get_team_ppp_metrics
except ImportError:
    from db_config import get_db_path
    from possession_dataset_builder import build_possession_dataset
    from ppp_aggregator import get_team_ppp_metrics

NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_game_data(row: pd.Series) -> bool:
    """
    Validate game data meets sanity checks (per-team thresholds)

    Returns True if valid, False otherwise
    """
    try:
        # Per-team validation based on real NBA data distributions
        is_valid = (
            80 <= row['points'] <= 160 and
            70 <= row['possessions'] <= 95 and  # Per-team possessions (median ~79)
            row['TO_pct'] is not None and 5 <= row['TO_pct'] <= 25 and
            row['OREB_pct'] is not None and 15 <= row['OREB_pct'] <= 40 and
            row['FTr'] is not None and 10 <= row['FTr'] <= 60  # Teams that attack rim can exceed 45%
        )

        if not is_valid:
            logger.warning(f"[game_possession_insights] Validation failed for team {row.get('team_id', 'unknown')}:")
            logger.warning(f"  Points: {row['points']} (need 80-160)")
            logger.warning(f"  Possessions: {row['possessions']} (need 70-95)")
            logger.warning(f"  TO%: {row.get('TO_pct', 'N/A')} (need 5-25)")
            logger.warning(f"  OREB%: {row.get('OREB_pct', 'N/A')} (need 15-40)")
            logger.warning(f"  FTr: {row.get('FTr', 'N/A')} (need 10-60)")

        return is_valid
    except Exception as e:
        logger.warning(f"[game_possession_insights] Validation error: {e}")
        return False


def _generate_section_1_drivers(team_row: pd.Series, opp_row: pd.Series, team_name: str, opp_name: str) -> List[str]:
    """
    Generate Section 1: What drives this matchup (Top 3 bullets)

    Uses TO%, OREB%, FTr deltas to identify possession drivers
    """
    bullets = []

    # Calculate deltas
    to_delta = team_row['TO_pct'] - opp_row['TO_pct']
    oreb_delta = team_row['OREB_pct'] - opp_row['OREB_pct']
    ftr_delta = team_row['FTr'] - opp_row['FTr']

    # Rank by absolute impact
    impacts = [
        ('TO', abs(to_delta), to_delta, 'turnover'),
        ('OREB', abs(oreb_delta), oreb_delta, 'offensive rebounding'),
        ('FTr', abs(ftr_delta), ftr_delta, 'free throw'),
    ]
    impacts.sort(key=lambda x: x[1], reverse=True)

    # Generate top 3 bullets
    for metric, abs_impact, delta, label in impacts[:3]:
        if abs_impact > 1:  # Only significant differences
            if delta > 0:
                bullets.append(f"{team_name} {label} edge (+{delta:.1f}%)")
            else:
                bullets.append(f"{opp_name} {label} edge ({delta:.1f}%)")
        else:
            bullets.append(f"Neutral {label} edge (within 1%)")

    return bullets


def _generate_section_2_spread_lens(team_row: pd.Series, historical_df: pd.DataFrame, team_name: str) -> Dict:
    """
    Generate Section 2: Spread/Margin Lens

    Shows opportunity_diff and percentile rank
    Returns label: Control (≥70%), Neutral (30-70%), Lean (<30%)
    """
    opportunity_diff = team_row['opportunity_diff']

    # Calculate percentile within historical window
    percentile = (historical_df['opportunity_diff'] < opportunity_diff).mean() * 100

    # Assign label
    if percentile >= 70:
        label = "Control"
    elif percentile >= 30:
        label = "Neutral"
    else:
        label = "Lean"

    return {
        'opportunity_diff': round(opportunity_diff, 1),
        'percentile': int(percentile),
        'label': label
    }


def _generate_section_3_total_lens(team_row: pd.Series, opp_row: pd.Series, historical_df: pd.DataFrame) -> Dict:
    """
    Generate Section 3: Total Lens

    Shows combined empty possessions and combined opportunities
    Returns label: Over-friendly (≥60%), Under-friendly (≤40%), High variance (mid)
    """
    # Estimate combined empty possessions (team + opponent)
    team_empty_pct = team_row.get('empty_rate', 0) or 0
    opp_empty_pct = opp_row.get('empty_rate', 0) or 0

    # Ensure values are valid (between 0 and 1)
    team_empty_pct = max(0, min(1, abs(team_empty_pct)))
    opp_empty_pct = max(0, min(1, abs(opp_empty_pct)))

    combined_empty_pct = (team_empty_pct + opp_empty_pct) / 2 * 100

    # Combined opportunities (total possessions)
    combined_opportunities = team_row['possessions'] + opp_row['possessions']

    # Calculate percentile of empty possession rate
    historical_empty_rates = historical_df.get('empty_rate', pd.Series([0]))
    historical_empty_rates = historical_empty_rates.apply(lambda x: max(0, min(1, abs(x if x is not None else 0)))) * 100
    historical_empty_rates = historical_empty_rates.fillna(0)
    empty_percentile = (historical_empty_rates < combined_empty_pct).mean() * 100

    # Assign label based on empty possession percentile
    if empty_percentile >= 60:
        label = "Over-friendly"  # Low empty possessions = high scoring
    elif empty_percentile <= 40:
        label = "Under-friendly"  # High empty possessions = low scoring
    else:
        label = "High variance"

    return {
        'combined_empty': round(combined_empty_pct, 1),
        'combined_opportunities': round(combined_opportunities, 1),
        'label': label
    }


def _generate_section_4_prop_lanes(team_row: pd.Series, opp_row: pd.Series, team_name: str) -> Dict:
    """
    Generate Section 4: Prop Lanes

    Returns 3 lanes: Rebounds, FT, Assists (each: Up/Neutral/Down)
    """
    # Rebounds lane: Based on OREB% + opponent DREB context
    oreb_pct = team_row['OREB_pct']
    if oreb_pct >= 28:
        rebounds_lane = "Up"
    elif oreb_pct <= 23:
        rebounds_lane = "Down"
    else:
        rebounds_lane = "Neutral"

    # FT lane: Based on FTr
    ftr = team_row['FTr']
    if ftr >= 28:
        ft_lane = "Up"
    elif ftr <= 20:
        ft_lane = "Down"
    else:
        ft_lane = "Neutral"

    # Assists lane: Based on TO% + opportunity stability
    to_pct = team_row['TO_pct']
    opportunity_diff = team_row['opportunity_diff']

    if to_pct <= 12 and abs(opportunity_diff) < 3:
        assists_lane = "Up"  # Low TOs + stable opportunities = good assist environment
    elif to_pct >= 16:
        assists_lane = "Down"  # High TOs = bad assist environment
    else:
        assists_lane = "Neutral"

    return {
        'rebounds_lane': rebounds_lane,
        'ft_lane': ft_lane,
        'assists_lane': assists_lane
    }


def _generate_ppp_metrics(team_id: int, season: str) -> Optional[Dict]:
    """
    Generate PPP metrics section for a team.

    Fetches from team_season_stats:
    - ppp_season
    - ppp_last10
    - ppp_last10_games (to show if < 10)

    Args:
        team_id: Team ID
        season: Season string (e.g., '2025-26')

    Returns:
        {
            'ppp_season': 1.12,
            'ppp_last10': 1.15,
            'ppp_last10_games': 10,
            'active_projection': 'blended'  # "60% Last10 + 40% Season"
        }
        Or None if data not available
    """
    try:
        ppp_metrics = get_team_ppp_metrics(team_id, season, split_type='overall')

        if not ppp_metrics:
            return None

        return {
            'ppp_season': ppp_metrics['ppp_season'],
            'ppp_last10': ppp_metrics['ppp_last10'],
            'ppp_last10_games': ppp_metrics['ppp_last10_games'],
            'active_projection': 'blended'  # Can be made configurable later
        }

    except Exception as e:
        logger.warning(f"[_generate_ppp_metrics] Failed to fetch PPP metrics for team {team_id}: {e}")
        return None


def generate_game_possession_insights(game_id: str, season: str = '2025-26') -> Optional[Dict]:
    """
    Generate possession insights for a specific game

    Args:
        game_id: NBA game ID
        season: Season string (default: '2025-26')

    Returns:
        Dict with insights for both teams, or None if unable to generate
    """
    try:
        logger.info(f"[game_possession_insights] Generating insights for game {game_id}")

        # Step 1: Fetch game info
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Try todays_games first
        cursor.execute('''
            SELECT game_id, game_date, home_team_id, home_team_name, away_team_id, away_team_name
            FROM todays_games
            WHERE game_id = ?
        ''', (game_id,))
        game = cursor.fetchone()
        conn.close()

        if not game:
            logger.warning(f"[game_possession_insights] Game {game_id} not found")
            return None

        game_date = game['game_date']
        home_team_id = game['home_team_id']
        away_team_id = game['away_team_id']
        home_team_name = str(game['home_team_name'])[:3].upper()  # Convert to abbreviation
        away_team_name = str(game['away_team_name'])[:3].upper()

        logger.info(f"[game_possession_insights] {away_team_name} @ {home_team_name} on {game_date}")

        # Step 2: Build historical dataset (Oct 21 - current date)
        logger.info(f"[game_possession_insights] Building historical dataset...")
        # Use game_date + 1 day to ensure we include the current game
        from datetime import datetime, timedelta
        try:
            # Handle various date formats
            if 'T' in game_date or 'Z' in game_date:
                game_datetime = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
            else:
                game_datetime = datetime.strptime(game_date, '%Y-%m-%d')
            end_date = (game_datetime + timedelta(days=1)).strftime('%Y-%m-%d')
        except Exception as e:
            logger.warning(f"[game_possession_insights] Error parsing game_date '{game_date}': {e}. Using today's date.")
            end_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')

        df = build_possession_dataset(
            season=season,
            start_date='2024-10-21',  # Will be converted to 2025-10-21
            end_date=end_date,
            output_format='dataframe'
        )

        if df is None or df.empty:
            logger.warning(f"[game_possession_insights] Failed to build dataset")
            return None

        logger.info(f"[game_possession_insights] Dataset built: {len(df)} rows")

        # Step 3: Find specific game rows
        home_row = df[(df['game_id'] == game_id) & (df['team_id'] == home_team_id)]
        away_row = df[(df['game_id'] == game_id) & (df['team_id'] == away_team_id)]

        # If game not found, use season averages for prediction
        is_projection = False
        if home_row.empty or away_row.empty:
            logger.info(f"[game_possession_insights] Game {game_id} not found - generating projection from season averages")
            is_projection = True

            # Calculate season averages for both teams
            home_season_data = df[df['team_id'] == home_team_id]
            away_season_data = df[df['team_id'] == away_team_id]

            if home_season_data.empty or away_season_data.empty:
                logger.warning(f"[game_possession_insights] No season data available for teams")
                return {
                    'error': 'no_season_data',
                    'message': 'No historical data available to generate projections.'
                }

            # Build synthetic rows from season averages
            home_row = pd.Series({
                'team_id': home_team_id,
                'game_id': game_id,
                'points': home_season_data['points'].mean(),
                'possessions': home_season_data['possessions'].mean(),
                'TO_pct': home_season_data['TO_pct'].mean(),
                'OREB_pct': home_season_data['OREB_pct'].mean(),
                'FTr': home_season_data['FTr'].mean(),
                'empty_rate': home_season_data['empty_rate'].mean(),
                'opportunity_diff': home_season_data['opportunity_diff'].mean(),
            })

            away_row = pd.Series({
                'team_id': away_team_id,
                'game_id': game_id,
                'points': away_season_data['points'].mean(),
                'possessions': away_season_data['possessions'].mean(),
                'TO_pct': away_season_data['TO_pct'].mean(),
                'OREB_pct': away_season_data['OREB_pct'].mean(),
                'FTr': away_season_data['FTr'].mean(),
                'empty_rate': away_season_data['empty_rate'].mean(),
                'opportunity_diff': away_season_data['opportunity_diff'].mean(),
            })
        else:
            home_row = home_row.iloc[0]
            away_row = away_row.iloc[0]

        # Step 4: Validate data
        if not _validate_game_data(home_row) or not _validate_game_data(away_row):
            logger.error(f"[game_possession_insights] Data validation failed for game {game_id}")
            return {
                'error': 'validation_failed',
                'message': 'Game data contains outlier metrics and cannot be analyzed.'
            }

        # Step 5: Generate 4 sections for each team
        home_insights = {
            'team_id': int(home_team_id),
            'team_name': home_team_name,
            'section_1_drivers': _generate_section_1_drivers(home_row, away_row, home_team_name, away_team_name),
            'section_2_spread': _generate_section_2_spread_lens(home_row, df, home_team_name),
            'section_3_total': _generate_section_3_total_lens(home_row, away_row, df),
            'section_4_props': _generate_section_4_prop_lanes(home_row, away_row, home_team_name),
            'ppp_metrics': _generate_ppp_metrics(home_team_id, season)
        }

        away_insights = {
            'team_id': int(away_team_id),
            'team_name': away_team_name,
            'section_1_drivers': _generate_section_1_drivers(away_row, home_row, away_team_name, home_team_name),
            'section_2_spread': _generate_section_2_spread_lens(away_row, df, away_team_name),
            'section_3_total': _generate_section_3_total_lens(away_row, home_row, df),
            'section_4_props': _generate_section_4_prop_lanes(away_row, home_row, away_team_name),
            'ppp_metrics': _generate_ppp_metrics(away_team_id, season)
        }

        # Step 6: Return structured JSON
        result = {
            'home_team': home_insights,
            'away_team': away_insights,
            'metadata': {
                'game_id': game_id,
                'game_date': game_date,
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'is_projection': is_projection
            }
        }

        log_type = "projection" if is_projection else "actual game"
        logger.info(f"[game_possession_insights] Successfully generated {log_type} insights for game {game_id}")
        return result

    except Exception as e:
        logger.error(f"[game_possession_insights] Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        return None


def _calculate_data_hash(game_id: str) -> str:
    """Calculate MD5 hash for cache invalidation"""
    hash_str = f"{game_id}_2025-26_possession_insights_v5"
    return hashlib.md5(hash_str.encode()).hexdigest()


def get_cached_insights(game_id: str) -> Optional[Dict]:
    """
    Retrieve cached insights from database

    Returns None if not found or cache is invalid
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT game_id, team_id, insights_json, data_hash, created_at
            FROM possession_insights_cache
            WHERE game_id = ?
        ''', (game_id,))

        rows = cursor.fetchall()
        conn.close()

        if not rows or len(rows) != 2:  # Should have 2 rows (one per team)
            return None

        # Check hash validity
        expected_hash = _calculate_data_hash(game_id)
        if rows[0]['data_hash'] != expected_hash:
            logger.info(f"[game_possession_insights] Cache STALE for game {game_id} (hash mismatch)")
            return None

        # Parse JSON from both rows
        home_insights = json.loads(rows[0]['insights_json'])
        away_insights = json.loads(rows[1]['insights_json'])

        # Reconstruct full payload
        result = {
            'home_team': home_insights if home_insights.get('team_id') == rows[0]['team_id'] else away_insights,
            'away_team': away_insights if away_insights.get('team_id') == rows[1]['team_id'] else home_insights,
            'metadata': {
                'game_id': game_id,
                'game_date': '',  # Not stored in cache
                'data_hash': rows[0]['data_hash'],
                'generated_at': rows[0]['created_at']
            }
        }

        logger.info(f"[game_possession_insights] Cache HIT for game {game_id}")
        return result

    except Exception as e:
        logger.error(f"[game_possession_insights] Error retrieving cache: {e}")
        return None


def save_insights_to_cache(game_id: str, insights: Dict) -> bool:
    """
    Save insights to database cache

    Returns True if successful, False otherwise
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        data_hash = _calculate_data_hash(game_id)
        game_date = insights['metadata']['game_date']

        # Save home team insights
        home = insights['home_team']
        cursor.execute('''
            INSERT OR REPLACE INTO possession_insights_cache
            (game_id, team_id, opponent_id, game_date, insights_json, data_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (game_id, home['team_id'], insights['away_team']['team_id'], game_date, json.dumps(home), data_hash))

        # Save away team insights
        away = insights['away_team']
        cursor.execute('''
            INSERT OR REPLACE INTO possession_insights_cache
            (game_id, team_id, opponent_id, game_date, insights_json, data_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (game_id, away['team_id'], home['team_id'], game_date, json.dumps(away), data_hash))

        conn.commit()
        conn.close()

        logger.info(f"[game_possession_insights] Saved to cache: game {game_id}")
        return True

    except Exception as e:
        logger.error(f"[game_possession_insights] Error saving to cache: {e}")
        return False


def get_or_generate_insights(game_id: str, season: str = '2025-26') -> Optional[Dict]:
    """
    Main orchestration function: cache-first retrieval

    Workflow:
    1. Check cache
    2. If cache miss -> generate new insights
    3. Save to cache
    4. Return insights

    Returns insights dict or None if unable to generate
    """
    # Step 1: Check cache
    cached = get_cached_insights(game_id)
    if cached:
        return cached

    # Step 2: Cache miss - generate new
    logger.info(f"[game_possession_insights] Cache MISS for game {game_id} - generating...")
    insights = generate_game_possession_insights(game_id, season)

    if not insights:
        return None

    # Step 3: Save to cache
    save_insights_to_cache(game_id, insights)

    # Step 4: Return
    return insights
