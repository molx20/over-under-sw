"""
Archetype Games Query Module

Fetches games where a team played with a specific archetype (season or last10)
"""

import sqlite3
from typing import Dict, List, Optional
from .db_queries import _get_db_connection


def get_team_archetype_games(
    team_id: int,
    archetype_type: str,  # 'offensive' or 'defensive'
    archetype_id: str,    # e.g., 'perimeter_spacing_offense'
    window: str,          # 'season' or 'last10'
    season: str = '2025-26'
) -> List[Dict]:
    """
    Get all games where a team played with a specific archetype.

    Strategy:
    - For 'season': Get all games in season (archetype applies to full season)
    - For 'last10': Get the most recent 10 games

    Returns list of games with full box score stats.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get team abbreviation
    cursor.execute("SELECT team_abbreviation FROM nba_teams WHERE team_id = ?", (team_id,))
    team_result = cursor.fetchone()
    if not team_result:
        conn.close()
        return []

    team_abbr = team_result[0]

    # Query game logs for this team
    if window == 'season':
        # Get all games for the season
        query = """
            SELECT
                game_id,
                game_date,
                matchup,
                win_loss as wl,
                team_pts,
                opp_pts,
                fgm, fga, fg3m, fg3a,
                ftm, fta,
                rebounds as reb,
                assists as ast,
                turnovers as tov,
                pace,
                opponent_abbr as opp_abbr,
                points_in_paint as pitp
            FROM team_game_logs
            WHERE team_id IN (SELECT team_id FROM nba_teams WHERE team_abbreviation = ? LIMIT 1)
            AND season = ?
            ORDER BY game_date DESC
            LIMIT 82
        """
        cursor.execute(query, (team_abbr, season))
    else:  # last10
        # Get most recent 10 games
        query = """
            SELECT
                game_id,
                game_date,
                matchup,
                win_loss as wl,
                team_pts,
                opp_pts,
                fgm, fga, fg3m, fg3a,
                ftm, fta,
                rebounds as reb,
                assists as ast,
                turnovers as tov,
                pace,
                opponent_abbr as opp_abbr,
                points_in_paint as pitp
            FROM team_game_logs
            WHERE team_id IN (SELECT team_id FROM nba_teams WHERE team_abbreviation = ? LIMIT 1)
            AND season = ?
            ORDER BY game_date DESC
            LIMIT 10
        """
        cursor.execute(query, (team_abbr, season))

    games = []
    for row in cursor.fetchall():
        game_id, game_date, matchup, wl, team_pts, opp_pts, \
        fgm, fga, fg3m, fg3a, ftm, fta, reb, ast, tov, pace, opp_abbr, pitp = row

        # Calculate eFG%
        efg_pct = ((fgm + 0.5 * fg3m) / fga * 100) if fga > 0 else 0

        # Calculate FT Rate
        ft_rate = (fta / fga * 100) if fga > 0 else 0

        # Calculate FT points and paint points
        ft_points = ftm or 0
        paint_points = pitp or 0

        # Get opponent ranks (if available)
        opponent_data = get_opponent_ranks(cursor, opp_abbr, season)

        games.append({
            'game_id': game_id,
            'game_date': game_date,
            'matchup': matchup,
            'wl': wl,
            'team_pts': team_pts or 0,
            'opp_pts': opp_pts or 0,
            'total': (team_pts or 0) + (opp_pts or 0),
            'pace': pace or 0,
            'fgm': fgm or 0,
            'fga': fga or 0,
            'fg3m': fg3m or 0,
            'fg3a': fg3a or 0,
            'ftm': ftm or 0,
            'fta': fta or 0,
            'efg_pct': round(efg_pct, 1),
            'ft_rate': round(ft_rate, 1),
            'ft_points': ft_points,
            'paint_points': paint_points,
            'reb': reb or 0,
            'ast': ast or 0,
            'tov': tov or 0,
            'opponent': opponent_data,
            'opp_abbr': opp_abbr,
            # For BoxScoreModal compatibility
            'three_pt': {
                'made': fg3m or 0,
                'attempted': fg3a or 0,
                'pct': round((fg3m / fg3a * 100) if fg3a and fg3a > 0 else 0, 1),
                'points': (fg3m or 0) * 3
            }
        })

    conn.close()
    return games


def get_opponent_ranks(cursor, opp_abbr: str, season: str) -> Dict:
    """
    Get opponent's offensive and defensive ranks.
    """
    query = """
        SELECT
            tss.off_rtg_rank,
            tss.def_rtg_rank
        FROM team_season_stats tss
        JOIN nba_teams nt ON tss.team_id = nt.team_id
        WHERE nt.team_abbreviation = ?
        AND tss.season = ?
        AND tss.split_type = 'overall'
    """
    cursor.execute(query, (opp_abbr, season))
    result = cursor.fetchone()

    if not result:
        return {
            'tricode': opp_abbr,
            'off_rtg_rank': None,
            'def_rtg_rank': None,
            'strength': 'unknown'
        }

    off_rank, def_rank = result

    # Determine strength tier based on defensive rank
    if def_rank and def_rank <= 10:
        strength = 'top'
    elif def_rank and def_rank <= 20:
        strength = 'mid'
    elif def_rank:
        strength = 'bottom'
    else:
        strength = 'unknown'

    return {
        'tricode': opp_abbr,
        'off_rtg_rank': off_rank,
        'def_rtg_rank': def_rank,
        'strength': strength
    }


def get_archetype_aggregated_stats(games: List[Dict], archetype_type: str) -> Dict:
    """
    Calculate aggregated stats from a list of games.
    Returns defensive or offensive stats based on archetype type.
    """
    if not games:
        return {}

    stats = {
        'game_count': len(games),
        'avg_team_pts': 0,
        'avg_opp_pts': 0,
        'avg_total': 0,
        'avg_pace': 0,
        'avg_efg': 0,
        'avg_ft_rate': 0,
        'avg_ft_points': 0,
        'avg_paint_points': 0,
        'avg_3pm': 0,
        'avg_3pa': 0,
        'avg_ast': 0,
        'avg_tov': 0,
        'wins': 0
    }

    for game in games:
        stats['avg_team_pts'] += game['team_pts']
        stats['avg_opp_pts'] += game['opp_pts']
        stats['avg_total'] += game['total']
        stats['avg_pace'] += game.get('pace', 0)
        stats['avg_efg'] += game.get('efg_pct', 0)
        stats['avg_ft_rate'] += game.get('ft_rate', 0)
        stats['avg_ft_points'] += game.get('ft_points', 0)
        stats['avg_paint_points'] += game.get('paint_points', 0)
        stats['avg_3pm'] += game.get('fg3m', 0)
        stats['avg_3pa'] += game.get('fg3a', 0)
        stats['avg_ast'] += game.get('ast', 0)
        stats['avg_tov'] += game.get('tov', 0)
        if game.get('wl') == 'W':
            stats['wins'] += 1

    count = len(games)
    for key in stats:
        if key not in ['game_count', 'wins']:
            stats[key] = round(stats[key] / count, 1)

    stats['win_pct'] = round(stats['wins'] / count * 100, 1)

    return stats
