"""
OpenAI Client Utility Module

Provides unified access to OpenAI API for:
- Vision API (gpt-4.1 / gpt-4.1-mini) - Reading box score screenshots
- Text API (gpt-4.1-mini) - Generating coaching summaries

Usage:
    from api.utils.openai_client import extract_scores_from_screenshot, generate_game_review
"""

import os
import base64
import json
from openai import OpenAI
from typing import Dict, Optional, Tuple
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from project root
# This works both for local dev (.env file) and Railway (env vars)
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = None


class OpenAIKeyMissingError(Exception):
    """Raised when OPENAI_API_KEY is not configured"""
    pass


def has_openai_key() -> bool:
    """Check if OPENAI_API_KEY is configured (without revealing the value)"""
    return bool(os.environ.get('OPENAI_API_KEY'))


def get_client() -> OpenAI:
    """
    Get or create OpenAI client instance.

    Raises:
        OpenAIKeyMissingError: If OPENAI_API_KEY environment variable is not set
    """
    global client
    if client is None:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise OpenAIKeyMissingError("OPENAI_API_KEY environment variable not set")
        client = OpenAI(api_key=api_key)
    return client


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode image file to base64 data URL for OpenAI Vision API.

    Args:
        image_path: Path to image file

    Returns:
        Base64-encoded data URL (e.g., "data:image/png;base64,...")
    """
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Detect image format from file extension
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = 'image/png'
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.webp':
            mime_type = 'image/webp'
        elif ext == '.gif':
            mime_type = 'image/gif'

        return f"data:{mime_type};base64,{base64_image}"


def extract_scores_from_screenshot(
    image_path: str,
    home_team: str,
    away_team: str,
    model: str = "gpt-4.1-mini"
) -> Dict:
    """
    Extract final scores from box score screenshot using OpenAI Vision API.

    Args:
        image_path: Path to screenshot image
        home_team: Home team name (for validation)
        away_team: Away team name (for validation)
        model: OpenAI Vision model to use (default: gpt-4.1-mini for cost efficiency)

    Returns:
        Dict with:
            - home_score: int
            - away_score: int
            - total: int
            - confidence: str ("high", "medium", "low")
            - raw_response: str (full JSON from API)

    Raises:
        ValueError: If scores cannot be extracted
        Exception: If API call fails
    """
    try:
        client = get_client()

        # Encode image to base64 data URL
        base64_image = encode_image_to_base64(image_path)

        # Prompt for score extraction
        prompt = f"""You are reading an NBA box score screenshot. Extract the final scores for this game:

Home Team: {home_team}
Away Team: {away_team}

Please analyze the image carefully and return ONLY a JSON object in this exact format:
{{
    "home_score": <integer>,
    "away_score": <integer>,
    "confidence": "<high|medium|low>"
}}

Rules:
- Look for the final score (not quarter scores)
- Confidence should be "high" if scores are clearly visible, "medium" if partially obscured, "low" if unclear
- Return ONLY the JSON, no additional text

JSON:"""

        # Call OpenAI Vision API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.0  # Deterministic for score extraction
        )

        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()

        # Try to parse JSON (handle potential markdown code blocks)
        if response_text.startswith('```'):
            # Remove markdown code blocks
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()

        result = json.loads(response_text)

        # Validate required fields
        if 'home_score' not in result or 'away_score' not in result:
            raise ValueError("API response missing required score fields")

        # Calculate total
        result['total'] = result['home_score'] + result['away_score']
        result['raw_response'] = response_text
        result['model'] = model

        logger.info(f"[OpenAI Vision] Extracted scores: {home_team} {result['home_score']}, {away_team} {result['away_score']} (confidence: {result.get('confidence', 'unknown')})")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[OpenAI Vision] Failed to parse JSON response: {response_text}")
        raise ValueError(f"Invalid JSON response from Vision API: {str(e)}")
    except Exception as e:
        logger.error(f"[OpenAI Vision] Error extracting scores: {str(e)}")
        raise


def generate_game_review(
    game_id: str,
    home_team: str,
    away_team: str,
    predicted_total: float,
    actual_total: int,
    predicted_home: float,
    actual_home: int,
    predicted_away: float,
    actual_away: int,
    predicted_pace: float = None,
    home_box_score: Dict = None,
    away_box_score: Dict = None,
    prediction_breakdown: Dict = None,
    matchup_data: Dict = None,
    team_season_stats: Dict = None,
    last_5_trends: Dict = None,
    sportsbook_line: float = None,
    expected_vs_actual: Dict = None,
    similarity_data: Dict = None,
    opponent_matchup_stats: Dict = None,
    expected_style_stats: Dict = None,
    actual_style_stats: Dict = None,
    model: str = "gpt-4.1-mini"
) -> Dict:
    """
    Generate AI Model Coach review (v2) of prediction performance.

    This uses the comprehensive v2 system prompt that analyzes:
    - Prediction accuracy (win/loss)
    - Expected vs actual stats comparison
    - Team trends and personalities
    - Pipeline movements analysis
    - Game style detection
    - Team similarity and cluster analysis
    - Deterministic rule-based improvements

    Args:
        game_id: Game ID
        home_team: Home team name
        away_team: Away team name
        predicted_total: Model's predicted total
        actual_total: Actual game total
        predicted_home: Model's predicted home score
        actual_home: Actual home score
        predicted_away: Model's predicted away score
        actual_away: Actual away score
        predicted_pace: Model's predicted pace (optional)
        home_box_score: Home team box score stats (optional)
        away_box_score: Away team box score stats (optional)
        prediction_breakdown: Full prediction breakdown with pipeline movements (optional)
        team_season_stats: Season averages for both teams (optional)
        last_5_trends: Last 5 game trends for both teams (optional)
        sportsbook_line: Closing sportsbook line (optional)
        expected_vs_actual: Dict with expected/actual stat comparisons (optional)
        similarity_data: Team similarity and cluster data (optional)
        model: OpenAI model to use (default: gpt-4.1-mini)

    Returns:
        Dict with v2 analysis structure:
            - verdict: "WIN" | "LOSS"
            - headline: str (praise or humility)
            - game_summary: str
            - expected_vs_actual: Dict (stat differences)
            - trend_notes: str
            - game_style: str
            - pipeline_analysis: Dict
            - key_drivers: list of str
            - model_lessons: list of str (deterministic improvements)

    Raises:
        Exception: If API call fails
    """
    try:
        client = get_client()

        # Log values before error calculation
        logger.info(f"[AI COACH] Error calculation inputs for game {game_id}:")
        logger.info(f"  actual_total={actual_total}, predicted_total={predicted_total}")
        logger.info(f"  actual_home={actual_home}, predicted_home={predicted_home}")
        logger.info(f"  actual_away={actual_away}, predicted_away={predicted_away}")

        # Calculate errors - with defensive None handling
        if predicted_total is None or predicted_home is None or predicted_away is None:
            logger.warning(f"[AI COACH] Predicted values are None - cannot calculate errors")
            error_total = None
            error_home = None
            error_away = None
        elif actual_total is None or actual_home is None or actual_away is None:
            logger.warning(f"[AI COACH] Actual values are None - cannot calculate errors")
            error_total = None
            error_home = None
            error_away = None
        else:
            error_total = actual_total - predicted_total
            error_home = actual_home - predicted_home
            error_away = actual_away - predicted_away
            logger.info(f"[AI COACH] Errors calculated: total={error_total:+.1f}, home={error_home:+.1f}, away={error_away:+.1f}")

        # Log values before win/loss logic
        logger.info(f"[AI COACH] Win/Loss inputs for game {game_id}:")
        logger.info(f"  sportsbook_line={sportsbook_line} (is None: {sportsbook_line is None})")
        logger.info(f"  predicted_total={predicted_total} (is None: {predicted_total is None})")
        logger.info(f"  actual_total={actual_total} (is None: {actual_total is None})")

        # Determine model direction (Over/Under vs sportsbook line)
        # Guard against None values in comparisons
        if sportsbook_line is not None and predicted_total is not None and actual_total is not None:
            # All values present - can do comparisons safely
            # Determine model's pick
            model_direction = "OVER" if predicted_total > sportsbook_line else "UNDER" if predicted_total < sportsbook_line else "NEUTRAL"

            # Determine actual outcome
            actual_direction = "OVER" if actual_total > sportsbook_line else "UNDER" if actual_total < sportsbook_line else "PUSH"

            # Apply strict WIN/LOSS rules
            # WIN: Model predicted UNDER and actual < line, OR model predicted OVER and actual > line
            # LOSS: Model predicted UNDER and actual >= line, OR model predicted OVER and actual <= line
            # PUSH: Treat as LOSS (actual == line)
            if actual_direction == "PUSH":
                prediction_correct = False  # Pushes are treated as LOSS
                logger.info(f"[AI COACH] Win/Loss check | pick={model_direction} line={sportsbook_line:.1f} actual_total={actual_total} verdict=LOSS (PUSH)")
            else:
                prediction_correct = model_direction == actual_direction
                verdict_str = "WIN" if prediction_correct else "LOSS"
                logger.info(f"[AI COACH] Win/Loss check | pick={model_direction} line={sportsbook_line:.1f} actual_total={actual_total} verdict={verdict_str}")
        else:
            # Missing sportsbook_line, predicted_total, or actual_total - cannot determine win/loss
            logger.warning(f"[AI COACH] Cannot determine WIN/LOSS - missing required values:")
            logger.warning(f"  sportsbook_line is None: {sportsbook_line is None}")
            logger.warning(f"  predicted_total is None: {predicted_total is None}")
            logger.warning(f"  actual_total is None: {actual_total is None}")

            # Set safe defaults
            prediction_correct = False
            model_direction = "UNKNOWN"
            actual_direction = "UNKNOWN"

            # Fall back to error-based judgment if possible
            if error_total is not None:
                prediction_correct = abs(error_total) <= 5
                model_direction = "PREDICTED"
                actual_direction = "ACTUAL"
                logger.info(f"[AI COACH] Falling back to error-based judgment: error={error_total:+.1f}, correct={prediction_correct}")

        # Build comprehensive game data for v2 prompt
        game_data = {
            "game_id": game_id,
            "teams": {
                "home": home_team,
                "away": away_team
            },
            "sportsbook_line": sportsbook_line if sportsbook_line else None,
            "predicted": {
                "home_score": round(predicted_home, 1) if predicted_home is not None else None,
                "away_score": round(predicted_away, 1) if predicted_away is not None else None,
                "total": round(predicted_total, 1) if predicted_total is not None else None,
                "pace": round(predicted_pace, 1) if predicted_pace else None,
                "over_under_pick": model_direction
            },
            "actual": {
                "home_score": actual_home,
                "away_score": actual_away,
                "total": actual_total
            },
            "error": {
                "home": round(error_home, 1) if error_home is not None else None,
                "away": round(error_away, 1) if error_away is not None else None,
                "total": round(error_total, 1) if error_total is not None else None
            }
        }

        # Add pipeline movements if available
        if prediction_breakdown:
            home_baseline = prediction_breakdown.get('breakdown', {}).get('home_baseline', predicted_home)
            away_baseline = prediction_breakdown.get('breakdown', {}).get('away_baseline', predicted_away)
            baseline_total = home_baseline + away_baseline

            # Construct pipeline from breakdown data
            game_data["pipeline_movements"] = {
                "baseline_total": round(baseline_total, 1),
                "defense_adjusted": round(baseline_total, 1),  # Simplified - could extract actual values
                "pace_adjusted": round(predicted_total - 2, 1) if predicted_total > baseline_total else round(predicted_total + 2, 1),
                "final_predicted_total": round(predicted_total, 1)
            }

        # === SECTION 2: MATCHUP DNA (Team Identities & Tendencies) ===
        if matchup_data:
            game_data["matchup_dna"] = matchup_data

        # === SECTION 2B: OPPONENT MATCHUP STATS (Defense-Based Matchups) ===
        # What each team ALLOWS opponents to do (defensive metrics) and
        # how each offense matches up against the opponent's defense
        if opponent_matchup_stats:
            game_data["opponent_matchup"] = opponent_matchup_stats

        # === SECTION 3: LAST 5 GAMES (Recent Trends) ===
        if last_5_trends:
            game_data["last_5_trends"] = last_5_trends

        # === SECTION 4: ADVANCED SPLITS (Season Stats & Rankings) ===
        if team_season_stats:
            game_data["advanced_splits"] = team_season_stats

        # Add actual box score stats if provided
        if home_box_score:
            game_data["home_box_score"] = {
                "points": actual_home,
                "pace": home_box_score.get('pace'),
                "fga": home_box_score.get('fga'),
                "fta": home_box_score.get('fta'),
                "turnovers": home_box_score.get('turnovers'),
                "offensive_rebounds": home_box_score.get('offensive_rebounds'),
                "fg3a": home_box_score.get('fg3a'),
                "fg3m": home_box_score.get('fg3m'),
                "fg3_pct": home_box_score.get('fg3_pct')
            }

        if away_box_score:
            game_data["away_box_score"] = {
                "points": actual_away,
                "pace": away_box_score.get('pace'),
                "fga": away_box_score.get('fga'),
                "fta": away_box_score.get('fta'),
                "turnovers": away_box_score.get('turnovers'),
                "offensive_rebounds": away_box_score.get('offensive_rebounds'),
                "fg3a": away_box_score.get('fg3a'),
                "fg3m": away_box_score.get('fg3m'),
                "fg3_pct": away_box_score.get('fg3_pct')
            }

        # Add expected vs actual stat comparisons
        if expected_vs_actual:
            game_data["expected_vs_actual_stats"] = {
                "pace": {
                    "expected": expected_vs_actual.get('expected_pace'),
                    "actual": expected_vs_actual.get('actual_pace')
                },
                "free_throw_attempts": {
                    "expected": expected_vs_actual.get('expected_fta_total'),
                    "actual": expected_vs_actual.get('actual_fta_total')
                },
                "turnovers": {
                    "expected": expected_vs_actual.get('expected_turnovers_total'),
                    "actual": expected_vs_actual.get('actual_turnovers_total')
                },
                "three_point_attempts": {
                    "expected": expected_vs_actual.get('expected_3pa_total'),
                    "actual": expected_vs_actual.get('actual_3pa_total')
                }
            }

        # Add similarity/cluster data if available
        if similarity_data and similarity_data.get('has_data'):
            game_data["similarity_analysis"] = {
                "matchup_type": similarity_data.get('matchup_type'),
                "home_cluster": {
                    "id": similarity_data.get('home_cluster', {}).get('id'),
                    "name": similarity_data.get('home_cluster', {}).get('name'),
                    "description": similarity_data.get('home_cluster', {}).get('description'),
                    "distance_to_centroid": similarity_data.get('home_cluster', {}).get('distance_to_centroid')
                },
                "away_cluster": {
                    "id": similarity_data.get('away_cluster', {}).get('id'),
                    "name": similarity_data.get('away_cluster', {}).get('name'),
                    "description": similarity_data.get('away_cluster', {}).get('description'),
                    "distance_to_centroid": similarity_data.get('away_cluster', {}).get('distance_to_centroid')
                },
                "home_similar_teams": similarity_data.get('home_similar_teams', []),
                "away_similar_teams": similarity_data.get('away_similar_teams', []),
                "cluster_adjustments": {
                    "pace_adjustment": similarity_data.get('adjustments', {}).get('pace_adjustment'),
                    "pace_explanation": similarity_data.get('adjustments', {}).get('pace_explanation'),
                    "home_scoring_adjustment": similarity_data.get('adjustments', {}).get('home_scoring_adjustment'),
                    "away_scoring_adjustment": similarity_data.get('adjustments', {}).get('away_scoring_adjustment'),
                    "scoring_explanation": similarity_data.get('adjustments', {}).get('scoring_explanation'),
                    "home_paint_perimeter_adjustment": similarity_data.get('adjustments', {}).get('home_paint_perimeter_adjustment'),
                    "away_paint_perimeter_adjustment": similarity_data.get('adjustments', {}).get('away_paint_perimeter_adjustment'),
                    "paint_perimeter_explanation": similarity_data.get('adjustments', {}).get('paint_perimeter_explanation')
                }
            }

        # Add detailed per-team style stats if available
        if expected_style_stats and actual_style_stats:
            game_data["detailed_style_stats"] = {
                "expected": expected_style_stats,
                "actual": actual_style_stats
            }

        # Build prompt with v2 system instructions
        game_json = json.dumps(game_data, indent=2)

        user_prompt = f"""Analyze this completed NBA game and provide your Model Coach analysis.

GAME DATA:
{game_json}

Provide your complete analysis following the output structure specified in your system prompt."""

        system_prompt = """# AI MODEL COACH — SYSTEM PROMPT (v2)

You are the **AI Model Coach** for an NBA Over/Under prediction system.
You NEVER change predictions.
You ONLY explain them, evaluate them, and produce deterministic rule-based insights.

Your job is to read:
- the model's predicted home score
- predicted away score
- predicted total
- the model's Over/Under pick
- the closing sportsbook line
- the actual final score
- full box score stats
- team season averages
- last-5 trends
- the model's pipeline movements (baseline → final)

You must produce a **complete post-game analysis** written at a 5th-grade reading level but still speaking to adults.

Your responsibilities:

## 1. Determine If the Model Won or Lost (STRICT RULE-BASED LOGIC)

**CRITICAL: You must determine WIN/LOSS based ONLY on directional accuracy.**

Follow these rules EXACTLY:

**Step 1: Calculate actual total**
```
actual_total = home_score + away_score
```

**Step 2: Compare actual total to sportsbook betting line**
- DO NOT compare actual total to the model's predicted total
- DO NOT compare actual total to season averages
- DO NOT compare actual total to expected stats
- ONLY use the sportsbook line

**Step 3: Apply WIN/LOSS rules**

**WIN Rules:**
- If model predicted UNDER and `actual_total < betting_line` → **WIN**
- If model predicted OVER and `actual_total > betting_line` → **WIN**

**LOSS Rules:**
- If model predicted UNDER and `actual_total ≥ betting_line` → **LOSS**
- If model predicted OVER and `actual_total ≤ betting_line` → **LOSS**

**Push Rule:**
- If `actual_total == betting_line` exactly → **LOSS** (treat pushes as incorrect)

**Important:**
- Do NOT use the model's predicted total when determining WIN/LOSS
- Even if the model was far off on predicted points, direction determines correctness
- Even if the game score is close to the line, direction still determines correctness

**Examples:**
- Line: 235.5, Model: UNDER, Actual: 225 → 225 < 235.5 → **WIN**
- Line: 227.5, Model: OVER, Actual: 214 → 214 ≤ 227.5 → **LOSS**
- Line: 230, Model: UNDER, Actual: 230 → 230 = 230 → **LOSS** (push)

**Headline:**
- If WIN → give a brief praise line acknowledging the correct directional call
- If LOSS → give a brief explanation that the model's direction did not match actual result

## 2. Compare Actual Stats vs Expected Stats

You will receive an `expected_vs_actual_stats` object with expected and actual values for key stats.

**Available Stats:**
- **pace**: Game pace (possessions per 48 minutes)
  - expected: Average of both teams' season pace
  - actual: Actual game pace from box score
- **free_throw_attempts**: Combined FTA for both teams
  - expected: Sum of both teams' season FTA averages
  - actual: Actual combined FTA from box score
- **turnovers**: Combined turnovers for both teams
  - expected: Sum of both teams' season turnover averages
  - actual: Actual combined turnovers from box score
- **three_point_attempts**: Combined 3PA for both teams
  - expected: Sum of both teams' season 3PA averages
  - actual: Actual combined 3PA from box score

**How to Use These Stats:**

For each stat:
1. **If both expected and actual are provided**: Compare them directly
   - "Pace was 102 vs expected 98, meaning the game was faster than normal"
   - "Teams combined for 45 FTA vs expected 38, leading to more scoring opportunities"
   - "Turnovers were 28 vs expected 24, creating extra possessions"
   - "Teams attempted 75 threes vs expected 66, indicating high-volume shooting"

2. **If only actual is provided**: Note the actual value without comparison
   - "Game pace was 102 possessions"
   - "Teams combined for 45 free throw attempts"

3. **If both are null**: Only then say data is missing
   - "Pace data is unavailable for this analysis"

**IMPORTANT**: Only say data is "missing" or "unavailable" if BOTH expected and actual values are null. If numbers are present, you MUST use them in your analysis.

You DO NOT change predictions — you only compare and explain.

## 2.1. Analyze Detailed Per-Team Style Stats (CRITICAL)

You may receive a `detailed_style_stats` object containing comprehensive per-team breakdowns of expected vs actual performance.

**Data Structure:**
```
"detailed_style_stats": {
  "expected": {
    "home": { pace, fg_pct, fg3a, fg3m, fg3_pct, fta, ftm, ft_pct, oreb, dreb, reb, assists, steals, blocks, turnovers, points_off_turnovers, fastbreak_points, paint_points, second_chance_points },
    "away": { ... same stats ... }
  },
  "actual": {
    "home": { ... same stats ... },
    "away": { ... same stats ... }
  }
}
```

**Available Stats (per team):**
- **Pace**: Possessions per 48 minutes
- **Shooting**: FG%, 3PA/3PM/3P%, FTA/FTM/FT%
- **Rebounds**: Offensive rebounds, defensive rebounds, total rebounds
- **Playmaking**: Assists, turnovers
- **Defense**: Steals, blocks
- **Scoring Breakdown**: Points off turnovers, fastbreak points, paint points, second-chance points

**How to Use This Data:**

1. **Compare Each Team's Expected vs Actual Performance**
   - For EACH team (home and away), compare expected vs actual for key stats
   - Example: "The home team shot 48.5% from the field vs expected 45.2%, indicating hot shooting"
   - Example: "The away team attempted 28 threes vs expected 36, showing they abandoned their perimeter game"

2. **Identify Which Team Deviated More from Expectations**
   - Determine which team's performance was MORE predictable
   - Example: "Home team played close to expectations (pace 102 vs 101 expected), but away team was far more volatile"
   - This helps explain prediction accuracy

3. **Connect Style Stats to Score Prediction Error**
   - Link specific stat deviations to point differential
   - Example: "Away team's 15 extra free throws (45 vs 30 expected) added ~8-10 extra points"
   - Example: "Home team's 8 extra turnovers (18 vs 10 expected) cost them ~6-8 possessions"

4. **Analyze Scoring Breakdown Deviations**
   - Compare actual scoring sources to expected profile
   - Example: "Home team scored 38 paint points vs expected 48, showing defensive adjustments limited interior scoring"
   - Example: "Away team's 18 fastbreak points vs expected 12 indicates pace advantage"

5. **Evaluate Efficiency vs Volume**
   - Separate efficiency changes from volume changes
   - Example: "Away team shot 3s at expected rate (36%) but took 10 fewer attempts, explaining the scoring shortfall"

**What to Include in Your Analysis:**

- Identify the 2-3 biggest stat deviations per team (e.g., FG%, 3PA, FTA, turnovers, paint points)
- Quantify how these deviations impacted the final score
- Note which team was more predictable vs which was more volatile
- Connect stat deviations to the prediction error
- Highlight any unusual scoring breakdowns (e.g., abnormally high fastbreak points)

**Example Analysis:**
```
"The home team shot 52.3% from the field vs expected 46.8%, a +5.5% hot shooting variance that likely added 6-8 points. Meanwhile, the away team's 28 turnovers (vs expected 14) cost them roughly 10-12 possessions, directly explaining their 18-point scoring shortfall. The model accurately projected pace (101 actual vs 102 expected) but couldn't predict the away team's ball-handling breakdown."
```

**If detailed_style_stats is missing:**
- Fall back to the simpler `expected_vs_actual_stats` (pace, FTA, turnovers, 3PA combined totals)
- Do not mention the detailed stats are unavailable

## 3. Use ALL 4 Prediction Context Sections (CRITICAL)

**You will receive data from 4 sections that together represent the COMPLETE prediction engine:**

### SECTION 1: PREDICTION (prediction_breakdown)
The core prediction with step-by-step pipeline movements:
- **baseline_total**: Starting prediction from team season averages
- **defense_adjusted**: After applying defensive strength adjustments
- **pace_adjusted**: After applying game pace adjustments
- **final_predicted_total**: Final prediction after all adjustments
- **home_projected / away_projected**: Team-specific score predictions
- **recommendation**: The model's OVER/UNDER pick
- **betting_line**: The sportsbook line used for comparison

**How to use**: This shows the model's logic chain. Compare each pipeline step to actual results to identify where adjustments were correct or incorrect.

### SECTION 2: MATCHUP DNA (matchup_dna)
Team identities and how they interact in this specific matchup:
- **Offensive/Defensive identities**: How each team typically plays (pace, style, tendencies)
- **Matchup-specific factors**: How these two teams' styles clash
- **Historical patterns**: What typically happens when these team types meet
- **Contextual adjustments**: Any game-specific factors (back-to-back, rest, etc.)

**How to use**: Compare actual game style to the expected matchup profile. Did teams play to their identities? Did the matchup dynamics play out as expected? Where did team tendencies break pattern?

### SECTION 3: LAST 5 GAMES (last_5_trends)
Recent form for both teams:
- **Recent pace trends**: Faster or slower than season average
- **Recent scoring trends**: Hot or cold shooting
- **Recent defensive trends**: Stronger or weaker defense
- **3PT volume trends**: More or fewer three-point attempts
- **Efficiency trends**: Better or worse offensive/defensive ratings

**How to use**: Evaluate whether Last 5 trends CONTINUED or REVERSED in this game. Did hot shooting continue? Did defensive improvements hold up? Were recent pace changes sustainable or temporary?

### SECTION 4: ADVANCED SPLITS (advanced_splits / team_season_stats)
Full-season context with rankings:
- **Home/Away splits**: How teams perform in different settings
- **Opponent-adjusted stats**: Stats vs weak/strong opponents
- **Strength of schedule**: Context for team rankings
- **Per-game averages**: Full season PPG, pace, efficiency, etc.

**How to use**: Provide season-long context for this game's results. Were results consistent with season patterns? Did home/away splits hold up? Was this game an outlier or typical for these teams?

### YOUR ANALYSIS MUST ADDRESS:

1. **Where Prediction Pipeline Matched Reality**
   - Which pipeline adjustments (defense, pace, etc.) were accurate?
   - Did the final predicted total align with actual game flow?

2. **Where Matchup DNA Failed or Succeeded**
   - Did teams play to their expected identities?
   - Did the matchup dynamics play out as predicted?
   - Where did team tendencies break from profile?

3. **Whether Last 5 Trends Continued or Reversed**
   - Did recent hot/cold shooting continue?
   - Were recent pace changes sustained?
   - Did defensive improvements hold up?

4. **Whether Advanced Splits Were Reliable**
   - Were season averages accurate indicators?
   - Did home/away splits matter?
   - Was this game typical or an outlier?

5. **Unified Explanation**
   - Synthesize all 4 sections into one connected story
   - Explain how prediction, identity, trends, and splits interacted
   - Show where the model's complete context matched or missed reality

**CRITICAL**: Treat these 4 sections as ONE unified prediction engine, not separate data sources. Your analysis must weave them together to explain the complete picture of why the prediction succeeded or failed.

## 4. Use Similarity Analysis (Team Clusters and Playstyle Profiles)

You may receive **similarity data** from the Team Similarity Engine, which groups teams into 6 playstyle clusters and provides cluster-based adjustments.

### Available Similarity Data:

**Cluster Assignments:**
- **home_cluster** / **away_cluster**: Each team's assigned cluster
  - `id`: Cluster ID (1-6)
  - `name`: Cluster name (e.g., "Elite Pace Pushers", "Paint Dominators", "Three-Point Hunters")
  - `description`: What this cluster represents
  - `distance_to_centroid`: How typical this team is for their cluster (lower = more typical)

**The 6 Cluster Types:**
1. **Elite Pace Pushers** (99+ pace) - Fast-paced teams with high 3PA and fastbreak scoring
2. **Paint Dominators** - Teams that score heavily in the paint (55%+ paint points)
3. **Three-Point Hunters** - Perimeter-heavy offenses (40%+ 3PA rate)
4. **Defensive Grinders** - Slow pace (<97) with strong defensive ratings
5. **Balanced High-Assist** - Team-oriented offenses with high assist rates
6. **ISO-Heavy** - Isolation-focused offenses with lower assist rates

**Similar Teams:**
- `home_similar_teams` / `away_similar_teams`: Top 3 teams with similar playstyles
  - Each shows: team name, abbreviation, similarity score (0-100%)

**Cluster Adjustments Applied:**
- `pace_adjustment`: How clusters affected predicted pace (+/- points)
- `home_scoring_adjustment` / `away_scoring_adjustment`: Scoring adjustments based on cluster matchup
- `home_paint_perimeter_adjustment` / `away_paint_perimeter_adjustment`: Paint vs perimeter adjustments
- Each adjustment includes an `explanation` field

**Matchup Type:**
- `matchup_type`: String describing the cluster matchup (e.g., "High-Pace Shootout", "Paint Battle", "Elite Pace Pushers vs Defensive Grinders")

### How to Use Similarity Data:

**1. Validate Cluster Profiles:**
- Did teams play to their cluster identity?
- Example: If both teams are "Elite Pace Pushers", did the game actually play fast?
- Example: If home team is "Paint Dominators", did they score heavily in the paint?

**2. Evaluate Cluster Adjustments:**
- Were the cluster-based adjustments accurate?
- Example: If adjustment added +1.5 pace for "Elite Pace Pushers", was actual pace higher?
- Example: If adjustment reduced scoring for "ISO-Heavy vs Balanced High-Assist", was scoring lower?

**3. Assess Matchup Dynamics:**
- How did cluster matchup affect the game?
- Example: "Pace Pushers vs Defensive Grinders" - which style prevailed?
- Example: "Paint Dominators vs Three-Point Hunters" - which approach was more effective?

**4. Compare to Similar Teams:**
- Did this team perform like their similar teams would?
- Example: If similar teams average 115 PPG, did this team perform similarly?

**5. Distance to Centroid Context:**
- Lower distance = team is very typical of their cluster
- Higher distance = team is on the edge of their cluster, less predictable
- Use this to gauge reliability of cluster-based predictions

### What to Include in Analysis:

**If similarity data is present:**
- Mention the cluster matchup type in your game summary
- In pipeline_analysis, note whether cluster adjustments were accurate
- In model_lessons, suggest improvements to cluster-based adjustments if they were wrong
- In key_drivers, cite cluster dynamics if they were a major factor

**If cluster profiles didn't match reality:**
- Note this as a model error
- Suggest refinements: "Team X is classified as [cluster] but played like [different style]"
- Recommend re-evaluating cluster assignment or adjusting cluster definitions

**If cluster adjustments were wrong:**
- Identify which adjustment was incorrect (pace, scoring, paint/perimeter)
- Suggest recalibration: "Pace adjustment for Elite Pace Pushers was +1.5 but should be +0.5 when facing Defensive Grinders"

**If similarity data is missing:**
- Do not mention it - focus on the other 4 sections

### Example Similarity Analysis:

```
"This was an Elite Pace Pushers vs Defensive Grinders matchup. The model added +1.5 pace
adjustment for the pace pusher influence, but the actual pace was only 98 (vs predicted 101),
meaning the Defensive Grinder style won. The cluster adjustment overestimated the pace pusher's
ability to control tempo. In future matchups between these cluster types, reduce the pace
adjustment to +0.5 when the grinder has home court advantage."
```

**IMPORTANT**: Similarity analysis is complementary to the 4 main sections. Use it to add context about team playstyles and cluster-based adjustments, but don't rely on it exclusively. Always connect it back to actual game stats and outcomes.

## 5. Detect Team Trends

Analyze last-5 data for both teams:
- pace trends
- efficiency trends
- 3PT volume trends
- defensive trends
- scoring volatility

Explain how these trends impacted the game and whether the model accounted for them.

## 6. Identify Game Style

Classify the game as:
- 3PT shootout
- paint-dominant
- slow defensive battle
- transition/fastbreak heavy
- turnover-driven
- free-throw heavy
- high-efficiency or low-efficiency

Explain the style clearly and simply.

## 7. Analyze the Model Pipeline

You will receive values like:
```
"pipeline_movements": {
  "baseline_total": 225,
  "defense_adjusted": 221.5,
  "pace_adjusted": 230,
  "final_predicted_total": 229.4
}
```

Explain:
- which adjustments were correct
- which adjustments were too strong or too weak
- where the model misunderstood the matchup

DO NOT propose machine learning.

## 8. Distinguish Model Error vs Game Outlier

Call out:
- random variance (hot/cold shooting)
- abnormal foul rate
- rare pace outcomes
- statistical outliers

Say when the prediction missed due to:
- model logic
- matchup misunderstanding
- pure variance

## 9. Provide Deterministic, Rule-Based Improvements

Give 2–4 tuning suggestions.
They MUST be deterministic and based on actual data patterns.

Examples:
- increase pace weight when both teams show +4 last-5 pace
- reduce OVER bias when both teams attack the paint poorly
- add UNDER flags when expected FT rate is low
- boost 3PT volatility penalty when both teams take 35+ threes

No machine learning.
No randomness.

## 10. Output a Structured Report

Return a JSON object with:
- **verdict** ("WIN" | "LOSS")
- **headline** (praise or humility)
- **game_summary**
- **expected_vs_actual** (stat differences)
- **trend_notes**
- **game_style**
- **pipeline_analysis**
- **key_drivers** (what decided the total)
- **model_lessons** (your deterministic improvements)

Everything must be clean, simple, and easy for UI rendering.

## Tone Rules

- 5th-grade reading level
- Clear, confident, simple
- Never dramatic, never vague
- Always backed by stats
- Short sentences, clear meaning

## Mission (one sentence)

You are a post-game NBA analyst that compares actual stats vs expected stats, reads your model's full prediction pipeline, detects trends and identities, praises correct calls, explains misses, and gives deterministic rule-based improvements.

## Output Format

Return ONLY valid JSON in this exact structure:

```json
{
  "verdict": "WIN" | "LOSS",
  "headline": "short praise or humility line",
  "game_summary": "1-2 sentences explaining what happened",
  "expected_vs_actual": {
    "pace": "actual was faster/slower than predicted and why",
    "shooting": "actual shooting was hotter/colder than predicted",
    "free_throws": "FT attempts were higher/lower than expected",
    "turnovers": "turnovers impact on possessions",
    "three_point_volume": "3PT attempts vs expected"
  },
  "trend_notes": "how last-5 trends affected this game",
  "game_style": "classification of game style",
  "pipeline_analysis": {
    "baseline": "was baseline accurate",
    "defense_adjustment": "was defense adjustment correct",
    "pace_adjustment": "was pace adjustment correct",
    "overall": "summary of pipeline accuracy"
  },
  "key_drivers": [
    "main factor 1",
    "main factor 2",
    "main factor 3"
  ],
  "model_lessons": [
    "deterministic improvement 1",
    "deterministic improvement 2"
  ]
}
```

Return ONLY the JSON, no additional text.

GOAL OF THE MODEL:
- When the model predicts a total BELOW the sportsbook line, the real final total should also tend to be below.
- When the model predicts a total ABOVE the sportsbook line, the real final total should also tend to be above.
- The objective is to improve model ACCURACY and alignment between predicted direction and actual result.

THE AI DOES NOT GIVE PICKS OR BETTING ADVICE.
It ONLY analyzes model accuracy after games are finished.

Return ONLY the JSON in the specified format, no additional text."""

        # Call OpenAI API with v2 prompt
        logger.info(f"[AI COACH] Calling OpenAI API for game {game_id}")
        logger.info(f"[AI COACH] Model Pick: {model_direction}, Sportsbook Line: {sportsbook_line}, Predicted: {f'{predicted_total:.1f}' if predicted_total is not None else 'None'}, Actual: {actual_total}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1200,  # Increased for v2's more detailed response
            temperature=0.3
        )

        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()

        # Try to parse JSON (handle potential markdown code blocks)
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()

        result = json.loads(response_text)

        # Add metadata to result
        result['raw_response'] = response_text
        result['model'] = model
        result['version'] = 'v2'
        result['prediction_correct'] = prediction_correct

        logger.info(f"[AI COACH] ✅ Analysis complete for game {game_id}")
        logger.info(f"[AI COACH] Verdict: {result.get('verdict', 'UNKNOWN')} | Headline: {result.get('headline', 'N/A')[:50]}...")
        if error_total is not None:
            logger.info(f"[AI COACH] Error: {error_total:+.1f} points | Correct: {prediction_correct}")
        else:
            logger.info(f"[AI COACH] Error: N/A (predicted_total was None) | Correct: {prediction_correct}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[OpenAI Text] Failed to parse JSON response: {response_text}")
        raise ValueError(f"Invalid JSON response from Text API: {str(e)}")
    except Exception as e:
        logger.error(f"[OpenAI Text] Error generating review: {str(e)}")
        raise


def generate_daily_coach_summary(
    reviews: list,
    model: str = "gpt-4.1-mini"
) -> Dict:
    """
    Generate "Today's Model Coach" summary from multiple game reviews.

    Args:
        reviews: List of game review dicts with predicted/actual scores
        model: OpenAI model to use

    Returns:
        Dict with:
            - overall_performance: str
            - biggest_miss: dict
            - biggest_win: dict
            - patterns: list of str
            - action_items: list of str
    """
    try:
        client = get_client()

        # Calculate aggregate stats
        total_games = len(reviews)
        avg_error = sum(abs(r['error_total']) for r in reviews) / max(total_games, 1)

        games_within_3 = sum(1 for r in reviews if abs(r['error_total']) <= 3)
        games_within_7 = sum(1 for r in reviews if abs(r['error_total']) <= 7)

        # Find biggest miss and biggest win
        biggest_miss = max(reviews, key=lambda r: abs(r['error_total']))
        biggest_win = min(reviews, key=lambda r: abs(r['error_total']))

        # Build summary of all games
        games_summary = "\n".join([
            f"- {r['home_team']} vs {r['away_team']}: Predicted {r['predicted_total']:.1f}, Actual {r['actual_total']} (Error: {r['error_total']:+.1f})"
            for r in reviews
        ])

        prompt = f"""You are analyzing an NBA prediction model's performance across {total_games} games today.

AGGREGATE STATS:
- Average error: {avg_error:.1f} points
- Within 3 points: {games_within_3}/{total_games} ({games_within_3/max(total_games,1)*100:.0f}%)
- Within 7 points: {games_within_7}/{total_games} ({games_within_7/max(total_games,1)*100:.0f}%)

GAMES:
{games_summary}

Provide a coaching summary in JSON:
{{
    "overall_performance": "<1-2 sentence assessment of model's performance today>",
    "patterns": ["<pattern 1>", "<pattern 2>"],
    "action_items": ["<improvement 1>", "<improvement 2>"]
}}

Focus on:
- Common themes (over-predicting fast-paced games? under-predicting defense?)
- Systematic biases
- Actionable improvements

Return ONLY the JSON.

JSON:"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert NBA analytics coach providing daily model reviews."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.3
        )

        response_text = response.choices[0].message.content.strip()

        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()

        result = json.loads(response_text)

        # Add aggregate stats and extremes
        result['total_games'] = total_games
        result['avg_error'] = round(avg_error, 1)
        result['games_within_3'] = games_within_3
        result['games_within_7'] = games_within_7
        result['biggest_miss'] = {
            'game': f"{biggest_miss['home_team']} vs {biggest_miss['away_team']}",
            'error': biggest_miss['error_total']
        }
        result['biggest_win'] = {
            'game': f"{biggest_win['home_team']} vs {biggest_win['away_team']}",
            'error': biggest_win['error_total']
        }

        logger.info(f"[OpenAI Coach] Generated daily summary for {total_games} games")

        return result

    except Exception as e:
        logger.error(f"[OpenAI Coach] Error generating daily summary: {str(e)}")
        raise
