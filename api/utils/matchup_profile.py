"""
Matchup Profile Module

Classifies opponents into strength buckets and tracks team performance vs each bucket.
Uses simple 3-bucket system: Top 10, Middle 10, Bottom 10 in the league.

Bucket logic:
- Rank 1-10: 'top' (elite)
- Rank 11-20: 'mid' (average)
- Rank 21-30: 'bottom' (weak)

Tracks separate buckets for:
- Offensive strength (by OFF_RTG rank)
- Defensive strength (by DEF_RTG rank)
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import sqlite3
import os

try:
    from api.utils import team_rankings
    from api.utils.nba_data import get_all_teams
except ImportError:
    import team_rankings
    from nba_data import get_all_teams

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'predictions.db')


def classify_team_bucket(team_stats: Dict, dimension: str) -> str:
    """
    Classify a team into strength bucket based on league rank

    Args:
        team_stats: Dict from team_rankings.get_team_stats_with_ranks()
        dimension: 'off_rtg' or 'def_rtg'

    Returns:
        'top', 'mid', or 'bottom'

    Example:
        >>> stats = team_rankings.get_team_stats_with_ranks(1610612738)  # BOS
        >>> classify_team_bucket(stats, 'off_rtg')
        'top'  # BOS has rank 1 in offense
    """
    if not team_stats or 'stats' not in team_stats:
        return 'mid'  # Default to middle if no data

    rank = team_stats['stats'].get(dimension, {}).get('rank')

    if rank is None:
        return 'mid'

    if rank <= 10:
        return 'top'
    elif rank <= 20:
        return 'mid'
    else:
        return 'bottom'


def get_matchup_profile(
    team_tricode: str,
    vs_off_bucket: str,
    vs_def_bucket: str,
    season: str = '2025-26'
) -> Dict:
    """
    Get team's historical performance vs specific opponent strength buckets

    Args:
        team_tricode: Team abbreviation (e.g., 'BOS')
        vs_off_bucket: Opponent's offensive bucket ('top', 'mid', 'bottom')
        vs_def_bucket: Opponent's defensive bucket ('top', 'mid', 'bottom')
        season: Season string

    Returns:
        Dict with averages for each bucket combination:
        {
            'vs_off_top_avg_total': 225.3,
            'vs_off_mid_avg_total': 218.1,
            'vs_off_bottom_avg_total': 210.5,
            'vs_def_top_avg_total': 208.2,
            'vs_def_mid_avg_total': 220.4,
            'vs_def_bottom_avg_total': 228.7,
            'games_vs_off_top': 4,
            'games_vs_off_mid': 5,
            ...
        }

    Example:
        >>> profile = get_matchup_profile('BOS', 'top', 'mid')
        >>> profile['vs_off_top_avg_total']
        225.3  # BOS's games vs top-10 offenses average 225.3 total points
    """
    # Check cache first
    cached = _get_cached_profile(team_tricode)

    if cached and _is_cache_fresh(cached):
        return cached

    # Recompute from game history
    print(f'[matchup_profile] Computing profile for {team_tricode}')
    profile = _compute_matchup_profile_from_history(team_tricode, season)

    # Save to cache
    _save_profile_to_cache(team_tricode, profile)

    return profile


def _compute_matchup_profile_from_history(team_tricode: str, season: str) -> Dict:
    """
    Compute matchup profile from team_game_history table

    Groups games by opponent bucket and calculates averages
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query all games for this team
        cursor.execute('''
            SELECT
                opp_off_bucket,
                opp_def_bucket,
                points_scored,
                points_allowed
            FROM team_game_history
            WHERE team_tricode = ?
            ORDER BY game_date DESC
            LIMIT 50
        ''', (team_tricode,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print(f'[matchup_profile] No game history found for {team_tricode}')
            return _empty_profile()

        # Group by buckets
        buckets = {
            'off_top': [], 'off_mid': [], 'off_bottom': [],
            'def_top': [], 'def_mid': [], 'def_bottom': []
        }

        for row in rows:
            opp_off_bucket, opp_def_bucket, pts_scored, pts_allowed = row

            if opp_off_bucket:
                buckets[f'off_{opp_off_bucket}'].append({
                    'total': pts_scored + pts_allowed,
                    'scored': pts_scored,
                    'allowed': pts_allowed
                })

            if opp_def_bucket:
                buckets[f'def_{opp_def_bucket}'].append({
                    'total': pts_scored + pts_allowed,
                    'scored': pts_scored,
                    'allowed': pts_allowed
                })

        # Calculate averages
        profile = {}
        for bucket_key, games in buckets.items():
            prefix = f'vs_{bucket_key}'

            if len(games) > 0:
                profile[f'{prefix}_avg_total'] = round(sum(g['total'] for g in games) / len(games), 1)
                profile[f'{prefix}_avg_scored'] = round(sum(g['scored'] for g in games) / len(games), 1)
                profile[f'{prefix}_avg_allowed'] = round(sum(g['allowed'] for g in games) / len(games), 1)
                profile[f'games_{prefix}'] = len(games)
            else:
                profile[f'{prefix}_avg_total'] = 0.0
                profile[f'{prefix}_avg_scored'] = 0.0
                profile[f'{prefix}_avg_allowed'] = 0.0
                profile[f'games_{prefix}'] = 0

        return profile

    except sqlite3.OperationalError:
        # Table doesn't exist yet
        print(f'[matchup_profile] team_game_history table not found')
        return _empty_profile()


def _get_cached_profile(team_tricode: str) -> Optional[Dict]:
    """Get cached matchup profile from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all bucket profiles for this team
        cursor.execute('''
            SELECT vs_bucket_type, avg_total, games_count, last_updated
            FROM matchup_profile_cache
            WHERE team_tricode = ?
        ''', (team_tricode,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        # Reconstruct profile dict
        profile = {}
        for row in rows:
            bucket_type, avg_total, games_count, last_updated = row
            profile[f'{bucket_type}_avg_total'] = avg_total
            profile[f'games_{bucket_type}'] = games_count
            profile['_last_updated'] = last_updated  # Track freshness

        return profile if len(profile) > 1 else None  # Need more than just timestamp

    except sqlite3.OperationalError:
        return None


def _save_profile_to_cache(team_tricode: str, profile: Dict):
    """Save matchup profile to cache"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        # Clear existing cache for this team
        cursor.execute('DELETE FROM matchup_profile_cache WHERE team_tricode = ?', (team_tricode,))

        # Insert new cache entries
        for bucket_type in ['vs_off_top', 'vs_off_mid', 'vs_off_bottom',
                           'vs_def_top', 'vs_def_mid', 'vs_def_bottom']:
            avg_total = profile.get(f'{bucket_type}_avg_total', 0.0)
            games_count = profile.get(f'games_{bucket_type}', 0)

            cursor.execute('''
                INSERT INTO matchup_profile_cache (
                    team_tricode, vs_bucket_type,
                    avg_total, games_count, last_updated
                ) VALUES (?, ?, ?, ?, ?)
            ''', (team_tricode, bucket_type, avg_total, games_count, timestamp))

        conn.commit()
        conn.close()

    except sqlite3.OperationalError:
        # Table doesn't exist yet
        pass


def _is_cache_fresh(profile: Dict, max_age_hours: int = 24) -> bool:
    """Check if cached profile is fresh (less than 24 hours old)"""
    if '_last_updated' not in profile:
        return False

    try:
        last_updated = datetime.fromisoformat(profile['_last_updated'])
        age = datetime.now() - last_updated
        return age < timedelta(hours=max_age_hours)
    except:
        return False


def _empty_profile() -> Dict:
    """Return empty profile when no data available"""
    profile = {}
    for bucket_type in ['vs_off_top', 'vs_off_mid', 'vs_off_bottom',
                       'vs_def_top', 'vs_def_mid', 'vs_def_bottom']:
        profile[f'{bucket_type}_avg_total'] = 0.0
        profile[f'{bucket_type}_avg_scored'] = 0.0
        profile[f'{bucket_type}_avg_allowed'] = 0.0
        profile[f'games_{bucket_type}'] = 0
    return profile


def update_team_game_history_entry(
    game_id: str,
    team_tricode: str,
    opponent_tricode: str,
    stats: Dict,
    game_date: str,
    season: str = '2025-26'
):
    """
    Update team_game_history table with game results

    Called after a game finishes to record performance vs opponent bucket.

    Args:
        game_id: NBA game ID
        team_tricode: Team abbreviation
        opponent_tricode: Opponent abbreviation
        stats: Dict with points_scored, points_allowed, off_rtg, def_rtg, pace
        game_date: Game date (YYYY-MM-DD)
        season: Season string

    Example:
        >>> update_team_game_history_entry(
        ...     '0022500123', 'BOS', 'LAL',
        ...     {'points_scored': 115, 'points_allowed': 108, ...},
        ...     '2025-11-20'
        ... )
    """
    print(f'[matchup_profile] Recording game history: {team_tricode} vs {opponent_tricode}')

    # Get opponent's team ID and classify into buckets
    all_teams = get_all_teams()
    opp_team_data = next((t for t in all_teams if t['abbreviation'] == opponent_tricode), None)
    team_data = next((t for t in all_teams if t['abbreviation'] == team_tricode), None)

    if not opp_team_data or not team_data:
        print(f'[matchup_profile] WARNING: Could not find team data for {opponent_tricode} or {team_tricode}')
        return

    # Get opponent rankings and classify
    opp_stats = team_rankings.get_team_stats_with_ranks(opp_team_data['id'], season)
    opp_off_bucket = classify_team_bucket(opp_stats, 'off_rtg') if opp_stats else 'mid'
    opp_def_bucket = classify_team_bucket(opp_stats, 'def_rtg') if opp_stats else 'mid'

    # Extract opponent league ranks for last-5 opponent features
    opp_ppg_rank = None
    opp_pace_rank = None
    opp_off_rtg_rank = None
    opp_def_rtg_rank = None

    if opp_stats and 'stats' in opp_stats:
        try:
            opp_ppg_rank = opp_stats['stats']['ppg']['rank']
            opp_pace_rank = opp_stats['stats']['pace']['rank']
            opp_off_rtg_rank = opp_stats['stats']['off_rtg']['rank']
            opp_def_rtg_rank = opp_stats['stats']['def_rtg']['rank']
            print(f'[matchup_profile] Opponent {opponent_tricode} ranks: PPG={opp_ppg_rank}, Pace={opp_pace_rank}')
        except (KeyError, TypeError) as e:
            print(f'[matchup_profile] Could not extract opponent ranks: {e}')

    # Insert into database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO team_game_history (
                game_id, team_id, team_tricode,
                opponent_id, opponent_tricode,
                game_date, is_home,
                points_scored, points_allowed,
                off_rtg, def_rtg, pace,
                fg_pct, three_pct,
                opp_off_bucket, opp_def_bucket,
                opp_ppg_rank, opp_pace_rank,
                opp_off_rtg_rank, opp_def_rtg_rank,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            game_id,
            team_data['id'],
            team_tricode,
            opp_team_data['id'],
            opponent_tricode,
            game_date,
            stats.get('is_home', 1),
            stats.get('points_scored'),
            stats.get('points_allowed'),
            stats.get('off_rtg'),
            stats.get('def_rtg'),
            stats.get('pace'),
            stats.get('fg_pct'),
            stats.get('three_pct'),
            opp_off_bucket,
            opp_def_bucket,
            opp_ppg_rank,
            opp_pace_rank,
            opp_off_rtg_rank,
            opp_def_rtg_rank,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        print(f'[matchup_profile] Recorded: {team_tricode} vs {opponent_tricode} ({opp_off_bucket} off, {opp_def_bucket} def)')

        # Invalidate cache for this team
        _invalidate_cache(team_tricode)

    except sqlite3.OperationalError as e:
        print(f'[matchup_profile] Error recording game history: {e}')


def _invalidate_cache(team_tricode: str):
    """Invalidate matchup profile cache for a team"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM matchup_profile_cache WHERE team_tricode = ?', (team_tricode,))
        conn.commit()
        conn.close()
    except:
        pass
