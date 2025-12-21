"""
Matchup Summary Generator

Generates structured narrative summaries for NBA game matchups using LLM.
All summaries follow strict sentence count rules and 5th-grade reading level.

Rules:
- 7 sections with exact sentence counts
- NO betting language (no "locks", "hammer", "best bet", etc.)
- 5th-grade reading level but adult tone
- Model reference total only (not a pick)
"""

import json
from typing import Dict, Optional
from api.utils.openai_client import get_client, OpenAIKeyMissingError

ENGINE_VERSION = "v2"  # Updated: structured JSON payload + stricter validation
PAYLOAD_VERSION = "v1"  # Increment when context structure changes


def build_context_for_llm(prediction: Dict, matchup_data: Dict, home_team: Dict, away_team: Dict) -> Dict:
    """
    Extract relevant data from prediction engine output to build LLM context.

    Returns a compact dictionary with all the stats needed for narrative generation.
    """
    # Extract breakdown and factors
    breakdown = prediction.get('breakdown', {})
    factors = prediction.get('factors', {})

    # Get team stats
    home_stats = matchup_data.get('home', {}).get('stats', {}).get('overall', {})
    away_stats = matchup_data.get('away', {}).get('stats', {}).get('overall', {})
    home_adv = matchup_data.get('home', {}).get('advanced', {})
    away_adv = matchup_data.get('away', {}).get('advanced', {})
    home_last5 = matchup_data.get('home', {}).get('last5', {})
    away_last5 = matchup_data.get('away', {}).get('last5', {})

    # Build compact context
    context = {
        # Team identifiers
        'home_team': home_team.get('abbreviation', 'HOME'),
        'away_team': away_team.get('abbreviation', 'AWAY'),

        # Pace data
        'game_pace': round(breakdown.get('game_pace', 100), 1),
        'home_pace_season': round(home_adv.get('PACE', 100), 1),
        'away_pace_season': round(away_adv.get('PACE', 100), 1),
        'home_pace_last5': round(home_last5.get('PACE', 100), 1) if home_last5 else None,
        'away_pace_last5': round(away_last5.get('PACE', 100), 1) if away_last5 else None,

        # Offensive stats (season)
        'home_ppg_season': round(home_stats.get('PTS', 110), 1),
        'away_ppg_season': round(away_stats.get('PTS', 110), 1),
        'home_ortg_season': round(home_adv.get('OFF_RATING', 110), 1),
        'away_ortg_season': round(away_adv.get('OFF_RATING', 110), 1),

        # Offensive stats (last 5)
        'home_ppg_last5': round(home_last5.get('PTS', 110), 1) if home_last5 else None,
        'away_ppg_last5': round(away_last5.get('PTS', 110), 1) if away_last5 else None,
        'home_ortg_last5': round(home_last5.get('OFF_RATING', 110), 1) if home_last5 else None,
        'away_ortg_last5': round(away_last5.get('OFF_RATING', 110), 1) if away_last5 else None,

        # Defensive stats (season)
        'home_drtg_season': round(home_adv.get('DEF_RATING', 112), 1),
        'away_drtg_season': round(away_adv.get('DEF_RATING', 112), 1),
        'home_def_rank': breakdown.get('home_defense_rank', 15),
        'away_def_rank': breakdown.get('away_defense_rank', 15),

        # Defensive stats (last 5)
        'home_drtg_last5': round(home_last5.get('DEF_RATING', 112), 1) if home_last5 else None,
        'away_drtg_last5': round(away_last5.get('DEF_RATING', 112), 1) if away_last5 else None,

        # 3PT stats (season)
        'home_3pt_pct_season': round(home_stats.get('FG3_PCT', 0.35) * 100, 1),
        'away_3pt_pct_season': round(away_stats.get('FG3_PCT', 0.35) * 100, 1),
        'home_3pa_season': round(home_stats.get('FG3A', 35), 1),
        'away_3pa_season': round(away_stats.get('FG3A', 35), 1),
        'home_3pt_def_pct': round(factors.get('home_3pt_def_pct', 0.36) * 100, 1),
        'away_3pt_def_pct': round(factors.get('away_3pt_def_pct', 0.36) * 100, 1),

        # 3PT stats (last 5)
        'home_3pt_pct_last5': round(home_last5.get('FG3_PCT', 0.35) * 100, 1) if home_last5 else None,
        'away_3pt_pct_last5': round(away_last5.get('FG3_PCT', 0.35) * 100, 1) if away_last5 else None,

        # Paint/rim stats
        'home_fga_season': round(home_stats.get('FGA', 85), 1),
        'away_fga_season': round(away_stats.get('FGA', 85), 1),
        'home_fta_season': round(home_stats.get('FTA', 22), 1),
        'away_fta_season': round(away_stats.get('FTA', 22), 1),
        'home_oreb_season': round(home_stats.get('OREB', 10), 1),
        'away_oreb_season': round(away_stats.get('OREB', 10), 1),

        # Matchup type & cluster
        'matchup_type': factors.get('matchup_type', 'Balanced Matchup'),
        'home_cluster': factors.get('home_cluster', 'Balanced'),
        'away_cluster': factors.get('away_cluster', 'Balanced'),

        # Shootout bonus
        'shootout_bonus': round(breakdown.get('shootout_bonus', 0), 1),

        # Back-to-back & rest
        'home_rest_days': factors.get('home_rest_days', 1),
        'away_rest_days': factors.get('away_rest_days', 1),

        # Model prediction
        'model_reference_total': round(prediction.get('predicted_total', 220), 1),
        'home_projected': round(breakdown.get('home_projected', 110), 1),
        'away_projected': round(breakdown.get('away_projected', 110), 1),
    }

    return context


def generate_matchup_summary(game_id: str, prediction: Dict, matchup_data: Dict,
                             home_team: Dict, away_team: Dict, existing_writeups: Optional[Dict] = None) -> Optional[Dict]:
    """
    Generate a structured matchup summary using LLM.

    Returns JSON with 7 narrative sections + model reference total.
    Each section has strict sentence count requirements.

    Args:
        game_id: NBA game ID
        prediction: Prediction engine output
        matchup_data: Matchup data from get_matchup_data()
        home_team: Home team info
        away_team: Away team info
        existing_writeups: Optional dict of previously cached sections to reuse
    """
    try:
        client = get_client()
    except OpenAIKeyMissingError:
        print("[matchup_summary] ERROR: OpenAI API key not configured")
        return None

    # Build context from prediction data
    context = build_context_for_llm(prediction, matchup_data, home_team, away_team)

    # Build matchup payload (structured JSON)
    matchup_payload = {
        "game_id": game_id,
        "teams": {
            "home": context['home_team'],
            "away": context['away_team']
        },
        "pace": {
            "expected_game_pace": context['game_pace'],
            "home_season_pace": context['home_pace_season'],
            "away_season_pace": context['away_pace_season'],
            "home_last5_pace": context.get('home_pace_last5'),
            "away_last5_pace": context.get('away_pace_last5')
        },
        "offense": {
            "home_ppg_season": context['home_ppg_season'],
            "away_ppg_season": context['away_ppg_season'],
            "home_ortg_season": context['home_ortg_season'],
            "away_ortg_season": context['away_ortg_season'],
            "home_ppg_last5": context.get('home_ppg_last5'),
            "away_ppg_last5": context.get('away_ppg_last5'),
            "home_ortg_last5": context.get('home_ortg_last5'),
            "away_ortg_last5": context.get('away_ortg_last5')
        },
        "defense": {
            "home_drtg_season": context['home_drtg_season'],
            "away_drtg_season": context['away_drtg_season'],
            "home_def_rank": context['home_def_rank'],
            "away_def_rank": context['away_def_rank'],
            "home_drtg_last5": context.get('home_drtg_last5'),
            "away_drtg_last5": context.get('away_drtg_last5')
        },
        "shooting": {
            "home_3pt_pct_season": context['home_3pt_pct_season'],
            "away_3pt_pct_season": context['away_3pt_pct_season'],
            "home_3pa_season": context['home_3pa_season'],
            "away_3pa_season": context['away_3pa_season'],
            "home_3pt_def_pct": context['home_3pt_def_pct'],
            "away_3pt_def_pct": context['away_3pt_def_pct'],
            "home_3pt_pct_last5": context.get('home_3pt_pct_last5'),
            "away_3pt_pct_last5": context.get('away_3pt_pct_last5')
        },
        "paint_and_rim": {
            "home_fga_season": context['home_fga_season'],
            "away_fga_season": context['away_fga_season'],
            "home_fta_season": context['home_fta_season'],
            "away_fta_season": context['away_fta_season'],
            "home_oreb_season": context['home_oreb_season'],
            "away_oreb_season": context['away_oreb_season']
        },
        "matchup_context": {
            "matchup_type": context['matchup_type'],
            "home_cluster": context['home_cluster'],
            "away_cluster": context['away_cluster'],
            "shootout_bonus": context['shootout_bonus'],
            "home_rest_days": context['home_rest_days'],
            "away_rest_days": context['away_rest_days']
        },
        "projection": {
            "model_reference_total": context['model_reference_total'],
            "home_projected": context['home_projected'],
            "away_projected": context['away_projected']
        }
    }

    # Attempt generation with retry logic
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            system_message = get_system_message(attempt)
            user_message = build_structured_request(matchup_payload, existing_writeups)

            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Fast, cost-effective model
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            # Parse response
            response_text = response.choices[0].message.content

            # Validate response (detect if AI is asking for data instead of generating)
            if is_invalid_response(response_text):
                print(f"[matchup_summary] WARNING: AI returned invalid response on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    print("[matchup_summary] Retrying with stricter prompt...")
                    continue
                else:
                    print("[matchup_summary] ERROR: AI failed to generate valid output after retries")
                    return None

            # Parse JSON response
            summary_json = json.loads(response_text)

            # Add metadata
            summary_json['game_id'] = game_id
            summary_json['home_team'] = context['home_team']
            summary_json['away_team'] = context['away_team']
            summary_json['model_reference_total'] = context['model_reference_total']
            summary_json['payload_version'] = PAYLOAD_VERSION
            summary_json['engine_version'] = ENGINE_VERSION

            print(f"[matchup_summary] ✓ Generated summary for game {game_id}")
            return summary_json

        except json.JSONDecodeError as e:
            print(f"[matchup_summary] ERROR: Invalid JSON response on attempt {attempt + 1}: {str(e)}")
            if attempt < max_attempts - 1:
                continue
            return None
        except Exception as e:
            print(f"[matchup_summary] ERROR on attempt {attempt + 1}: {str(e)}")
            if attempt < max_attempts - 1:
                continue
            return None

    return None


def get_system_message(attempt: int) -> str:
    """
    Get system message for AI request.

    On retry (attempt > 0), use stricter language to prevent asking for data.
    """
    if attempt == 0:
        return """You will be given matchup_payload and existing_writeups. Do not request more info. Return only JSON.

You are a professional NBA matchup analyst writing for adult basketball fans. Use a 5th-grade reading level for clarity, but maintain an adult tone.

CRITICAL RULES:
- You will receive all data in the matchup_payload. NEVER ask the user for more information.
- Return ONLY valid JSON. No explanations, no markdown, no preamble.
- NEVER use betting language or make picks.
- Stick strictly to sentence count requirements.
- If existing_writeups are provided, reuse those sections exactly."""
    else:
        return """STRICT MODE: You MUST return ONLY valid JSON. Do NOT ask for data. All data is provided in matchup_payload.

You are a professional NBA matchup analyst. The user has already sent you matchup_payload with all necessary data.

Your ONLY job is to:
1. Read the matchup_payload (already provided)
2. Generate the 7 required sections
3. Return valid JSON

DO NOT:
- Ask "Please send me..."
- Request additional data
- Include markdown formatting
- Add explanations outside JSON

Return ONLY the JSON object with the 7 sections."""


def build_structured_request(matchup_payload: Dict, existing_writeups: Optional[Dict] = None) -> str:
    """
    Build user message with embedded matchup payload.

    This ensures AI receives all data upfront and never needs to ask for it.
    """
    request = {
        "matchup_payload": matchup_payload,
        "existing_writeups": existing_writeups or {},
        "instructions": {
            "output_format": "Return a JSON object with these exact 7 sections",
            "sections": [
                {
                    "key": "pace_and_flow",
                    "title": "Pace & Game Flow",
                    "sentences": 5,
                    "template": [
                        "State expected pace (Fast/Normal/Slow)",
                        "Compare both teams' season pace",
                        "Compare last-5 pace trends vs season",
                        "Explain how styles interact",
                        "Describe expected shot volume & possession style"
                    ]
                },
                {
                    "key": "offensive_style",
                    "title": "Offensive Style Matchup",
                    "sentences": 5,
                    "template": [
                        "How home team scores",
                        "How away defense handles that",
                        "How away team scores",
                        "How home defense handles that",
                        "Biggest offensive advantage"
                    ]
                },
                {
                    "key": "shooting_profile",
                    "title": "Shooting & 3PT Profile",
                    "sentences": 5,
                    "template": [
                        "Home 3PT vs away 3PT defense (season)",
                        "Away 3PT vs home 3PT defense (season)",
                        "Home last-5 shooting trend",
                        "Away last-5 shooting trend",
                        "Shooting variance conclusion"
                    ]
                },
                {
                    "key": "rim_and_paint",
                    "title": "Rim Pressure & Paint Matchup",
                    "sentences": 5,
                    "template": [
                        "Which team attacks rim more",
                        "Which team protects paint better",
                        "Offensive rebounding comparison",
                        "Foul-drawing and free-throw impact",
                        "Interior advantage conclusion"
                    ]
                },
                {
                    "key": "recent_form",
                    "title": "Recent Form Check",
                    "sentences": 5,
                    "template": [
                        "Home offensive trend last 5",
                        "Away offensive trend last 5",
                        "Home defensive trend last 5",
                        "Away defensive trend last 5",
                        "How trends align with matchup"
                    ]
                },
                {
                    "key": "volatility_profile",
                    "title": "Volatility Profile",
                    "sentences": 5,
                    "template": [
                        "Label volatility (Stable/Moderately Swingy/High-Variance)",
                        "Explain volatility driver",
                        "How quickly game can flip",
                        "Scoring profile consistency",
                        "Unpredictability summary"
                    ]
                },
                {
                    "key": "matchup_dna_summary",
                    "title": "Matchup DNA Summary",
                    "sentences": "8-10",
                    "template": [
                        "Tie together all sections",
                        "Reference matchup type from payload",
                        "Describe matchup identity",
                        "NO picks, NO betting advice",
                        "Final sentence describes game character"
                    ]
                }
            ],
            "writing_rules": [
                "5th-grade reading level (short sentences, simple words)",
                "Adult tone (no condescension, professional basketball analysis)",
                "NO betting language ('locks', 'hammer', 'sharp', 'best bet', etc.)",
                "NO picks or recommendations",
                "NEVER mention betting lines",
                "Use team abbreviations from matchup_payload.teams",
                "Focus on explaining the matchup, not predicting outcomes"
            ],
            "reuse_existing": "If existing_writeups contains a section, copy it exactly. Only generate missing sections."
        }
    }

    return json.dumps(request, indent=2)


def is_invalid_response(response_text: str) -> bool:
    """
    Detect if AI returned an invalid response (asking for data instead of generating).

    Returns True if response is invalid and should be retried.
    """
    # Check for common phrases that indicate AI is asking for data
    invalid_phrases = [
        "please send",
        "send me",
        "provide the",
        "i need",
        "could you provide",
        "share the data",
        "missing data",
        "need more information"
    ]

    lower_response = response_text.lower()

    for phrase in invalid_phrases:
        if phrase in lower_response:
            return True

    # Check if response is suspiciously short (likely not a full summary)
    if len(response_text) < 500:
        return True

    return False


def build_llm_prompt(context: Dict) -> str:
    """
    Build the LLM prompt with strict instructions and context data.

    This prompt enforces:
    - Exact sentence counts for each section
    - 5th-grade reading level
    - No betting language
    - Structured JSON output
    """
    prompt = f"""Generate a structured matchup breakdown for {context['away_team']} @ {context['home_team']}.

CONTEXT DATA:
- Game Pace: {context['game_pace']} (Home: {context['home_pace_season']}, Away: {context['away_pace_season']})
- Matchup Type: {context['matchup_type']}
- Home Team Cluster: {context['home_cluster']}
- Away Team Cluster: {context['away_cluster']}

SEASON STATS:
Home ({context['home_team']}):
- PPG: {context['home_ppg_season']} | ORTG: {context['home_ortg_season']} | DRTG: {context['home_drtg_season']} | Def Rank: #{context['home_def_rank']}
- 3PT%: {context['home_3pt_pct_season']}% ({context['home_3pa_season']} attempts) | Allows: {context['home_3pt_def_pct']}%
- FGA: {context['home_fga_season']} | FTA: {context['home_fta_season']} | OREB: {context['home_oreb_season']}

Away ({context['away_team']}):
- PPG: {context['away_ppg_season']} | ORTG: {context['away_ortg_season']} | DRTG: {context['away_drtg_season']} | Def Rank: #{context['away_def_rank']}
- 3PT%: {context['away_3pt_pct_season']}% ({context['away_3pa_season']} attempts) | Allows: {context['away_3pt_def_pct']}%
- FGA: {context['away_fga_season']} | FTA: {context['away_fta_season']} | OREB: {context['away_oreb_season']}

LAST 5 TRENDS:
Home ({context['home_team']}): PPG {context.get('home_ppg_last5', 'N/A')} | ORTG {context.get('home_ortg_last5', 'N/A')} | DRTG {context.get('home_drtg_last5', 'N/A')} | 3PT% {context.get('home_3pt_pct_last5', 'N/A')}%
Away ({context['away_team']}): PPG {context.get('away_ppg_last5', 'N/A')} | ORTG {context.get('away_ortg_last5', 'N/A')} | DRTG {context.get('away_drtg_last5', 'N/A')} | 3PT% {context.get('away_3pt_pct_last5', 'N/A')}%

OTHER CONTEXT:
- Rest: Home {context['home_rest_days']} days, Away {context['away_rest_days']} days
- Shootout Bonus: {context['shootout_bonus']} pts
- Model Projection: Home {context['home_projected']}, Away {context['away_projected']}

STRICT OUTPUT REQUIREMENTS:

Return a JSON object with these exact fields:

{{
  "pace_and_flow": {{
    "title": "Pace & Game Flow",
    "text": "EXACTLY 5 sentences here..."
  }},
  "offensive_style": {{
    "title": "Offensive Style Matchup",
    "text": "EXACTLY 5 sentences here..."
  }},
  "shooting_profile": {{
    "title": "Shooting & 3PT Profile",
    "text": "EXACTLY 5 sentences here..."
  }},
  "rim_and_paint": {{
    "title": "Rim Pressure & Paint Matchup",
    "text": "EXACTLY 5 sentences here..."
  }},
  "recent_form": {{
    "title": "Recent Form Check",
    "text": "EXACTLY 5 sentences here..."
  }},
  "volatility_profile": {{
    "title": "Volatility Profile",
    "text": "EXACTLY 5 sentences here..."
  }},
  "matchup_dna_summary": {{
    "title": "Matchup DNA Summary",
    "text": "8-10 sentences of big-picture explanation..."
  }}
}}

WRITING RULES:
1. 5th-grade reading level (short sentences, simple words)
2. Adult tone (no condescension, professional basketball analysis)
3. NO betting language ("locks", "hammer", "sharp", "best bet", etc.)
4. NO picks or recommendations
5. NEVER mention betting lines
6. Use team abbreviations: {context['home_team']} and {context['away_team']}
7. Focus on explaining the matchup, not predicting outcomes

SECTION TEMPLATES:

1. Pace & Game Flow (5 sentences):
   - Sentence 1: State expected pace (Fast/Normal/Slow)
   - Sentence 2: Compare both teams' season pace
   - Sentence 3: Compare last-5 pace trends vs season
   - Sentence 4: Explain how styles interact
   - Sentence 5: Describe expected shot volume & possession style

2. Offensive Style Matchup (5 sentences):
   - Sentence 1: How home team scores
   - Sentence 2: How away defense handles that
   - Sentence 3: How away team scores
   - Sentence 4: How home defense handles that
   - Sentence 5: Biggest offensive advantage

3. Shooting & 3PT Profile (5 sentences):
   - Sentence 1: Home 3PT vs away 3PT defense (season)
   - Sentence 2: Away 3PT vs home 3PT defense (season)
   - Sentence 3: Home last-5 shooting trend
   - Sentence 4: Away last-5 shooting trend
   - Sentence 5: Shooting variance conclusion

4. Rim Pressure & Paint Matchup (5 sentences):
   - Sentence 1: Which team attacks rim more
   - Sentence 2: Which team protects paint better
   - Sentence 3: Offensive rebounding comparison
   - Sentence 4: Foul-drawing and free-throw impact
   - Sentence 5: Interior advantage conclusion

5. Recent Form Check (5 sentences):
   - Sentence 1: Home offensive trend last 5
   - Sentence 2: Away offensive trend last 5
   - Sentence 3: Home defensive trend last 5
   - Sentence 4: Away defensive trend last 5
   - Sentence 5: How trends align with matchup

6. Volatility Profile (5 sentences):
   - Sentence 1: Label volatility (Stable/Moderately Swingy/High-Variance)
   - Sentence 2: Explain volatility driver
   - Sentence 3: How quickly game can flip
   - Sentence 4: Scoring profile consistency
   - Sentence 5: Unpredictability summary

7. Matchup DNA Summary (8-10 sentences):
   - Tie together all sections
   - Reference matchup type: "{context['matchup_type']}"
   - Describe matchup identity
   - NO picks, NO betting advice
   - Final sentence describes game character

Generate the JSON now."""

    return prompt
