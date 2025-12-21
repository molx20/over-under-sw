# AI Model Coach Data Flow Documentation

## Overview
This document traces the complete data flow from prediction → screenshot upload → AI analysis → UI display.

---

## Component Architecture

### Frontend Components

1. **GamePage.jsx** (`src/pages/GamePage.jsx`)
   - Main game detail page
   - Displays prediction card with betting line, predicted total, OVER/UNDER recommendation
   - Contains "Upload Final Score" button
   - Manages `customBettingLine` state (user-entered betting line)
   - Opens `PostGameReviewModal` when user clicks upload button

2. **PredictionPanel.jsx** (`src/components/PredictionPanel.jsx`)
   - Displays the model's prediction
   - Shows: predicted home score, predicted away score, predicted total
   - Shows: OVER/UNDER recommendation

3. **PostGameReviewModal.jsx** (`src/components/PostGameReviewModal.jsx`)
   - Modal for uploading final score screenshot
   - Auto-loads existing reviews from database
   - Handles screenshot upload and analysis display
   - **KEY**: Receives `gameData` prop with prediction object including `betting_line`

### Backend Endpoints

1. **POST /api/games/<game_id>/result-screenshot** (`server.py:1836`)
   - Receives screenshot upload
   - Extracts form data (predicted values, teams, betting line)
   - Calls OpenAI Vision to extract actual scores
   - Fetches comprehensive prediction data
   - Calls AI Model Coach
   - Stores result in database
   - Returns analysis to frontend

2. **GET /api/games/<game_id>/review** (`server.py:2093`)
   - Retrieves saved analysis from database
   - Returns existing review if available

### Backend AI Functions

1. **generate_game_review()** (`api/utils/openai_client.py:193`)
   - Main AI Model Coach function
   - Uses GPT-4.1-mini with comprehensive v2 system prompt
   - Determines WIN/LOSS based on strict directional logic
   - Returns structured analysis

---

## Complete Data Flow

### Step 1: User Views Prediction

```
GamePage.jsx
  ├─ Fetches prediction via useGameDetail()
  ├─ Displays PredictionPanel with:
  │    ├─ Betting Line (e.g., 235.5)
  │    ├─ Predicted Total (e.g., 208.8)
  │    ├─ Predicted Home Score (e.g., 104.2)
  │    ├─ Predicted Away Score (e.g., 103.1)
  │    └─ Recommendation (OVER/UNDER)
  └─ User can enter custom betting line
```

**Prediction Object Structure:**
```javascript
{
  predicted_total: 208.8,
  betting_line: 235.5,
  recommendation: "UNDER",
  breakdown: {
    home_projected: 104.2,
    away_projected: 103.1,
    home_baseline: 110.5,
    away_baseline: 108.2,
    game_pace: 98.5,
    // ... other breakdown fields
  },
  factors: { ... },
  home_last5_trends: { ... },
  away_last5_trends: { ... }
}
```

---

### Step 2: User Uploads Screenshot

```
User clicks "Upload Final Score"
  ↓
PostGameReviewModal opens
  ↓
User selects/drops screenshot file
  ↓
Frontend creates FormData:
  {
    screenshot: <File>,
    home_team: "Orlando Magic",
    away_team: "Miami Heat",
    game_date: "2025-12-09",
    predicted_home: 104.2,
    predicted_away: 103.1,
    predicted_total: 208.8,
    sportsbook_line: 235.5  ← CRITICAL for WIN/LOSS
  }
  ↓
POST /api/games/<game_id>/result-screenshot
```

**Frontend Code** (`PostGameReviewModal.jsx:113-121`):
```javascript
const formData = new FormData();
formData.append('screenshot', selectedFile);
formData.append('home_team', gameData.home_team);
formData.append('away_team', gameData.away_team);
formData.append('game_date', gameData.game_date);
formData.append('predicted_home', gameData.prediction.breakdown.home_projected);
formData.append('predicted_away', gameData.prediction.breakdown.away_projected);
formData.append('predicted_total', gameData.prediction.predicted_total);
formData.append('sportsbook_line', gameData.prediction.betting_line); // ← ADDED
```

---

### Step 3: Backend Processes Upload

```
Backend receives POST /api/games/<game_id>/result-screenshot
  ↓
1. Extract form data (predicted values, betting line)
  ↓
2. Call OpenAI Vision API
     extract_scores_from_screenshot()
     └─ Returns: { home_score: 117, away_score: 108, total: 225 }
  ↓
3. Fetch comprehensive data:
     ├─ prediction_breakdown (from cache via get_cached_prediction)
     ├─ team_season_stats (via get_team_stats_with_ranks)
     ├─ last_5_trends (from prediction object)
     └─ box_score_stats (via get_game_box_score)
  ↓
4. Build complete AI Coach payload
  ↓
5. Call generate_game_review()
  ↓
6. Store result in game_reviews.db
  ↓
7. Return analysis to frontend
```

**Backend Code** (`server.py:1999-2031`):
```python
# Comprehensive logging
print(f"[AI COACH] Starting post-game analysis for game {game_id}")
print(f"  Sportsbook Line: {sportsbook_line}")
print(f"  Predicted Total: {predicted_total}")
print(f"  Actual Total: {actual_total}")
print(f"  Has Prediction Breakdown: {bool(prediction_breakdown)}")

# Call AI Coach with ALL data
ai_review = generate_game_review(
    game_id,
    home_team,
    away_team,
    predicted_total,
    actual_total,
    predicted_home,
    actual_home,
    predicted_away,
    actual_away,
    predicted_pace=predicted_pace,
    home_box_score=home_box_score,
    away_box_score=away_box_score,
    prediction_breakdown=prediction_breakdown,  # ← Pipeline data
    team_season_stats=team_season_stats,        # ← Season stats
    last_5_trends=last_5_trends,                # ← Trends
    sportsbook_line=sportsbook_line,            # ← CRITICAL
    model="gpt-4.1-mini"
)
```

---

### Step 4: AI Model Coach Analysis

```
generate_game_review() receives complete payload
  ↓
1. Determine model direction:
     predicted_total vs sportsbook_line
     → OVER if predicted > line
     → UNDER if predicted < line
  ↓
2. Determine actual outcome:
     actual_total vs sportsbook_line
     → OVER if actual > line
     → UNDER if actual < line
  ↓
3. Apply strict WIN/LOSS logic:
     ✓ WIN: Model predicted UNDER and actual < line
     ✓ WIN: Model predicted OVER and actual > line
     ✗ LOSS: Model predicted UNDER and actual ≥ line
     ✗ LOSS: Model predicted OVER and actual ≤ line
     ✗ LOSS: Push (actual == line)
  ↓
4. Build comprehensive game data JSON for AI:
     {
       "sportsbook_line": 235.5,
       "predicted": {
         "total": 208.8,
         "home_score": 104.2,
         "away_score": 103.1,
         "over_under_pick": "UNDER"
       },
       "actual": {
         "total": 225,
         "home_score": 117,
         "away_score": 108
       },
       "pipeline_movements": { ... },
       "team_season_averages": { ... },
       "last_5_trends": { ... },
       "home_box_score": { pace, fga, 3pa, fta, tov, ... },
       "away_box_score": { ... }
     }
  ↓
5. Send to OpenAI with v2 system prompt
  ↓
6. Parse JSON response
  ↓
7. Return structured analysis
```

**AI Coach System Prompt** (`openai_client.py:362-596`):
- Strict WIN/LOSS determination based ONLY on directional accuracy
- Compares actual vs expected stats (pace, shooting, FTs, turnovers, 3PT volume)
- Detects game style (shootout, defensive battle, etc.)
- Analyzes pipeline movements (baseline → adjustments → final)
- Provides deterministic, rule-based improvement suggestions

**Response Structure:**
```json
{
  "verdict": "WIN" | "LOSS",
  "headline": "short praise or humility line",
  "game_summary": "1-2 sentences explaining what happened",
  "expected_vs_actual": {
    "pace": "...",
    "shooting": "...",
    "free_throws": "...",
    "turnovers": "...",
    "three_point_volume": "..."
  },
  "trend_notes": "how last-5 trends affected this game",
  "game_style": "classification of game style",
  "pipeline_analysis": {
    "baseline": "...",
    "defense_adjustment": "...",
    "pace_adjustment": "...",
    "overall": "..."
  },
  "key_drivers": ["factor 1", "factor 2", "factor 3"],
  "model_lessons": ["improvement 1", "improvement 2"]
}
```

---

### Step 5: Database Storage

```
Backend stores review in game_reviews.db:
  {
    game_id,
    home_team,
    away_team,
    game_date,
    actual_home_score,
    actual_away_score,
    actual_total,
    predicted_home_score,
    predicted_away_score,
    predicted_total,
    error_total,
    ai_review_json,  ← Full v2 analysis stored here
    screenshot_filename,
    created_at,
    updated_at
  }
```

---

### Step 6: Frontend Displays Analysis

```
Frontend receives response:
  {
    success: true,
    review: {
      game_id,
      actual_total: 225,
      predicted_total: 208.8,
      error_total: +16.2,
      ai_review: {
        verdict: "WIN",
        headline: "Model correctly predicted UNDER",
        game_summary: "...",
        expected_vs_actual: { ... },
        // ... rest of v2 structure
      }
    }
  }
  ↓
PostGameReviewModal renders:
  ├─ Verdict badge (WIN ✓ / LOSS ✗)
  ├─ Headline
  ├─ Game Summary
  ├─ Expected vs Actual stats
  ├─ Trend Notes
  ├─ Game Style
  ├─ Pipeline Analysis
  ├─ Key Drivers
  └─ Model Lessons
```

**Frontend Rendering** (`PostGameReviewModal.jsx:196-347`):
- Shows "Saved Review" badge if loading existing review
- Displays verdict with color coding (green=WIN, red=LOSS)
- Shows all v2 analysis sections
- Supports re-uploading to update review

---

## WIN/LOSS Determination Logic

### Rules (Strict, Deterministic)

```python
actual_total = home_score + away_score

# Determine model pick
if predicted_total > sportsbook_line:
    model_pick = "OVER"
elif predicted_total < sportsbook_line:
    model_pick = "UNDER"
else:
    model_pick = "NEUTRAL"

# Determine actual outcome
if actual_total > sportsbook_line:
    actual_outcome = "OVER"
elif actual_total < sportsbook_line:
    actual_outcome = "UNDER"
else:
    actual_outcome = "PUSH"

# Determine WIN/LOSS
if actual_outcome == "PUSH":
    verdict = "LOSS"  # Pushes counted as incorrect
elif model_pick == actual_outcome:
    verdict = "WIN"
else:
    verdict = "LOSS"
```

### Examples

| Line | Predicted | Model Pick | Actual | Outcome | Verdict | Reason |
|------|-----------|------------|--------|---------|---------|--------|
| 235.5 | 208.8 | UNDER | 225 | UNDER | **WIN** | 225 < 235.5 ✓ |
| 227.5 | 245.2 | OVER | 214 | UNDER | **LOSS** | 214 ≤ 227.5 ✗ |
| 230.0 | 218.5 | UNDER | 230 | PUSH | **LOSS** | Exact tie ✗ |
| 220.5 | 225.0 | OVER | 235 | OVER | **WIN** | 235 > 220.5 ✓ |

---

## Data Validation Checklist

When uploading a screenshot, the backend should have:

✅ **Required Fields:**
- `sportsbook_line` (from user input or prediction)
- `predicted_total`
- `predicted_home`, `predicted_away`
- `actual_total` (from Vision API)
- `actual_home`, `actual_away` (from Vision API)

✅ **Optional Enhanced Data:**
- `prediction_breakdown` (pipeline movements)
- `team_season_stats` (season averages)
- `last_5_trends` (recent form)
- `home_box_score`, `away_box_score` (game stats)

⚠️ **If Missing:**
- If `sportsbook_line` is missing → AI cannot determine WIN/LOSS correctly
- If `prediction_breakdown` is missing → AI cannot analyze pipeline
- If box scores missing → AI has less context but can still analyze

---

## Logging and Debugging

### Backend Logs (server.py)

When processing a screenshot upload:
```
================================================================================
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
================================================================================
```

### AI Coach Logs (openai_client.py)

```
[AI COACH] Calling OpenAI API for game 0022500XXX
[AI COACH] Model Pick: UNDER, Sportsbook Line: 235.5, Predicted: 208.8, Actual: 225
[AI COACH] ✅ Analysis complete for game 0022500XXX
[AI COACH] Verdict: WIN | Headline: Model correctly predicted UNDER and the game...
[AI COACH] Error: +16.2 points | Correct: True
```

---

## Troubleshooting

### Issue: "Model direction could not be evaluated due to missing sportsbook line"

**Cause:** The `sportsbook_line` was not sent in the upload formData.

**Fix:** Ensure `gameData.prediction.betting_line` is set before opening modal.

**Code Check:** `PostGameReviewModal.jsx:121`
```javascript
formData.append('sportsbook_line', gameData.prediction.betting_line);
```

---

### Issue: Old review shows without betting line

**Cause:** Review was saved before the sportsbook_line fix.

**Fix:** Delete old review and re-upload screenshot.
```bash
sqlite3 api/data/game_reviews.db "DELETE FROM game_reviews WHERE game_id = 'XXX';"
```

---

### Issue: Prediction data not showing in analysis

**Cause:** `prediction_breakdown` not fetched or passed to AI Coach.

**Fix:** Verify `get_cached_prediction()` is called in backend.

**Code Check:** `server.py:1953-1963`

---

## Summary

The AI Model Coach system is **fully connected** with the following data flow:

1. ✅ **Frontend** sends complete prediction data (including custom betting line)
2. ✅ **Backend** fetches comprehensive data (prediction, stats, trends, box scores)
3. ✅ **AI Coach** receives complete payload for analysis
4. ✅ **WIN/LOSS** determined by strict directional logic (not point difference)
5. ✅ **Analysis** stored in database and displayed in UI
6. ✅ **Logging** tracks every step for debugging

**No changes needed to prediction math or core logic.**
**System is deterministic and rule-based.**
**All components are wired correctly.**
