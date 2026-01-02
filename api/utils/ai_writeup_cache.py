"""
AI Writeup Cache Module

Manages caching of AI-generated game writeups in SQLite database.
Implements cache validation, retrieval, and regeneration logic.

Cache Invalidation Strategy:
- Data hash changes (empty possessions, archetypes, last5 trends modified)
- Engine version changes (prompt updated)

Target: 85%+ cache hit rate for cost optimization.
"""

import sqlite3
import logging
from typing import Dict, Optional
from datetime import datetime

# Import generator and db config
try:
    from api.utils.ai_game_writeup_generator import (
        build_writeup_context,
        calculate_data_hash,
        generate_game_writeup,
        ENGINE_VERSION
    )
    from api.utils.db_config import get_db_path
except ImportError:
    from ai_game_writeup_generator import (
        build_writeup_context,
        calculate_data_hash,
        generate_game_writeup,
        ENGINE_VERSION
    )
    from db_config import get_db_path

logger = logging.getLogger(__name__)

# Database path
NBA_DATA_DB_PATH = get_db_path('nba_data.db')


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection to nba_data.db with row factory"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def get_cached_writeup(game_id: str) -> Optional[Dict]:
    """
    Retrieve cached writeup from database.

    Args:
        game_id: Unique game identifier

    Returns:
        Dict with:
            - writeup_text: str
            - data_hash: str
            - engine_version: str
            - created_at: str (ISO timestamp)
            - updated_at: str (ISO timestamp)
        Returns None if not found
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT game_id, writeup_text, data_hash, engine_version, created_at, updated_at
            FROM ai_game_writeups
            WHERE game_id = ?
        ''', (game_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'game_id': row['game_id'],
                'writeup_text': row['writeup_text'],
                'data_hash': row['data_hash'],
                'engine_version': row['engine_version'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }

        return None

    except Exception as e:
        logger.error(f"[ai_writeup_cache] Error retrieving cached writeup for game {game_id}: {e}")
        return None


def save_writeup(game_id: str, writeup_text: str, data_hash: str) -> bool:
    """
    Save writeup to database with upsert logic.

    If writeup exists, updates it with new text, hash, and timestamp.
    If writeup doesn't exist, creates new entry.

    Args:
        game_id: Unique game identifier
        writeup_text: Generated writeup text (3 sections)
        data_hash: MD5 hash of source data

    Returns:
        True if save successful, False otherwise
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Use INSERT OR REPLACE to handle upsert
        cursor.execute('''
            INSERT OR REPLACE INTO ai_game_writeups
            (game_id, writeup_text, data_hash, engine_version, created_at, updated_at)
            VALUES (
                ?,
                ?,
                ?,
                ?,
                COALESCE((SELECT created_at FROM ai_game_writeups WHERE game_id = ?), CURRENT_TIMESTAMP),
                CURRENT_TIMESTAMP
            )
        ''', (game_id, writeup_text, data_hash, ENGINE_VERSION, game_id))

        conn.commit()
        conn.close()

        logger.info(f"[ai_writeup_cache] Saved writeup for game {game_id} (hash: {data_hash[:8]}...)")
        return True

    except Exception as e:
        logger.error(f"[ai_writeup_cache] Error saving writeup for game {game_id}: {e}")
        return False


def should_regenerate(game_id: str, current_hash: str) -> bool:
    """
    Determine if cached writeup should be regenerated.

    Regenerate if:
    1. No cached writeup exists
    2. Data hash has changed (source data updated)
    3. Engine version has changed (prompt updated)

    Args:
        game_id: Unique game identifier
        current_hash: Current MD5 hash of game data

    Returns:
        True if regeneration needed, False if cache is valid
    """
    cached = get_cached_writeup(game_id)

    if not cached:
        logger.info(f"[ai_writeup_cache] No cache exists for game {game_id} - regenerating")
        return True

    # Check engine version
    if cached['engine_version'] != ENGINE_VERSION:
        logger.info(f"[ai_writeup_cache] Engine version changed ({cached['engine_version']} → {ENGINE_VERSION}) - regenerating game {game_id}")
        return True

    # Check data hash
    if cached['data_hash'] != current_hash:
        logger.info(f"[ai_writeup_cache] Data hash changed ({cached['data_hash'][:8]}... → {current_hash[:8]}...) - regenerating game {game_id}")
        return True

    logger.info(f"[ai_writeup_cache] Cache HIT for game {game_id}")
    return False


def get_or_generate_writeup(game_data: Dict) -> Optional[str]:
    """
    Main orchestration function for cached AI writeup retrieval/generation.

    Workflow:
    1. Extract context from game_data
    2. Calculate current data hash
    3. Check if cached writeup exists and is valid
    4. If cache miss: Generate new writeup with OpenAI
    5. Save new writeup to database
    6. Return writeup text

    Args:
        game_data: Complete game data dict from /api/game_detail endpoint
            Required fields:
            - game_id
            - home_team, away_team
            - empty_possessions
            - home_archetypes, away_archetypes
            - home_last5_trends, away_last5_trends

    Returns:
        Writeup text (3 sections, plain text with double line breaks)
        Returns None if generation fails or data is missing

    Cache Hit Rate Target: 85%+
    Average Generation Time: <3s
    """
    try:
        game_id = game_data.get('game_id')
        if not game_id:
            logger.warning("[ai_writeup_cache] game_id missing from game_data")
            return None

        # Step 1: Build context and calculate hash
        context = build_writeup_context(game_data)
        current_hash = calculate_data_hash(context)

        # Step 2: Check cache validity
        if not should_regenerate(game_id, current_hash):
            # Cache hit - return cached writeup
            cached = get_cached_writeup(game_id)
            if cached:
                return cached['writeup_text']

        # Step 3: Cache miss - generate new writeup
        logger.info(f"[ai_writeup_cache] Generating new writeup for game {game_id}")
        writeup_text = generate_game_writeup(game_data)

        if not writeup_text:
            logger.warning(f"[ai_writeup_cache] Failed to generate writeup for game {game_id}")
            return None

        # Step 4: Save to cache
        save_success = save_writeup(game_id, writeup_text, current_hash)
        if not save_success:
            logger.warning(f"[ai_writeup_cache] Failed to save writeup to cache for game {game_id}")
            # Still return the generated writeup even if save failed

        return writeup_text

    except Exception as e:
        logger.error(f"[ai_writeup_cache] Unexpected error in get_or_generate_writeup: {e}")
        return None


def clear_cache_for_game(game_id: str) -> bool:
    """
    Delete cached writeup for a specific game.

    Useful for manual cache invalidation during testing or data corrections.

    Args:
        game_id: Unique game identifier

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM ai_game_writeups WHERE game_id = ?', (game_id,))
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info(f"[ai_writeup_cache] Cleared cache for game {game_id}")
            return True
        else:
            logger.info(f"[ai_writeup_cache] No cache to clear for game {game_id}")
            return False

    except Exception as e:
        logger.error(f"[ai_writeup_cache] Error clearing cache for game {game_id}: {e}")
        return False


def get_cache_stats() -> Dict:
    """
    Get cache statistics for monitoring.

    Returns:
        Dict with:
            - total_cached: int (total writeups in cache)
            - by_engine_version: dict (breakdown by engine version)
            - oldest_entry: str (ISO timestamp of oldest cached writeup)
            - newest_entry: str (ISO timestamp of newest cached writeup)
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Total count
        cursor.execute('SELECT COUNT(*) as total FROM ai_game_writeups')
        total_cached = cursor.fetchone()['total']

        # By engine version
        cursor.execute('''
            SELECT engine_version, COUNT(*) as count
            FROM ai_game_writeups
            GROUP BY engine_version
        ''')
        version_breakdown = {row['engine_version']: row['count'] for row in cursor.fetchall()}

        # Oldest and newest
        cursor.execute('SELECT MIN(created_at) as oldest, MAX(created_at) as newest FROM ai_game_writeups')
        timestamps = cursor.fetchone()

        conn.close()

        return {
            'total_cached': total_cached,
            'by_engine_version': version_breakdown,
            'oldest_entry': timestamps['oldest'],
            'newest_entry': timestamps['newest']
        }

    except Exception as e:
        logger.error(f"[ai_writeup_cache] Error getting cache stats: {e}")
        return {
            'total_cached': 0,
            'by_engine_version': {},
            'oldest_entry': None,
            'newest_entry': None
        }
