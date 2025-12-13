"""
Similar Opponent Box Scores Module

Retrieves actual box scores from games where a team played opponents
similar to their current matchup opponent. Uses Team Similarity Engine
to identify similar teams and fetch historical performance data.

Usage:
    from api.utils.similar_opponent_boxscores import get_similar_opponent_boxscores

    data = get_similar_opponent_boxscores(
        subject_team_id=1610612760,  # OKC
        archetype_team_id=1610612756,  # PHX
        season='2025-26',
        top_n_similar=3
    )
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple


def get_nba_db_connection():
    """Connect to NBA data database"""
    db_path = os.path.join(os.path.dirname(__file__), '../data/nba_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_similarity_db_connection():
    """Connect to Team Similarity database"""
    db_path = os.path.join(os.path.dirname(__file__), '../data/team_similarity.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_cluster_glossary_name(cluster_id: int, cluster_name: str) -> Tuple[str, str]:
    """
    Map database cluster names to glossary names with descriptions.

    Args:
        cluster_id: Cluster ID (1-6)
        cluster_name: Database cluster name

    Returns:
        Tuple of (glossary_name, description)
    """
    glossary = {
        1: (
            "Pace Pushers",
            "Teams that create more possessions per game with transition emphasis."
        ),
        2: (
            "Paint Pressure Teams",
            "High paint points, high FT rate, bully-ball or slash-heavy offenses."
        ),
        3: (
            "Three-Point Hunters",
            "High 3PA rate teams (40%+). Stretch the floor, heavy perimeter creation."
        ),
        4: (
            "Slow Grind Defensive Teams",
            "Halfcourt, low-pace teams that control tempo and protect the paint."
        ),
        5: (
            "Balanced Ball-Movement Teams",
            "High assist % teams with evenly distributed shot profiles."
        ),
        6: (
            "ISO-Heavy Teams",
            "Low assist % teams with high usage concentrated in one or two stars."
        )
    }

    return glossary.get(cluster_id, (cluster_name, ""))


def get_team_season_averages(cursor, team_id: int, season: str) -> Dict:
    """
    Calculate team's full season averages for comparison.

    Args:
        cursor: Database cursor
        team_id: Team ID
        season: Season string (e.g., '2025-26')

    Returns:
        Dict with season averages
    """
    cursor.execute("""
        SELECT
            AVG(team_pts) as avg_pts_scored,
            AVG(opp_pts) as avg_pts_allowed,
            AVG(team_pts + opp_pts) as avg_total,
            AVG(pace) as avg_pace,
            AVG(fg3a) as avg_three_pa,
            SUM(fg3m) * 100.0 / NULLIF(SUM(fg3a), 0) as avg_three_pct,
            AVG(points_in_paint) as avg_paint_pts,
            AVG(turnovers) as avg_turnovers,
            AVG(assists) as avg_assists,
            AVG(offensive_rebounds) as avg_oreb,
            AVG(defensive_rebounds) as avg_dreb,
            AVG(rebounds) as avg_reb,
            AVG(fast_break_points) as avg_fastbreak,
            AVG(second_chance_points) as avg_second_chance
        FROM team_game_logs
        WHERE team_id = ? AND season = ? AND team_pts IS NOT NULL
            AND game_date >= '2025-10-21'
    """, (team_id, season))

    row = cursor.fetchone()

    if not row:
        return {}

    return {
        'avg_pts_scored': round(row['avg_pts_scored'], 1) if row['avg_pts_scored'] else None,
        'avg_pts_allowed': round(row['avg_pts_allowed'], 1) if row['avg_pts_allowed'] else None,
        'avg_total': round(row['avg_total'], 1) if row['avg_total'] else None,
        'avg_pace': round(row['avg_pace'], 1) if row['avg_pace'] else None,
        'avg_three_pa': round(row['avg_three_pa'], 1) if row['avg_three_pa'] else None,
        'avg_three_pct': round(row['avg_three_pct'], 1) if row['avg_three_pct'] else None,
        'avg_paint_pts': round(row['avg_paint_pts'], 1) if row['avg_paint_pts'] else None,
        'avg_turnovers': round(row['avg_turnovers'], 1) if row['avg_turnovers'] else None,
        'avg_assists': round(row['avg_assists'], 1) if row['avg_assists'] else None,
        'avg_oreb': round(row['avg_oreb'], 1) if row['avg_oreb'] else None,
        'avg_dreb': round(row['avg_dreb'], 1) if row['avg_dreb'] else None,
        'avg_reb': round(row['avg_reb'], 1) if row['avg_reb'] else None,
        'avg_fastbreak': round(row['avg_fastbreak'], 1) if row['avg_fastbreak'] else None,
        'avg_second_chance': round(row['avg_second_chance'], 1) if row['avg_second_chance'] else None,
    }


def get_similar_opponent_boxscores(
    subject_team_id: int,
    archetype_team_id: int,
    season: str = '2025-26',
    top_n_similar: int = 3
) -> Dict:
    """
    Get box scores from games where subject team played teams similar to archetype team.

    Example:
        If subject_team = OKC and archetype_team = PHX,
        returns OKC's games vs teams similar to PHX (e.g., LAC, SAS, MIL)

    Args:
        subject_team_id: The team whose games we're analyzing (e.g., OKC)
        archetype_team_id: The opponent whose similar teams we're finding (e.g., PHX)
        season: NBA season (e.g., '2025-26')
        top_n_similar: Number of similar teams to consider (default: 3)

    Returns:
        Dictionary with structure:
        {
            'subject_team_id': int,
            'subject_team_name': str,
            'archetype_team_id': int,
            'archetype_team_name': str,
            'cluster_id': int,
            'cluster_name': str,
            'cluster_description': str,
            'similar_teams': List[Dict],
            'sample': {
                'games_played': int,
                'record': str,
                'summary': Dict[str, float],
                'games': List[Dict]
            }
        }
    """

    # Connect to databases
    nba_conn = get_nba_db_connection()
    sim_conn = get_similarity_db_connection()

    nba_cursor = nba_conn.cursor()
    sim_cursor = sim_conn.cursor()

    # Initialize response structure
    response = {
        'subject_team_id': subject_team_id,
        'subject_team_name': None,
        'archetype_team_id': archetype_team_id,
        'archetype_team_name': None,
        'cluster_id': None,
        'cluster_name': None,
        'cluster_description': None,
        'similar_teams': [],
        'sample': {
            'games_played': 0,
            'record': '0-0',
            'summary': {
                'avg_pts_scored': None,
                'avg_pts_allowed': None,
                'avg_total': None,
                'avg_pace': None,
                'avg_three_pa': None,
                'avg_three_pct': None,
                'avg_paint_pts': None,
                'avg_turnovers': None,
                'avg_assists': None,
                'avg_oreb': None,
                'avg_dreb': None,
                'avg_reb': None,
                'avg_fastbreak': None,
                'avg_second_chance': None
            },
            'games': []
        }
    }

    try:
        # Step 1: Get team names
        nba_cursor.execute("SELECT team_id, full_name, team_abbreviation FROM nba_teams WHERE team_id = ?", (subject_team_id,))
        subject_team_data = nba_cursor.fetchone()

        nba_cursor.execute("SELECT team_id, full_name, team_abbreviation FROM nba_teams WHERE team_id = ?", (archetype_team_id,))
        archetype_team_data = nba_cursor.fetchone()

        if not subject_team_data or not archetype_team_data:
            return response

        response['subject_team_name'] = subject_team_data['full_name']
        response['subject_team_abbr'] = subject_team_data['team_abbreviation']
        response['archetype_team_name'] = archetype_team_data['full_name']
        response['archetype_team_abbr'] = archetype_team_data['team_abbreviation']

        # Step 2: Get archetype team's cluster assignment
        sim_cursor.execute("""
            SELECT tca.cluster_id, tsc.cluster_name, tsc.cluster_description
            FROM team_cluster_assignments tca
            LEFT JOIN team_similarity_clusters tsc
                ON tca.cluster_id = tsc.cluster_id AND tca.season = tsc.season
            WHERE tca.team_id = ? AND tca.season = ?
        """, (archetype_team_id, season))

        cluster_data = sim_cursor.fetchone()

        if cluster_data:
            cluster_id = cluster_data['cluster_id']
            cluster_name = cluster_data['cluster_name']
            glossary_name, glossary_desc = get_cluster_glossary_name(cluster_id, cluster_name)

            response['cluster_id'] = cluster_id
            response['cluster_name'] = glossary_name
            response['cluster_description'] = glossary_desc

        # Step 3: Get top N similar teams to archetype
        # Note: Need to join with nba_data.db for team names
        # For now, we'll get IDs and fetch names separately
        sim_cursor.execute("""
            SELECT
                tss.similar_team_id,
                tss.similarity_score
            FROM team_similarity_scores tss
            WHERE tss.team_id = ? AND tss.season = ?
            ORDER BY tss.rank ASC
            LIMIT ?
        """, (archetype_team_id, season, top_n_similar))

        similar_teams_rows = sim_cursor.fetchall()

        if not similar_teams_rows:
            return response

        # Build similar teams list and extract IDs
        similar_team_ids = []
        for row in similar_teams_rows:
            similar_team_ids.append(row['similar_team_id'])

            # Fetch team name from nba_data.db
            nba_cursor.execute("SELECT full_name, team_abbreviation FROM nba_teams WHERE team_id = ?", (row['similar_team_id'],))
            team_data = nba_cursor.fetchone()

            response['similar_teams'].append({
                'team_id': row['similar_team_id'],
                'team_name': team_data['full_name'] if team_data else 'Unknown',
                'team_abbr': team_data['team_abbreviation'] if team_data else 'UNK',
                'similarity_score': round(row['similarity_score'], 1) if row['similarity_score'] else None
            })

        if not similar_team_ids:
            return response

        # Step 4: Find games where subject team played any of those similar teams
        # Query team_game_logs directly (not todays_games which only has upcoming games)
        placeholders = ','.join('?' * len(similar_team_ids))

        query = f"""
            SELECT
                tgl.game_id,
                tgl.game_date,
                tgl.team_id as subject_team_id,
                tgl.opponent_team_id,
                t_opp.full_name as opponent_name,
                t_opp.team_abbreviation as opponent_abbr,
                tgl.team_pts as pts_scored,
                tgl.opp_pts as pts_allowed,
                tgl.fg3a as three_pa,
                tgl.fg3m as three_pm,
                tgl.fg3_pct as three_pct,
                tgl.points_in_paint as paint_pts,
                tgl.turnovers,
                tgl.assists,
                tgl.offensive_rebounds as oreb,
                tgl.defensive_rebounds as dreb,
                tgl.rebounds as reb,
                tgl.fast_break_points as fastbreak,
                tgl.second_chance_points as second_chance,
                tgl.pace,
                tgl.win_loss as result
            FROM team_game_logs tgl
            JOIN nba_teams t_opp
                ON t_opp.team_id = tgl.opponent_team_id
            WHERE tgl.season = ?
                AND tgl.team_id = ?
                AND tgl.opponent_team_id IN ({placeholders})
                AND tgl.team_pts IS NOT NULL
                AND tgl.game_date >= '2025-10-21'
            ORDER BY tgl.game_date DESC
        """

        params = [season, subject_team_id] + similar_team_ids
        nba_cursor.execute(query, params)

        games_rows = nba_cursor.fetchall()

        if not games_rows:
            return response

        # Step 5: Process games and compute averages
        games_list = []
        wins = 0
        losses = 0

        # Accumulators for averages
        total_pts_scored = 0
        total_pts_allowed = 0
        total_pace = 0
        total_three_pa = 0
        total_three_pm = 0
        total_paint_pts = 0
        total_turnovers = 0
        total_assists = 0
        total_oreb = 0
        total_dreb = 0
        total_reb = 0
        total_fastbreak = 0
        total_second_chance = 0

        games_with_pace = 0
        games_with_3pt = 0

        for row in games_rows:
            game_data = {
                'game_id': row['game_id'],
                'date': row['game_date'],
                'opponent_id': row['opponent_team_id'],
                'opponent_name': row['opponent_name'],
                'opponent_abbr': row['opponent_abbr'],
                'result': row['result'],
                'pts_scored': row['pts_scored'],
                'pts_allowed': row['pts_allowed'],
                'total': row['pts_scored'] + row['pts_allowed'] if row['pts_scored'] and row['pts_allowed'] else None,
                'pace': round(row['pace'], 1) if row['pace'] else None,
                'three_pa': row['three_pa'],
                'three_pm': row['three_pm'],
                'three_pct': round(row['three_pct'], 1) if row['three_pct'] else None,
                'paint_pts': row['paint_pts'],
                'turnovers': row['turnovers'],
                'assists': row['assists'],
                'oreb': row['oreb'],
                'dreb': row['dreb'],
                'reb': row['reb'],
                'fastbreak': row['fastbreak'],
                'second_chance': row['second_chance']
            }

            games_list.append(game_data)

            # Track wins/losses
            if row['result'] == 'W':
                wins += 1
            else:
                losses += 1

            # Accumulate for averages
            if row['pts_scored']:
                total_pts_scored += row['pts_scored']
            if row['pts_allowed']:
                total_pts_allowed += row['pts_allowed']
            if row['pace']:
                total_pace += row['pace']
                games_with_pace += 1
            if row['three_pa']:
                total_three_pa += row['three_pa']
            if row['three_pm']:
                total_three_pm += row['three_pm']
            if row['three_pa'] and row['three_pa'] > 0:
                games_with_3pt += 1
            if row['paint_pts']:
                total_paint_pts += row['paint_pts']
            if row['turnovers']:
                total_turnovers += row['turnovers']
            if row['assists']:
                total_assists += row['assists']
            if row['oreb']:
                total_oreb += row['oreb']
            if row['dreb']:
                total_dreb += row['dreb']
            if row['reb']:
                total_reb += row['reb']
            if row['fastbreak']:
                total_fastbreak += row['fastbreak']
            if row['second_chance']:
                total_second_chance += row['second_chance']

        games_played = len(games_rows)

        # Calculate averages
        response['sample']['games_played'] = games_played
        response['sample']['record'] = f"{wins}-{losses}"
        response['sample']['games'] = games_list

        if games_played > 0:
            response['sample']['summary']['avg_pts_scored'] = round(total_pts_scored / games_played, 1)
            response['sample']['summary']['avg_pts_allowed'] = round(total_pts_allowed / games_played, 1)
            response['sample']['summary']['avg_total'] = round((total_pts_scored + total_pts_allowed) / games_played, 1)

            if games_with_pace > 0:
                response['sample']['summary']['avg_pace'] = round(total_pace / games_with_pace, 1)

            response['sample']['summary']['avg_three_pa'] = round(total_three_pa / games_played, 1)

            if games_with_3pt > 0 and total_three_pa > 0:
                response['sample']['summary']['avg_three_pct'] = round((total_three_pm / total_three_pa) * 100, 1)

            response['sample']['summary']['avg_paint_pts'] = round(total_paint_pts / games_played, 1)
            response['sample']['summary']['avg_turnovers'] = round(total_turnovers / games_played, 1)
            response['sample']['summary']['avg_assists'] = round(total_assists / games_played, 1)
            response['sample']['summary']['avg_oreb'] = round(total_oreb / games_played, 1)
            response['sample']['summary']['avg_dreb'] = round(total_dreb / games_played, 1)
            response['sample']['summary']['avg_reb'] = round(total_reb / games_played, 1)
            response['sample']['summary']['avg_fastbreak'] = round(total_fastbreak / games_played, 1)
            response['sample']['summary']['avg_second_chance'] = round(total_second_chance / games_played, 1)

        # Step 6: Add season averages for comparison
        try:
            season_avg_data = get_team_season_averages(nba_cursor, subject_team_id, season)
            response['season_avg'] = season_avg_data
            print(f"[SimilarOpponentBoxScores] Season avg for team {subject_team_id}: {len(season_avg_data)} stats")
        except Exception as e:
            print(f"[SimilarOpponentBoxScores] Error getting season avg: {e}")
            response['season_avg'] = {}

        return response

    except Exception as e:
        print(f"[SimilarOpponentBoxScores] Error: {e}")
        import traceback
        traceback.print_exc()
        return response

    finally:
        nba_conn.close()
        sim_conn.close()


if __name__ == '__main__':
    # Test with OKC vs PHX
    print("Testing Similar Opponent Box Scores")
    print("=" * 60)

    # OKC = 1610612760, PHX = 1610612756
    okc_id = 1610612760
    phx_id = 1610612756

    print("\n1. OKC vs teams similar to PHX:")
    result = get_similar_opponent_boxscores(okc_id, phx_id, '2025-26', top_n_similar=3)

    print(f"   Subject: {result['subject_team_name']}")
    print(f"   Archetype: {result['archetype_team_name']}")
    print(f"   Cluster: {result['cluster_name']}")
    print(f"   Similar teams: {[t['team_abbr'] for t in result['similar_teams']]}")
    print(f"   Games played: {result['sample']['games_played']}")
    print(f"   Record: {result['sample']['record']}")

    if result['sample']['games_played'] > 0:
        summary = result['sample']['summary']
        print(f"   Avg Scored: {summary['avg_pts_scored']}")
        print(f"   Avg Allowed: {summary['avg_pts_allowed']}")
        print(f"   Avg Total: {summary['avg_total']}")
        print(f"   Avg Pace: {summary['avg_pace']}")

    print("\n" + "=" * 60)
