"""
Games vs Archetype Query Module

Fetches games where a team played AGAINST opponents with a specific archetype.
"""

import sqlite3
from typing import Dict, List, Optional
from .db_queries import _get_db_connection
from .archetype_classifier import assign_all_team_archetypes


def get_team_vs_archetype_games(
    team_id: int,
    archetype_type: str,  # 'offensive' or 'defensive'
    archetype_id: str,    # e.g., 'perimeter_lockdown'
    window: str,          # 'season' or 'last10'
    season: str = '2025-26'
) -> Dict:
    """
    Get all games where a team played AGAINST opponents with a specific archetype.

    Args:
        team_id: NBA team ID (the team we want to see games for)
        archetype_type: 'offensive' or 'defensive' (opponent's archetype type)
        archetype_id: archetype ID to match (opponent's archetype)
        window: 'season' or 'last10' (which opponent archetype to match)
        season: Season string

    Returns:
        {
            'team_id': int,
            'team_abbr': str,
            'archetype_type': str,
            'archetype_id': str,
            'window': str,
            'summary': {
                'games_count': int,
                'ppg': float,
                'efg': float,
                'ft_points': float,
                'paint_points': float,
                'wins': int,
                'win_pct': float
            },
            'games': [...]
        }
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Get team abbreviation
    cursor.execute("SELECT team_abbreviation FROM nba_teams WHERE team_id = ?", (team_id,))
    team_result = cursor.fetchone()
    if not team_result:
        conn.close()
        return {
            'team_id': team_id,
            'team_abbr': None,
            'archetype_type': archetype_type,
            'archetype_id': archetype_id,
            'window': window,
            'summary': {},
            'games': []
        }

    team_abbr = team_result[0]

    # Get all team archetypes for the season
    all_archetypes = assign_all_team_archetypes(season)

    # Build opponent archetype lookup map
    # opponent_archetypes[opponent_team_id] = archetype_id
    opponent_archetypes = {}
    for tid, assignment in all_archetypes.items():
        if window == 'season':
            if archetype_type == 'offensive':
                opponent_archetypes[tid] = assignment.get('season_offensive')
            else:  # defensive
                opponent_archetypes[tid] = assignment.get('season_defensive')
        else:  # last10
            if archetype_type == 'offensive':
                opponent_archetypes[tid] = assignment.get('last10_offensive')
            else:  # defensive
                opponent_archetypes[tid] = assignment.get('last10_defensive')

    # Get all games for this team (filter out games before 2025-10-21)
    query = """
        SELECT
            tgl.game_id,
            tgl.game_date,
            tgl.matchup,
            tgl.win_loss as wl,
            tgl.team_pts,
            tgl.opp_pts,
            tgl.fgm, tgl.fga, tgl.fg3m, tgl.fg3a,
            tgl.ftm, tgl.fta,
            tgl.rebounds as reb,
            tgl.assists as ast,
            tgl.turnovers as tov,
            tgl.pace,
            tgl.opponent_abbr as opp_abbr,
            tgl.points_in_paint as pitp,
            nt.team_id as opp_team_id
        FROM team_game_logs tgl
        LEFT JOIN nba_teams nt ON tgl.opponent_abbr = nt.team_abbreviation
        WHERE tgl.team_id = ?
        AND tgl.season = ?
        AND tgl.game_date >= '2025-10-21'
        ORDER BY tgl.game_date DESC
    """
    cursor.execute(query, (team_id, season))

    matching_games = []
    for row in cursor.fetchall():
        (game_id, game_date, matchup, wl, team_pts, opp_pts,
         fgm, fga, fg3m, fg3a, ftm, fta, reb, ast, tov, pace,
         opp_abbr, pitp, opp_team_id) = row

        # Check if opponent has the matching archetype
        if opp_team_id and opp_team_id in opponent_archetypes:
            opp_archetype = opponent_archetypes[opp_team_id]
            if opp_archetype == archetype_id:
                # Calculate derived stats
                efg_pct = ((fgm + 0.5 * fg3m) / fga * 100) if fga and fga > 0 else 0
                ft_points = ftm or 0
                paint_points = pitp or 0

                matching_games.append({
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
                    'ft_points': ft_points,
                    'paint_points': paint_points,
                    'reb': reb or 0,
                    'ast': ast or 0,
                    'tov': tov or 0,
                    'opponent': {
                        'tricode': opp_abbr,
                        'team_id': opp_team_id,
                        'archetype': opp_archetype
                    },
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

    # Calculate summary stats
    summary = calculate_vs_archetype_summary(matching_games)

    return {
        'team_id': team_id,
        'team_abbr': team_abbr,
        'archetype_type': archetype_type,
        'archetype_id': archetype_id,
        'window': window,
        'summary': summary,
        'games': matching_games
    }


def calculate_vs_archetype_summary(games: List[Dict]) -> Dict:
    """
    Calculate summary stats from games vs archetype.
    """
    if not games:
        return {
            'games_count': 0,
            'ppg': 0,
            'efg': 0,
            'ft_points': 0,
            'paint_points': 0,
            'ast': 0,
            'tov': 0,
            'wins': 0,
            'win_pct': 0
        }

    total_pts = 0
    total_efg = 0
    total_ft_points = 0
    total_paint_points = 0
    total_ast = 0
    total_tov = 0
    wins = 0

    for game in games:
        total_pts += game.get('team_pts', 0)
        total_efg += game.get('efg_pct', 0)
        total_ft_points += game.get('ft_points', 0)
        total_paint_points += game.get('paint_points', 0)
        total_ast += game.get('ast', 0)
        total_tov += game.get('tov', 0)
        if game.get('wl') == 'W':
            wins += 1

    count = len(games)

    return {
        'games_count': count,
        'ppg': round(total_pts / count, 1),
        'efg': round(total_efg / count, 1),
        'ft_points': round(total_ft_points / count, 1),
        'paint_points': round(total_paint_points / count, 1),
        'ast': round(total_ast / count, 1),
        'tov': round(total_tov / count, 1),
        'wins': wins,
        'win_pct': round(wins / count * 100, 1)
    }
