"""
AI Game Writeup Generator Module

Generates AI-powered 3-section analytical writeups for NBA games using OpenAI GPT-4o.

Sections:
1. Empty Possessions Analysis (4-6 sentences)
2. Archetype Matchups (4-6 sentences covering all 5 categories)
3. Last 5 Games Trends (4-6 sentences)

Uses deterministic prompts and structured context extraction for consistent, betting-focused analysis.
"""

import hashlib
import json
import time
import logging
from typing import Dict, Optional, Tuple
from openai import OpenAI, RateLimitError

# Import OpenAI client utility
try:
    from api.utils.openai_client import get_client, OpenAIKeyMissingError
except ImportError:
    from openai_client import get_client, OpenAIKeyMissingError

logger = logging.getLogger(__name__)

# Engine version for cache invalidation when prompt changes
ENGINE_VERSION = 'v1'


def build_writeup_context(game_data: Dict) -> Dict:
    """
    Extract and structure relevant data from game_data for AI writeup generation.

    Args:
        game_data: Complete game data dict from /api/game_detail endpoint

    Returns:
        Structured context dict with:
            - game_id: str
            - home_team: dict (abbreviation, full_name)
            - away_team: dict (abbreviation, full_name)
            - empty_possessions: dict (score, metrics, etc.)
            - home_archetypes: dict (offensive, defensive styles)
            - away_archetypes: dict (offensive, defensive styles)
            - home_last5_trends: dict (recent form, pace, efficiency)
            - away_last5_trends: dict (recent form, pace, efficiency)
            - back_to_back_info: dict (rest days, fatigue factors)
    """
    context = {
        'game_id': game_data.get('game_id', 'unknown'),
        'home_team': {
            'abbreviation': game_data.get('home_team', {}).get('abbreviation', 'UNK'),
            'full_name': game_data.get('home_team', {}).get('full_name', 'Unknown')
        },
        'away_team': {
            'abbreviation': game_data.get('away_team', {}).get('abbreviation', 'UNK'),
            'full_name': game_data.get('away_team', {}).get('full_name', 'Unknown')
        }
    }

    # Empty Possessions Data
    ep_data = game_data.get('empty_possessions', {})
    context['empty_possessions'] = {
        'score': ep_data.get('matchup_score', 0),
        'home_to_pct': ep_data.get('home_metrics', {}).get('turnover_pct', 0),
        'away_to_pct': ep_data.get('away_metrics', {}).get('turnover_pct', 0),
        'home_oreb_pct': ep_data.get('home_metrics', {}).get('oreb_pct', 0),
        'away_oreb_pct': ep_data.get('away_metrics', {}).get('oreb_pct', 0),
        'home_ftr': ep_data.get('home_metrics', {}).get('ft_rate', 0),
        'away_ftr': ep_data.get('away_metrics', {}).get('ft_rate', 0),
        'efficiency_label': ep_data.get('efficiency_label', 'Average'),
        'league_avg_to': 14.0  # NBA league average turnover %
    }

    # Archetype Data
    context['home_archetypes'] = game_data.get('home_archetypes', {})
    context['away_archetypes'] = game_data.get('away_archetypes', {})

    # Last 5 Trends Data
    context['home_last5_trends'] = game_data.get('home_last5_trends', {})
    context['away_last5_trends'] = game_data.get('away_last5_trends', {})

    # Back-to-Back / Rest Data
    context['back_to_back_info'] = game_data.get('back_to_back_debug', {})

    return context


def calculate_data_hash(context: Dict) -> str:
    """
    Calculate MD5 hash of key context fields for cache invalidation.

    Hash changes when any of these data sources change:
    - Empty possessions metrics
    - Home/away archetypes
    - Last 5 trends
    - Back-to-back rest days

    Args:
        context: Structured context dict from build_writeup_context

    Returns:
        32-character MD5 hash string
    """
    # Extract hashable fields (sorted for consistency)
    hashable_data = {
        'engine_version': ENGINE_VERSION,
        'empty_possessions': context.get('empty_possessions', {}),
        'home_archetypes': context.get('home_archetypes', {}),
        'away_archetypes': context.get('away_archetypes', {}),
        'home_last5': context.get('home_last5_trends', {}),
        'away_last5': context.get('away_last5_trends', {}),
        'back_to_back': context.get('back_to_back_info', {})
    }

    # Convert to sorted JSON string for consistent hashing
    json_str = json.dumps(hashable_data, sort_keys=True)
    hash_obj = hashlib.md5(json_str.encode('utf-8'))

    return hash_obj.hexdigest()


def generate_writeup_prompt(context: Dict) -> Tuple[str, str]:
    """
    Build system and user prompts for OpenAI GPT-4o writeup generation.

    Args:
        context: Structured context dict from build_writeup_context

    Returns:
        Tuple of (system_message, user_message)
    """
    system_message = """You are an expert NBA betting analyst specializing in Over/Under predictions.

Generate a 3-section analytical write-up to help bettors make informed decisions.

CRITICAL REQUIREMENTS:
1. Exactly 3 sections (Empty Possessions, Archetype Matchups, Last 5 Trends)
2. Each section: 4-6 sentences (STRICT)
3. Focus on Over/Under implications only
4. Use specific data points from context
5. Professional but accessible (8th-grade reading level)
6. NO betting advice ("hammer", "lock") - analysis only
7. IMPORTANT: Wrap ALL numbers in **bold** (e.g., **12.3%**, **105.2 PPG**, **+4.5**)

Output: Plain text with double line breaks between sections (NO section headers)."""

    # Extract data for prompt
    home_abbr = context['home_team']['abbreviation']
    away_abbr = context['away_team']['abbreviation']
    home_name = context['home_team']['full_name']
    away_name = context['away_team']['full_name']

    ep = context['empty_possessions']
    home_arch = context['home_archetypes']
    away_arch = context['away_archetypes']
    home_l5 = context['home_last5_trends']
    away_l5 = context['away_last5_trends']

    # Get archetype labels safely
    home_off_scoring = home_arch.get('offensive', {}).get('scoring', {}).get('label', 'Balanced Scorer')
    home_off_3pt = home_arch.get('offensive', {}).get('three_pt', {}).get('label', 'Balanced 3PT')
    home_off_ast = home_arch.get('offensive', {}).get('assists', {}).get('label', 'Balanced Assists')
    home_off_reb = home_arch.get('offensive', {}).get('rebounds', {}).get('label', 'Balanced Rebounds')
    home_off_tov = home_arch.get('offensive', {}).get('turnovers', {}).get('label', 'Balanced Turnovers')

    away_def_scoring = away_arch.get('defensive', {}).get('scoring', {}).get('label', 'Balanced Defense')
    away_def_3pt = away_arch.get('defensive', {}).get('three_pt', {}).get('label', 'Balanced 3PT Defense')
    away_def_ast = away_arch.get('defensive', {}).get('assists', {}).get('label', 'Balanced Assist Defense')
    away_def_reb = away_arch.get('defensive', {}).get('rebounds', {}).get('label', 'Balanced Rebound Defense')
    away_def_tov = away_arch.get('defensive', {}).get('turnovers', {}).get('label', 'Balanced Turnover Defense')

    away_off_scoring = away_arch.get('offensive', {}).get('scoring', {}).get('label', 'Balanced Scorer')
    away_off_3pt = away_arch.get('offensive', {}).get('three_pt', {}).get('label', 'Balanced 3PT')
    away_off_ast = away_arch.get('offensive', {}).get('assists', {}).get('label', 'Balanced Assists')
    away_off_reb = away_arch.get('offensive', {}).get('rebounds', {}).get('label', 'Balanced Rebounds')
    away_off_tov = away_arch.get('offensive', {}).get('turnovers', {}).get('label', 'Balanced Turnovers')

    home_def_scoring = home_arch.get('defensive', {}).get('scoring', {}).get('label', 'Balanced Defense')
    home_def_3pt = home_arch.get('defensive', {}).get('three_pt', {}).get('label', 'Balanced 3PT Defense')
    home_def_ast = home_arch.get('defensive', {}).get('assists', {}).get('label', 'Balanced Assist Defense')
    home_def_reb = home_arch.get('defensive', {}).get('rebounds', {}).get('label', 'Balanced Rebound Defense')
    home_def_tov = home_arch.get('defensive', {}).get('turnovers', {}).get('label', 'Balanced Turnover Defense')

    # Get Last 5 trends
    home_l5_ppg = home_l5.get('ppg', 0)
    home_l5_ppg_delta = home_l5.get('ppg_vs_season', 0)
    home_l5_pace = home_l5.get('pace', 0)
    home_l5_pace_delta = home_l5.get('pace_vs_season', 0)
    home_l5_ortg = home_l5.get('off_rtg', 0)
    home_l5_ortg_delta = home_l5.get('off_rtg_vs_season', 0)
    home_l5_drtg = home_l5.get('def_rtg', 0)
    home_l5_drtg_delta = home_l5.get('def_rtg_vs_season', 0)

    away_l5_ppg = away_l5.get('ppg', 0)
    away_l5_ppg_delta = away_l5.get('ppg_vs_season', 0)
    away_l5_pace = away_l5.get('pace', 0)
    away_l5_pace_delta = away_l5.get('pace_vs_season', 0)
    away_l5_ortg = away_l5.get('off_rtg', 0)
    away_l5_ortg_delta = away_l5.get('off_rtg_vs_season', 0)
    away_l5_drtg = away_l5.get('def_rtg', 0)
    away_l5_drtg_delta = away_l5.get('def_rtg_vs_season', 0)

    # Calculate combined last 5 avg total
    combined_last5_total = round(home_l5_ppg + away_l5_ppg, 1) if home_l5_ppg and away_l5_ppg else 0

    # Rest days info
    b2b_info = context.get('back_to_back_info', {})
    home_rest = b2b_info.get('home_rest_days', 1)
    away_rest = b2b_info.get('away_rest_days', 1)

    user_message = f"""
Analyze {home_name} vs {away_name}:

=== SECTION 1: Empty Possessions Analysis (4-6 sentences) ===
- Empty Poss Score: {ep['score']}/100 ({ep['efficiency_label']})
- {home_abbr} TO%: {ep['home_to_pct']:.1f}% (League avg: {ep['league_avg_to']}%)
- {away_abbr} TO%: {ep['away_to_pct']:.1f}%
- {home_abbr} OREB%: {ep['home_oreb_pct']:.1f}%, FTr: {ep['home_ftr']:.1f}%
- {away_abbr} OREB%: {ep['away_oreb_pct']:.1f}%, FTr: {ep['away_ftr']:.1f}%

TASK: Analyze possession efficiency, turnover impact, extra possession creation (OREB/FTr), and O/U implication

=== SECTION 2: Archetype Matchups (4-6 sentences covering ALL 5 categories) ===
SCORING: {home_abbr} {home_off_scoring} vs {away_abbr} {away_def_scoring} | {away_abbr} {away_off_scoring} vs {home_abbr} {home_def_scoring}
3PT: {home_abbr} {home_off_3pt} vs {away_abbr} {away_def_3pt} | {away_abbr} {away_off_3pt} vs {home_abbr} {home_def_3pt}
ASSISTS: {home_abbr} {home_off_ast} vs {away_abbr} {away_def_ast} | {away_abbr} {away_off_ast} vs {home_abbr} {home_def_ast}
REBOUNDS: {home_abbr} {home_off_reb} vs {away_abbr} {away_def_reb} | {away_abbr} {away_off_reb} vs {home_abbr} {home_def_reb}
TURNOVERS: {home_abbr} {home_off_tov} vs {away_abbr} {away_def_tov} | {away_abbr} {away_off_tov} vs {home_abbr} {home_def_tov}

TASK: Analyze clashes, mismatches, dominant tendencies, and O/U outlook across ALL 5 categories

=== SECTION 3: Last 5 Trends (4-6 sentences) ===
{home_abbr} Last 5: PPG {home_l5_ppg:.1f} (Δ{home_l5_ppg_delta:+.1f}), Pace {home_l5_pace:.1f} (Δ{home_l5_pace_delta:+.1f}), ORTG {home_l5_ortg:.1f} (Δ{home_l5_ortg_delta:+.1f}), DRTG {home_l5_drtg:.1f} (Δ{home_l5_drtg_delta:+.1f}), Rest: {home_rest} days
{away_abbr} Last 5: PPG {away_l5_ppg:.1f} (Δ{away_l5_ppg_delta:+.1f}), Pace {away_l5_pace:.1f} (Δ{away_l5_pace_delta:+.1f}), ORTG {away_l5_ortg:.1f} (Δ{away_l5_ortg_delta:+.1f}), DRTG {away_l5_drtg:.1f} (Δ{away_l5_drtg_delta:+.1f}), Rest: {away_rest} days
Combined last 5 avg: {combined_last5_total} points

TASK: Hot/cold trends, pace changes, rest impact, combined recent scoring average

Generate write-up (plain text, no headers, double line breaks between sections):
"""

    return (system_message, user_message)


def generate_with_retry(client: OpenAI, messages: list, max_retries: int = 3) -> Optional[str]:
    """
    Call OpenAI API with exponential backoff retry logic.

    Args:
        client: OpenAI client instance
        messages: List of message dicts for chat.completions.create
        max_retries: Maximum retry attempts

    Returns:
        Generated text content or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=600,
                timeout=15
            )
            return response.choices[0].message.content
        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"[ai_writeup] Rate limit hit, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.error(f"[ai_writeup] Rate limit exceeded after {max_retries} retries")
            return None
        except Exception as e:
            logger.error(f"[ai_writeup] OpenAI error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            return None
    return None


def generate_game_writeup(game_data: Dict) -> Optional[str]:
    """
    Generate AI-powered game writeup using OpenAI GPT-4o.

    Main entry point for writeup generation. Extracts context, builds prompts,
    calls OpenAI API, and returns formatted 3-section writeup.

    Args:
        game_data: Complete game data dict from /api/game_detail endpoint
            Required fields:
            - game_id
            - home_team (abbreviation, full_name)
            - away_team (abbreviation, full_name)
            - empty_possessions
            - home_archetypes, away_archetypes
            - home_last5_trends, away_last5_trends
            - back_to_back_debug (optional)

    Returns:
        3-section writeup text (plain text, double line breaks between sections)
        Returns None if generation fails

    Example Output:
        "Empty Possessions Score: 68.2/100, indicating above-average efficiency...
        [4-6 sentences total]

        Boston's Elite Volume Scorer clashes with LA's Rim Protection...
        [4-6 sentences covering all 5 archetype categories]

        Boston enters hot, averaging 121.8 PPG over last 5 (+6.6 vs season)...
        [4-6 sentences with trends and deltas]"
    """
    try:
        start_time = time.time()
        game_id = game_data.get('game_id', 'unknown')

        logger.info(f"[ai_writeup] Starting generation for game {game_id}")

        # Step 1: Build context
        context = build_writeup_context(game_data)

        # Step 2: Generate prompts
        system_message, user_message = generate_writeup_prompt(context)

        # Step 3: Get OpenAI client
        client = get_client()

        # Step 4: Call OpenAI with retry logic
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        writeup_text = generate_with_retry(client, messages, max_retries=3)

        if not writeup_text:
            logger.error(f"[ai_writeup] Failed to generate writeup for game {game_id}")
            return None

        # Step 5: Clean up response (remove any markdown artifacts)
        writeup_text = writeup_text.strip()
        if writeup_text.startswith('```'):
            # Remove markdown code blocks if present
            parts = writeup_text.split('```')
            if len(parts) >= 2:
                writeup_text = parts[1].strip()

        elapsed = time.time() - start_time
        logger.info(f"[ai_writeup] Generated for game {game_id} in {elapsed:.2f}s")

        return writeup_text

    except OpenAIKeyMissingError:
        logger.error("[ai_writeup] OPENAI_API_KEY not configured")
        return None
    except Exception as e:
        logger.error(f"[ai_writeup] Unexpected error generating writeup: {e}")
        return None
