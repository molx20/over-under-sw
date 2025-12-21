"""
Game Classification Utility

Classifies NBA games based on game_id prefix to filter out
non-regular-season games (Summer League, Preseason, Playoffs, etc.)
while keeping Regular Season and all NBA Cup games.

Game ID Prefix Reference (from NBA API):
- 002: Regular Season (includes NBA Cup games)
- 001: Preseason
- 003: All-Star
- 004/005: Playoffs/Play-In
- 132/152: Summer League
"""
import logging
from typing import Dict, Literal

logger = logging.getLogger(__name__)

GameType = Literal['regular_season', 'nba_cup', 'preseason', 'playoffs', 'all_star', 'summer_league', 'unknown']


def classify_game(game_id: str, game_date: str = None) -> Dict:
    """
    Classify a game based on its game_id and optional date.

    Args:
        game_id: NBA game ID (e.g., "0022501209")
        game_date: Optional game date for additional context (ISO format)

    Returns:
        {
            'game_type': str,  # 'regular_season', 'preseason', 'playoffs', etc.
            'is_eligible': bool,  # True if should be shown to users
            'is_regular_season': bool,
            'is_nba_cup': bool,  # True if during NBA Cup period (Nov-Dec)
            'is_excluded': bool  # True if should be filtered out
        }
    """
    if not game_id or len(game_id) < 3:
        logger.warning(f"Invalid game_id: {game_id}")
        return {
            'game_type': 'unknown',
            'is_eligible': False,
            'is_regular_season': False,
            'is_nba_cup': False,
            'is_excluded': True
        }

    prefix = game_id[:3]

    # Regular Season (includes NBA Cup)
    if prefix == '002':
        # NBA Cup typically runs Nov-Dec with Championship in mid-December
        # But all 002 games are regular season, so we include them all
        is_nba_cup_period = False
        if game_date:
            try:
                # NBA Cup period: November through mid-December
                month = int(game_date[5:7]) if len(game_date) >= 7 else 0
                day = int(game_date[8:10]) if len(game_date) >= 10 else 0
                is_nba_cup_period = (month == 11) or (month == 12 and day <= 17)
            except (ValueError, IndexError):
                pass

        return {
            'game_type': 'nba_cup' if is_nba_cup_period else 'regular_season',
            'is_eligible': True,  # Always include regular season
            'is_regular_season': True,
            'is_nba_cup': is_nba_cup_period,
            'is_excluded': False
        }

    # Preseason
    elif prefix == '001':
        return {
            'game_type': 'preseason',
            'is_eligible': False,
            'is_regular_season': False,
            'is_nba_cup': False,
            'is_excluded': True
        }

    # All-Star
    elif prefix == '003':
        return {
            'game_type': 'all_star',
            'is_eligible': False,
            'is_regular_season': False,
            'is_nba_cup': False,
            'is_excluded': True
        }

    # Playoffs / Play-In
    elif prefix in ('004', '005'):
        return {
            'game_type': 'playoffs',
            'is_eligible': False,
            'is_regular_season': False,
            'is_nba_cup': False,
            'is_excluded': True
        }

    # Summer League
    elif prefix in ('132', '152', '162'):
        return {
            'game_type': 'summer_league',
            'is_eligible': False,
            'is_regular_season': False,
            'is_nba_cup': False,
            'is_excluded': True
        }

    # Unknown prefix
    else:
        logger.warning(f"Unknown game_id prefix: {prefix} (game_id: {game_id})")
        return {
            'game_type': 'unknown',
            'is_eligible': False,
            'is_regular_season': False,
            'is_nba_cup': False,
            'is_excluded': True
        }


def get_game_type_label(game_id: str, game_date: str = None) -> str:
    """
    Get a human-readable label for the game type.

    Returns: 'Regular Season', 'NBA Cup', 'Preseason', 'Playoffs', 'Summer League', etc.
    """
    classification = classify_game(game_id, game_date)
    game_type = classification['game_type']

    labels = {
        'regular_season': 'Regular Season',
        'nba_cup': 'NBA Cup',
        'preseason': 'Preseason',
        'playoffs': 'Playoffs',
        'all_star': 'All-Star',
        'summer_league': 'Summer League',
        'unknown': 'Unknown'
    }

    return labels.get(game_type, 'Unknown')


def filter_eligible_games(games: list, game_id_key: str = 'game_id',
                         game_date_key: str = 'game_date') -> Dict:
    """
    Filter a list of games to only include eligible games (Regular Season + NBA Cup).

    Args:
        games: List of game dictionaries
        game_id_key: Key name for game_id in the dict
        game_date_key: Key name for game_date in the dict

    Returns:
        {
            'filtered_games': list,
            'stats': {
                'unfiltered_count': int,
                'filtered_count': int,
                'regular_season_count': int,
                'nba_cup_count': int,
                'excluded_count': int,
                'excluded_types': dict  # breakdown by excluded type
            }
        }
    """
    stats = {
        'unfiltered_count': len(games),
        'filtered_count': 0,
        'regular_season_count': 0,
        'nba_cup_count': 0,
        'excluded_count': 0,
        'excluded_types': {}
    }

    filtered_games = []

    for game in games:
        game_id = game.get(game_id_key, '')
        game_date = game.get(game_date_key, '')

        classification = classify_game(game_id, game_date)

        if classification['is_eligible']:
            filtered_games.append(game)
            stats['filtered_count'] += 1

            if classification['is_nba_cup']:
                stats['nba_cup_count'] += 1
            else:
                stats['regular_season_count'] += 1
        else:
            stats['excluded_count'] += 1
            game_type = classification['game_type']
            stats['excluded_types'][game_type] = stats['excluded_types'].get(game_type, 0) + 1

    return {
        'filtered_games': filtered_games,
        'stats': stats
    }
