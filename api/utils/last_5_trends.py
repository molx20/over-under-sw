"""
Last 5 Game Trends Analysis Module

Fetches a team's last 5 games, enriches with opponent profiles, analyzes trends,
and generates human-readable tags for UI display.

This module is part of the deterministic prediction system. All trend analysis
is based on hand-coded formulas with no machine learning.
"""

from typing import Dict, List, Optional
from datetime import datetime

# Import existing infrastructure
try:
    from api.utils.db_queries import get_team_last_n_games, get_team_stats_with_ranks
except ImportError:
    from db_queries import get_team_last_n_games, get_team_stats_with_ranks


def get_last_5_trends(team_id: int, team_tricode: str, season: str = '2025-26') -> Dict:
    """
    Fetch last 5 games, enrich with opponent profiles, analyze trends.

    Args:
        team_id: NBA team ID
        team_tricode: Team abbreviation (e.g., 'BOS', 'LAL')
        season: Season string (e.g., '2025-26')

    Returns:
        Dict containing:
        - games: List of enriched game records
        - averages: Last-5 averages (pace, off_rtg, def_rtg, ppg, opp_ppg)
        - season_comparison: Deltas vs season averages
        - opponent_breakdown: Analysis of opponent strength
        - trend_tags: Human-readable insights (2-4 tags)
        - data_quality: 'excellent', 'good', or 'poor'

    Example return:
        {
            'team_tricode': 'BOS',
            'games': [...],  # 5 enriched game records
            'averages': {'pace': 101.2, 'off_rtg': 116.8, ...},
            'season_comparison': {'pace_delta': +3.2, ...},
            'opponent_breakdown': {'vs_top_off': 2, ...},
            'trend_tags': ['Playing faster (+3.2 pace vs season)', ...],
            'data_quality': 'excellent'
        }
    """
    print(f'[last_5_trends] Analyzing last 5 games for {team_tricode} (team_id={team_id})')

    # Fetch last 5 games from NBA API
    try:
        games_raw = get_team_last_n_games(team_id, n=5, season=season)
    except Exception as e:
        print(f'[last_5_trends] Error fetching games: {e}')
        return _empty_trends(team_tricode)

    if not games_raw:
        print(f'[last_5_trends] No games found for {team_tricode}')
        return _empty_trends(team_tricode)

    # Get season stats for this team
    season_stats = get_team_stats_with_ranks(team_id, season)
    if not season_stats or not season_stats.get('stats'):
        print(f'[last_5_trends] No season stats found for {team_tricode}')
        return _empty_trends(team_tricode)

    # Enrich each game with opponent data
    enriched_games = []
    for game in games_raw[:5]:  # Take only first 5
        enriched_game = _enrich_game_with_opponent(game, season)
        if enriched_game:
            enriched_games.append(enriched_game)

    if not enriched_games:
        print(f'[last_5_trends] No enriched games for {team_tricode}')
        return _empty_trends(team_tricode)

    # Compute averages
    averages = _compute_averages(enriched_games)

    # Extract season stats for comparison
    season_off_rtg = season_stats['stats']['off_rtg']['value']
    season_def_rtg = season_stats['stats']['def_rtg']['value']
    season_pace = season_stats['stats']['pace']['value']
    season_ppg = season_stats['stats']['ppg']['value']

    # Build season averages dict
    season_avg = {
        'pace': round(season_pace, 1),
        'off_rtg': round(season_off_rtg, 1),
        'def_rtg': round(season_def_rtg, 1),
        'ppg': round(season_ppg, 1)
    }

    # Compute deltas (last5 - season)
    delta_vs_season = {
        'pace': round(averages['pace'] - season_pace, 1),
        'off_rtg': round(averages['off_rtg'] - season_off_rtg, 1),
        'def_rtg': round(averages['def_rtg'] - season_def_rtg, 1),
        'ppg': round(averages['ppg'] - season_ppg, 1)
    }

    # Legacy season_comparison for backward compatibility
    season_comparison = {
        'pace_delta': delta_vs_season['pace'],
        'off_rtg_delta': delta_vs_season['off_rtg'],
        'def_rtg_delta': delta_vs_season['def_rtg'],
        'ppg_delta': delta_vs_season['ppg']
    }

    # Analyze opponent strength
    opponent_breakdown = _analyze_opponents(enriched_games)

    # Generate human-readable trend tags
    trend_tags = _generate_trend_tags(season_comparison, opponent_breakdown)

    # Assess data quality
    if len(enriched_games) >= 5:
        data_quality = 'excellent'
    elif len(enriched_games) >= 3:
        data_quality = 'good'
    else:
        data_quality = 'poor'

    print(f'[last_5_trends] {team_tricode}: {len(enriched_games)} games, quality={data_quality}')
    print(f'[last_5_trends] {team_tricode}: Deltas - PACE:{delta_vs_season["pace"]:+.1f}, OFF:{delta_vs_season["off_rtg"]:+.1f}, DEF:{delta_vs_season["def_rtg"]:+.1f}')

    return {
        'team_tricode': team_tricode,
        'games': enriched_games,
        'averages': averages,
        'season_avg': season_avg,
        'delta_vs_season': delta_vs_season,
        'season_comparison': season_comparison,  # Legacy, keep for backward compat
        'opponent_breakdown': opponent_breakdown,
        'trend_tags': trend_tags,
        'data_quality': data_quality
    }


def _enrich_game_with_opponent(game: Dict, season: str) -> Optional[Dict]:
    """
    Enrich a single game record with opponent profile data.

    Args:
        game: Raw game record from NBA API
        season: Season string

    Returns:
        Enriched game dict with opponent stats/ranks, or None if enrichment fails
    """
    try:
        # Extract basic game data
        matchup = game.get('MATCHUP', '')

        # Parse opponent abbreviation from matchup string (e.g., "BOS vs. LAL" or "BOS @ LAL")
        if ' vs. ' in matchup:
            opponent_abbr = matchup.split(' vs. ')[1]
        elif ' @ ' in matchup:
            opponent_abbr = matchup.split(' @ ')[1]
        else:
            print(f'[last_5_trends] Could not parse opponent from matchup: {matchup}')
            return None

        # Get opponent's team_id
        from api.utils.db_queries import get_all_teams
        all_teams = get_all_teams()
        opponent_team = next((t for t in all_teams if t['abbreviation'] == opponent_abbr), None)

        if not opponent_team:
            print(f'[last_5_trends] Could not find opponent team: {opponent_abbr}')
            return None

        opponent_id = opponent_team['id']

        # Get opponent's season stats
        opponent_stats = get_team_stats_with_ranks(opponent_id, season)

        # Extract 3PT data for calculation
        fg3m = game.get('FG3M', 0)
        fg3a = game.get('FG3A', 0)

        # Calculate 3PT scoring object
        three_pt_points = fg3m * 3
        three_pt_pct = None
        if fg3a > 0:
            three_pt_pct = round((fg3m / fg3a) * 100, 1)

        three_pt_obj = {
            'points': three_pt_points,
            'made': fg3m,
            'attempted': fg3a,
            'percentage': three_pt_pct
        } if fg3a > 0 or fg3m > 0 else None

        # Build enriched game record with detailed box score stats
        enriched = {
            'game_id': game.get('GAME_ID'),
            'game_date': game.get('GAME_DATE'),
            'matchup': matchup,
            'team_pts': game.get('PTS', 0),
            'opp_pts': game.get('OPP_PTS', 0),
            'total': game.get('PTS', 0) + game.get('OPP_PTS', 0),
            'team_pace': game.get('PACE', 0),
            'team_off_rtg': game.get('OFF_RATING', 0),
            'team_def_rtg': game.get('DEF_RATING', 0),
            # Detailed box score stats
            'pace': game.get('PACE', 0),
            'three_pt': three_pt_obj,
            'tov': game.get('TOV', 0),
            'ast': game.get('AST', 0),
            'reb': game.get('REB', 0),
        }

        # Add opponent profile if available
        if opponent_stats and opponent_stats.get('stats'):
            stats = opponent_stats['stats']

            # Determine opponent strength tier
            off_rank = stats['off_rtg']['rank']
            def_rank = stats['def_rtg']['rank']

            # Top 10 = 'top', 11-20 = 'mid', 21-30 = 'bottom'
            if off_rank <= 10:
                off_strength = 'top'
            elif off_rank <= 20:
                off_strength = 'mid'
            else:
                off_strength = 'bottom'

            enriched['opponent'] = {
                'tricode': opponent_abbr,
                'off_rtg': stats['off_rtg']['value'],
                'off_rtg_rank': off_rank,
                'def_rtg': stats['def_rtg']['value'],
                'def_rtg_rank': def_rank,
                'pace': stats['pace']['value'],
                'pace_rank': stats['pace']['rank'],
                'strength': off_strength
            }
        else:
            # Fallback if opponent stats not available
            enriched['opponent'] = {
                'tricode': opponent_abbr,
                'off_rtg': None,
                'off_rtg_rank': None,
                'def_rtg': None,
                'def_rtg_rank': None,
                'pace': None,
                'pace_rank': None,
                'strength': 'unknown'
            }

        return enriched

    except Exception as e:
        print(f'[last_5_trends] Error enriching game: {e}')
        return None


def _compute_averages(games: List[Dict]) -> Dict:
    """
    Compute averages from enriched games.

    Args:
        games: List of enriched game records

    Returns:
        Dict with averages: pace, off_rtg, def_rtg, ppg, opp_ppg
    """
    if not games:
        return {
            'pace': 0.0,
            'off_rtg': 0.0,
            'def_rtg': 0.0,
            'ppg': 0.0,
            'opp_ppg': 0.0
        }

    # Extract valid values (filter out None/0)
    pace_vals = [g['team_pace'] for g in games if g.get('team_pace')]
    off_vals = [g['team_off_rtg'] for g in games if g.get('team_off_rtg')]
    def_vals = [g['team_def_rtg'] for g in games if g.get('team_def_rtg')]
    ppg_vals = [g['team_pts'] for g in games if g.get('team_pts')]
    opp_ppg_vals = [g['opp_pts'] for g in games if g.get('opp_pts')]

    return {
        'pace': round(_safe_avg(pace_vals), 1),
        'off_rtg': round(_safe_avg(off_vals), 1),
        'def_rtg': round(_safe_avg(def_vals), 1),
        'ppg': round(_safe_avg(ppg_vals), 1),
        'opp_ppg': round(_safe_avg(opp_ppg_vals), 1)
    }


def _analyze_opponents(games: List[Dict]) -> Dict:
    """
    Analyze the strength of opponents faced in last 5 games.

    Args:
        games: List of enriched game records

    Returns:
        Dict with opponent breakdown (vs_top_off, vs_mid_off, vs_bottom_off, avg ranks)
    """
    vs_top_off = 0
    vs_mid_off = 0
    vs_bottom_off = 0
    off_ranks = []
    def_ranks = []

    for game in games:
        opponent = game.get('opponent', {})

        # Count strength tiers
        strength = opponent.get('strength', 'unknown')
        if strength == 'top':
            vs_top_off += 1
        elif strength == 'mid':
            vs_mid_off += 1
        elif strength == 'bottom':
            vs_bottom_off += 1

        # Collect ranks
        if opponent.get('off_rtg_rank'):
            off_ranks.append(opponent['off_rtg_rank'])
        if opponent.get('def_rtg_rank'):
            def_ranks.append(opponent['def_rtg_rank'])

    return {
        'vs_top_off': vs_top_off,
        'vs_mid_off': vs_mid_off,
        'vs_bottom_off': vs_bottom_off,
        'avg_opp_off_rank': round(_safe_avg(off_ranks), 1) if off_ranks else None,
        'avg_opp_def_rank': round(_safe_avg(def_ranks), 1) if def_ranks else None
    }


def _generate_trend_tags(season_comparison: Dict, opponent_breakdown: Dict) -> List[str]:
    """
    Generate 2-4 human-readable trend tags based on deltas and opponent strength.

    Args:
        season_comparison: Dict with pace_delta, off_rtg_delta, def_rtg_delta, ppg_delta
        opponent_breakdown: Dict with opponent strength analysis

    Returns:
        List of trend tag strings (e.g., "Offense heating up (+2.1 ORTG)")
    """
    tags = []

    # Pace trends
    pace_delta = season_comparison['pace_delta']
    if abs(pace_delta) >= 2.0:
        direction = 'faster' if pace_delta > 0 else 'slower'
        tags.append(f'Playing {direction} ({pace_delta:+.1f} pace vs season)')

    # Offensive trends
    off_delta = season_comparison['off_rtg_delta']
    if off_delta >= 2.0:
        tags.append(f'Offense heating up ({off_delta:+.1f} ORTG)')
    elif off_delta <= -2.0:
        tags.append(f'Offense cooling down ({off_delta:+.1f} ORTG)')

    # Defensive trends (negative delta = improvement)
    def_delta = season_comparison['def_rtg_delta']
    if def_delta <= -2.0:
        tags.append(f'Defense improving ({def_delta:+.1f} DRTG)')
    elif def_delta >= 2.0:
        tags.append(f'Defense struggling ({def_delta:+.1f} DRTG)')

    # Opponent strength context
    avg_opp_off_rank = opponent_breakdown.get('avg_opp_off_rank')
    if avg_opp_off_rank:
        if avg_opp_off_rank <= 10:
            tags.append('Facing elite competition')
        elif avg_opp_off_rank >= 20:
            tags.append('Facing weak competition')
        else:
            tags.append('Facing average competition')

    # If no significant trends, add a neutral tag
    if not tags:
        tags.append('Playing near season averages')

    # Limit to 4 tags max
    return tags[:4]


def _safe_avg(values: List[float]) -> float:
    """
    Calculate average, filtering out None values.

    Args:
        values: List of numeric values (may contain None)

    Returns:
        Average of valid values, or 0.0 if no valid values
    """
    valid = [v for v in values if v is not None and v != 0]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def _empty_trends(team_tricode: str) -> Dict:
    """
    Return empty trends structure when no data available.

    Args:
        team_tricode: Team abbreviation

    Returns:
        Empty trends dict with all fields set to None/empty
    """
    return {
        'team_tricode': team_tricode,
        'games': [],
        'averages': {
            'pace': 0.0,
            'off_rtg': 0.0,
            'def_rtg': 0.0,
            'ppg': 0.0,
            'opp_ppg': 0.0
        },
        'season_comparison': {
            'pace_delta': 0.0,
            'off_rtg_delta': 0.0,
            'def_rtg_delta': 0.0,
            'ppg_delta': 0.0
        },
        'opponent_breakdown': {
            'vs_top_off': 0,
            'vs_mid_off': 0,
            'vs_bottom_off': 0,
            'avg_opp_off_rank': None,
            'avg_opp_def_rank': None
        },
        'trend_tags': ['No recent game data available'],
        'data_quality': 'none'
    }
