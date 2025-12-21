# Advanced Stats Wiring for AI Model Coach - Implementation Summary

## Overview

Successfully wired expected vs actual stats (pace, FTA, turnovers, 3PA) into the AI Model Coach without changing core prediction math. The AI now receives real stat comparisons instead of saying "data is missing."

---

## Files Changed

### 1. **NEW FILE**: `api/utils/expected_vs_actual_stats.py`

**Purpose**: Deterministic helper functions to compute expected values from season stats and actual values from box scores.

**Key Functions**:
- `compute_expected_pace(home_pace, away_pace)` - Simple average
- `compute_expected_fta(home_fta, away_fta)` - Sum of team FTA averages
- `compute_expected_turnovers(home_tov, away_tov)` - Sum of team turnover averages
- `compute_expected_3pa(home_3pa, away_3pa)` - Sum of team 3PA averages
- `compute_actual_stats_from_box_scores(home_box, away_box)` - Extract actual values
- `compute_all_expected_vs_actual()` - Main entry point that computes all comparisons

**Logging**: Logs all computed expected/actual stats for debugging

**Code Example**:
```python
def compute_expected_pace(
    home_season_pace: Optional[float],
    away_season_pace: Optional[float]
) -> Optional[float]:
    """Compute expected game pace from team season averages."""
    if home_season_pace is None or away_season_pace is None:
        return None
    return (home_season_pace + away_season_pace) / 2.0
```

---

### 2. **UPDATED**: `api/utils/db_queries.py`

**Changes**: Extended `get_team_stats_with_ranks()` to include additional stats needed for expected value calculation.

**Lines Modified**: 286-307

**New Stats Added**:
```python
'fta': {'value': row['fta'] if 'fta' in row.keys() else None, 'rank': None},
'turnovers': {'value': row['turnovers'] if 'turnovers' in row.keys() else None, 'rank': None},
'fg3a': {'value': row['fg3a'] if 'fg3a' in row.keys() else None, 'rank': None},
```

**Impact**: Season stats now include per-game FTA, turnovers, and 3PA for both teams.

---

### 3. **UPDATED**: `server.py`

**Changes**: Compute expected vs actual stats before calling AI Coach.

**Lines Modified**: 1999-2044

**New Logic**:
```python
# Import the new helper module
from api.utils.expected_vs_actual_stats import compute_all_expected_vs_actual

# Compute expected vs actual stats
expected_vs_actual = compute_all_expected_vs_actual(
    team_season_stats=team_season_stats,
    home_box_score=home_box_score,
    away_box_score=away_box_score,
    predicted_pace=predicted_pace
)

# Log availability
print(f"  Has Expected vs Actual Stats: {bool(expected_vs_actual)}")

# Pass to AI Coach
ai_review = generate_game_review(
    # ... existing params ...
    expected_vs_actual=expected_vs_actual,  # NEW
    model="gpt-4.1-mini"
)
```

**Impact**: Backend now computes all stat comparisons before generating AI review.

---

### 4. **UPDATED**: `api/utils/openai_client.py`

**Changes**:
1. Added `expected_vs_actual` parameter to `generate_game_review()`
2. Added expected_vs_actual_stats to the game_data payload sent to OpenAI
3. Updated system prompt with detailed instructions on how to use these stats

**Lines Modified**:
- Function signature: 193-212
- Docstring: 238-242
- Payload construction: 367-386
- System prompt: 464-500

**New Payload Structure**:
```python
game_data["expected_vs_actual_stats"] = {
    "pace": {
        "expected": expected_vs_actual.get('expected_pace'),  # e.g., 98.5
        "actual": expected_vs_actual.get('actual_pace')       # e.g., 102.3
    },
    "free_throw_attempts": {
        "expected": expected_vs_actual.get('expected_fta_total'),  # e.g., 38.0
        "actual": expected_vs_actual.get('actual_fta_total')       # e.g., 45
    },
    "turnovers": {
        "expected": expected_vs_actual.get('expected_turnovers_total'),  # e.g., 24.0
        "actual": expected_vs_actual.get('actual_turnovers_total')       # e.g., 28
    },
    "three_point_attempts": {
        "expected": expected_vs_actual.get('expected_3pa_total'),  # e.g., 66.0
        "actual": expected_vs_actual.get('actual_3pa_total')       # e.g., 75
    }
}
```

**System Prompt Update**:
```
## 2. Compare Actual Stats vs Expected Stats

You will receive an `expected_vs_actual_stats` object with expected and actual values for key stats.

**How to Use These Stats:**

1. **If both expected and actual are provided**: Compare them directly
   - "Pace was 102 vs expected 98, meaning the game was faster than normal"
   - "Teams combined for 45 FTA vs expected 38, leading to more scoring opportunities"

2. **If only actual is provided**: Note the actual value without comparison
   - "Game pace was 102 possessions"

3. **If both are null**: Only then say data is missing
   - "Pace data is unavailable for this analysis"

**IMPORTANT**: Only say data is "missing" or "unavailable" if BOTH expected and actual values are null.
```

---

## Complete Data Flow

### Step 1: Screenshot Upload
User uploads screenshot → Backend receives game_id, teams, predicted values

### Step 2: Data Gathering (server.py:1918-1997)
```python
# Fetch comprehensive data
home_box_score = get_game_box_score(game_id, home_team_id)
away_box_score = get_game_box_score(game_id, away_team_id)
team_season_stats = {
    'home': get_team_stats_with_ranks(home_team_id),  # Now includes fta, tov, fg3a
    'away': get_team_stats_with_ranks(away_team_id)
}
prediction_breakdown = get_cached_prediction(...)
```

### Step 3: Compute Expected vs Actual (server.py:1999-2007)
```python
expected_vs_actual = compute_all_expected_vs_actual(
    team_season_stats=team_season_stats,
    home_box_score=home_box_score,
    away_box_score=away_box_score,
    predicted_pace=predicted_pace
)

# Result example:
{
    'expected_pace': 98.5,
    'actual_pace': 102.3,
    'expected_fta_total': 38.0,
    'actual_fta_total': 45,
    'expected_turnovers_total': 24.0,
    'actual_turnovers_total': 28,
    'expected_3pa_total': 66.0,
    'actual_3pa_total': 75
}
```

### Step 4: Build AI Payload (openai_client.py:367-386)
```python
game_data["expected_vs_actual_stats"] = {
    "pace": {"expected": 98.5, "actual": 102.3},
    "free_throw_attempts": {"expected": 38.0, "actual": 45},
    "turnovers": {"expected": 24.0, "actual": 28},
    "three_point_attempts": {"expected": 66.0, "actual": 75}
}
```

### Step 5: AI Analysis
OpenAI receives complete payload → Compares expected vs actual → Returns structured analysis

### Step 6: Frontend Display
```json
{
  "expected_vs_actual": {
    "pace": "Game pace was 102 vs expected 98, making it a faster-paced contest",
    "free_throws": "Teams combined for 45 FTA vs expected 38, adding 14 extra points",
    "turnovers": "Turnovers were 28 vs expected 24, creating 4 extra possessions",
    "three_point_volume": "Teams attempted 75 threes vs expected 66, a high-volume shootout"
  }
}
```

---

## Final AI Coach Payload Structure

```json
{
  "game_id": "0022500XXX",
  "teams": {
    "home": "Orlando Magic",
    "away": "Miami Heat"
  },
  "sportsbook_line": 235.5,
  "predicted": {
    "home_score": 104.2,
    "away_score": 103.1,
    "total": 208.8,
    "pace": 98.5,
    "over_under_pick": "UNDER"
  },
  "actual": {
    "home_score": 117,
    "away_score": 108,
    "total": 225
  },
  "error": {
    "home": 12.8,
    "away": 4.9,
    "total": 16.2
  },
  "expected_vs_actual_stats": {
    "pace": {
      "expected": 98.5,
      "actual": 102.3
    },
    "free_throw_attempts": {
      "expected": 38.0,
      "actual": 45
    },
    "turnovers": {
      "expected": 24.0,
      "actual": 28
    },
    "three_point_attempts": {
      "expected": 66.0,
      "actual": 75
    }
  },
  "pipeline_movements": {
    "baseline_total": 225.0,
    "defense_adjusted": 221.5,
    "pace_adjusted": 230.0,
    "final_predicted_total": 229.4
  },
  "team_season_averages": { ... },
  "last_5_trends": { ... },
  "home_box_score": { ... },
  "away_box_score": { ... }
}
```

---

## Key Principles Maintained

✅ **No changes to core prediction math** - All helpers are read-only
✅ **Deterministic calculations** - Simple averages and sums, no ML
✅ **Defensive coding** - All functions handle None values gracefully
✅ **Comprehensive logging** - Expected/actual stats logged for debugging
✅ **Frontend unchanged** - Response structure remains compatible

---

## Testing Guide

### Test Case: Orlando Magic vs Miami Heat

**Expected Behavior**:

1. **Before wiring**:
   - "No pace prediction provided…"
   - "Free throw attempt data is missing…"
   - "Turnover data is unavailable…"
   - "3PT attempt data is missing…"

2. **After wiring**:
   - "Pace was 102 vs expected 98, making the game faster"
   - "Teams combined for 45 FTA vs expected 38, leading to 14 extra points"
   - "Turnovers were 28 vs expected 24, creating 4 extra possessions"
   - "Teams attempted 75 threes vs expected 66, a high-volume shootout"

### Verification Steps:

1. Upload a screenshot for a completed game
2. Check backend logs for:
   ```
   [Expected vs Actual] Computed stats | exp_pace=98.5 act_pace=102.3 | exp_fta=38.0 act_fta=45 | ...
   ```
3. Check AI response for specific stat comparisons (not "missing" messages)
4. Verify frontend displays detailed "Expected vs Actual" section

---

## Logging Output Example

```
[AI COACH] Starting post-game analysis for game 0022500XXX
[AI COACH] Data Summary:
  Teams: Orlando Magic vs Miami Heat
  Sportsbook Line: 235.5
  Predicted Total: 208.8 (104.2 + 103.1)
  Actual Total: 225 (117 + 108)
  Error: +16.2 points
  Has Prediction Breakdown: True
  Has Team Season Stats: True
  Has Last-5 Trends: True
  Has Box Score Stats: True
  Has Expected vs Actual Stats: True  ← NEW

[Expected vs Actual] Computed stats | exp_pace=98.5 act_pace=102.3 | exp_fta=38.0 act_fta=45 | exp_tov=24.0 act_tov=28 | exp_3pa=66.0 act_3pa=75
```

---

## Summary

**What Changed**:
- Created helper module to compute expected/actual stat comparisons
- Extended database queries to include FTA, turnovers, 3PA from season stats
- Wired computations into server.py before AI Coach call
- Updated AI payload to include expected_vs_actual_stats object
- Updated system prompt with detailed instructions on using these stats

**What Didn't Change**:
- Core prediction engine logic
- Prediction math or formulas
- Frontend UI components
- Database schema (all needed fields already existed)

**Result**:
AI Model Coach now receives real expected vs actual numbers for pace, FTA, turnovers, and 3PA, enabling detailed stat-based explanations instead of "data missing" messages.
