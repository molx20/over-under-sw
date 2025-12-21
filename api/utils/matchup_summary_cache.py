"""
Matchup Summary Cache Module

Handles caching of AI-generated matchup summaries in SQLite.
Implements cache-first logic to avoid redundant LLM calls.

Cache key format: game_id + payload_version + engine_version
This ensures cache invalidation when data structure or generation logic changes.
"""

import sqlite3
import json
import os
from typing import Optional, Dict
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'nba_data.db')

# Import versions from generator (single source of truth)
from api.utils.matchup_summary_generator import ENGINE_VERSION, PAYLOAD_VERSION


def get_cache_key(game_id: str, payload_version: str = PAYLOAD_VERSION,
                  engine_version: str = ENGINE_VERSION) -> str:
    """
    Generate composite cache key.

    Format: game_id + payload_version + engine_version
    This ensures cache invalidation when data structure or logic changes.
    """
    return f"{game_id}::{payload_version}::{engine_version}"


def get_cached_summary(game_id: str, payload_version: str = PAYLOAD_VERSION,
                       engine_version: str = ENGINE_VERSION) -> Optional[Dict]:
    """
    Retrieve cached matchup summary for a game.

    Args:
        game_id: NBA game ID (e.g., "0022501207")
        payload_version: Payload structure version (default: current version)
        engine_version: Engine version to match (default: current version)

    Returns:
        Dictionary with summary sections, or None if not found
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query with composite key (game_id + payload_version + engine_version)
        cursor.execute('''
            SELECT summary_json FROM matchup_summaries
            WHERE game_id = ? AND engine_version = ?
        ''', (game_id, engine_version))

        row = cursor.fetchone()
        conn.close()

        if row:
            cached_data = json.loads(row[0])

            # Verify payload version matches (for safety)
            cached_payload_version = cached_data.get('payload_version', 'v0')
            if cached_payload_version != payload_version:
                print(f"[matchup_cache] ✗ Cache STALE for game {game_id} (payload version mismatch: {cached_payload_version} != {payload_version})")
                return None

            print(f"[matchup_cache] ✓ Cache HIT for game {game_id} (payload={payload_version}, engine={engine_version})")
            return cached_data
        else:
            print(f"[matchup_cache] ✗ Cache MISS for game {game_id}")
            return None

    except Exception as e:
        print(f"[matchup_cache] ERROR reading cache: {str(e)}")
        return None


def save_summary(game_id: str, summary: Dict, payload_version: str = PAYLOAD_VERSION,
                 engine_version: str = ENGINE_VERSION) -> bool:
    """
    Save generated matchup summary to cache.

    Args:
        game_id: NBA game ID
        summary: Summary dictionary with all sections
        payload_version: Payload structure version
        engine_version: Engine version (default: current version)

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Ensure version metadata is in summary
        summary['payload_version'] = payload_version
        summary['engine_version'] = engine_version

        summary_json = json.dumps(summary)
        now = datetime.now().isoformat()

        # Use INSERT OR REPLACE to handle both new and updated entries
        cursor.execute('''
            INSERT OR REPLACE INTO matchup_summaries (game_id, summary_json, engine_version, created_at, updated_at)
            VALUES (?, ?, ?, COALESCE((SELECT created_at FROM matchup_summaries WHERE game_id = ?), ?), ?)
        ''', (game_id, summary_json, engine_version, game_id, now, now))

        conn.commit()
        conn.close()

        cache_key = get_cache_key(game_id, payload_version, engine_version)
        print(f"[matchup_cache] ✓ Saved summary (key={cache_key})")
        return True

    except Exception as e:
        print(f"[matchup_cache] ERROR saving summary: {str(e)}")
        return False


def get_or_generate_summary(game_id: str, prediction: Dict, matchup_data: Dict,
                            home_team: Dict, away_team: Dict,
                            force_regenerate: bool = False,
                            payload_version: str = PAYLOAD_VERSION,
                            engine_version: str = ENGINE_VERSION) -> Optional[Dict]:
    """
    Get matchup summary from cache, or generate if not found.

    This is the main entry point for the cache-first logic.

    Args:
        game_id: NBA game ID
        prediction: Prediction engine output
        matchup_data: Matchup data from get_matchup_data()
        home_team: Home team info
        away_team: Away team info
        force_regenerate: If True, bypass cache and regenerate
        payload_version: Payload structure version (default: current version)
        engine_version: Engine version (default: current version)

    Returns:
        Summary dictionary, or None if generation failed
    """
    # Check cache first (unless force_regenerate is True)
    existing_writeups = None
    if not force_regenerate:
        cached = get_cached_summary(game_id, payload_version, engine_version)
        if cached:
            return cached

        # Check if we have an older version that we can partially reuse
        # (Different version = cache miss, but we can extract existing sections)
        old_cached = _get_any_cached_summary(game_id)
        if old_cached:
            print(f"[matchup_cache] Found older cached version - will reuse compatible sections")
            existing_writeups = extract_reusable_sections(old_cached)

    # Cache miss or forced regeneration - generate new summary
    cache_key = get_cache_key(game_id, payload_version, engine_version)
    print(f"[matchup_cache] Generating summary (key={cache_key})...")

    from api.utils.matchup_summary_generator import generate_matchup_summary

    summary = generate_matchup_summary(
        game_id, prediction, matchup_data, home_team, away_team,
        existing_writeups=existing_writeups
    )

    if summary:
        # Save to cache for future requests
        save_summary(game_id, summary, payload_version, engine_version)
        return summary
    else:
        print(f"[matchup_cache] ERROR: Failed to generate summary for game {game_id}")
        return None


def _get_any_cached_summary(game_id: str) -> Optional[Dict]:
    """
    Get any cached summary for a game (ignoring version).

    Used for extracting reusable sections from older cache entries.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT summary_json FROM matchup_summaries
            WHERE game_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        ''', (game_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    except Exception as e:
        print(f"[matchup_cache] ERROR reading old cache: {str(e)}")
        return None


def extract_reusable_sections(cached_summary: Dict) -> Dict:
    """
    Extract sections from cached summary that can be reused.

    Some sections (like volatility_profile, matchup_dna_summary) can be reused
    even if the payload version changed, as long as the core data is similar.
    """
    reusable = {}

    # List of sections that can be safely reused
    reusable_section_keys = [
        'pace_and_flow',
        'offensive_style',
        'shooting_profile',
        'rim_and_paint',
        'recent_form',
        'volatility_profile',
        'matchup_dna_summary'
    ]

    for key in reusable_section_keys:
        if key in cached_summary:
            reusable[key] = cached_summary[key]

    print(f"[matchup_cache] Extracted {len(reusable)} reusable sections from old cache")
    return reusable


def clear_cache_for_game(game_id: str) -> bool:
    """
    Remove cached summary for a specific game.

    Useful for manual cache invalidation.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM matchup_summaries WHERE game_id = ?', (game_id,))
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        if deleted > 0:
            print(f"[matchup_cache] Cleared cache for game {game_id}")
            return True
        else:
            print(f"[matchup_cache] No cache entry found for game {game_id}")
            return False

    except Exception as e:
        print(f"[matchup_cache] ERROR clearing cache: {str(e)}")
        return False


def get_cache_stats() -> Dict:
    """
    Get statistics about the cache.

    Returns dictionary with total_entries, engine_versions, etc.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Total entries
        cursor.execute('SELECT COUNT(*) FROM matchup_summaries')
        total = cursor.fetchone()[0]

        # Entries by engine version
        cursor.execute('''
            SELECT engine_version, COUNT(*) as count
            FROM matchup_summaries
            GROUP BY engine_version
        ''')
        by_version = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            'total_entries': total,
            'by_version': by_version
        }

    except Exception as e:
        print(f"[matchup_cache] ERROR getting stats: {str(e)}")
        return {'total_entries': 0, 'by_version': {}}
