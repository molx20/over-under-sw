# Self-Learning NBA Prediction Feature - Usage Guide

## Overview

This feature adds a betting-line-aware self-learning system to your NBA prediction app. It learns from:
1. Your model's pre-game predictions
2. Sportsbook closing total lines
3. Actual final game scores

The system gradually improves by comparing your model's accuracy against the sportsbook line and adjusting itself over time.

---

## Architecture

### Components

1. **SQLite Database** (`api/data/predictions.db`)
   - Stores all predictions, sportsbook lines, and learning outcomes
   - Lightweight, file-based, included in your Railway deployment

2. **Enhanced Team Ratings Model** (`api/utils/team_ratings_model.py`)
   - Original team offensive/defensive ratings (existing)
   - NEW: `total_bias` parameter that learns from sportsbook lines
   - NEW: `predict_with_bias()` function for enhanced predictions

3. **Three New API Endpoints**:
   - `POST /api/save-prediction` - Save pre-game prediction
   - `POST /api/submit-line` - Submit sportsbook total line
   - `POST /api/run-learning` - Trigger post-game learning

---

## Database Schema

### `game_predictions` Table

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | TEXT | Unique NBA game ID |
| `home_team` | TEXT | Home team tricode (e.g., "BOS") |
| `away_team` | TEXT | Away team tricode (e.g., "LAL") |
| `pred_total` | REAL | Model's predicted total points |
| `pred_home` | REAL | Model's predicted home score |
| `pred_away` | REAL | Model's predicted away score |
| `sportsbook_total_line` | REAL | Over/under line from sportsbooks |
| `actual_home` | REAL | Actual home team final score |
| `actual_away` | REAL | Actual away team final score |
| `actual_total` | REAL | Actual total points scored |
| `model_error` | REAL | actual_total - pred_total |
| `line_error` | REAL | actual_total - sportsbook_line |
| `model_abs_error` | REAL | Absolute value of model error |
| `line_abs_error` | REAL | Absolute value of line error |
| `model_beat_line` | BOOLEAN | True if model was more accurate |

### `model_performance` Table

Tracks aggregate performance metrics over time.

---

## Learning Algorithm

### Model Formula

```python
# Basic prediction (existing)
PTS_home_hat = base + HCA + Off[home] - Def[away]
PTS_away_hat = base - HCA + Off[away] - Def[home]

# Enhanced prediction (NEW)
total_hat = (PTS_home_hat + PTS_away_hat) + total_bias
```

### Parameters (in `model.json`)

```json
{
  "version": "2.0",
  "parameters": {
    "base": 100,                    // Base points per team
    "hca": 2,                       // Home court advantage
    "learning_rate": 0.02,          // Team rating learning rate
    "line_learning_rate": 0.005,    // NEW: Line-aware learning rate
    "total_bias": 0                 // NEW: Learned bias from lines
  }
}
```

### Learning Steps

#### 1. Team Rating Updates (Existing Logic)
```python
err_home = actual_home - pred_home
err_away = actual_away - pred_away

Off[home] += learning_rate * err_home
Def[away] -= learning_rate * err_home
Off[away] += learning_rate * err_away
Def[home] -= learning_rate * err_away
```

#### 2. Line-Aware Learning (NEW)
```python
# Compute errors
model_error = actual_total - pred_total
line_error = actual_total - sportsbook_line

# If line beat model, nudge total_bias toward it
if |line_error| < |model_error|:
    line_gap = sportsbook_line - pred_total
    total_bias += line_learning_rate * line_gap

# Clamp to prevent over-correction
total_bias = clamp(total_bias, -5, +5)
```

**Why this works:**
- If the sportsbook line is consistently more accurate, the model learns to shift its predictions toward it
- The small learning rate (0.005) means gradual, stable learning
- The clamp prevents the model from becoming over-reliant on lines

---

## Usage Workflow

### Step 1: Save Pre-Game Prediction

**Before the game starts**, save your model's prediction:

```bash
curl -X POST http://your-app.railway.app/api/save-prediction \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "0022500123",
    "home_team": "BOS",
    "away_team": "LAL"
  }'
```

**Response:**
```json
{
  "success": true,
  "game_id": "0022500123",
  "prediction": {
    "home": 112.5,
    "away": 108.2,
    "total": 220.7
  },
  "saved_at": "2025-11-19T18:00:00Z"
}
```

### Step 2: Submit Sportsbook Line

**Anytime before or during the game**, enter the sportsbook total line:

```bash
curl -X POST http://your-app.railway.app/api/submit-line \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "0022500123",
    "sportsbook_total_line": 218.5
  }'
```

**Response:**
```json
{
  "success": true,
  "game_id": "0022500123",
  "line": 218.5,
  "submitted_at": "2025-11-19T19:30:00Z"
}
```

### Step 3: Run Post-Game Learning

**After the game finishes**, trigger the learning process:

```bash
curl -X POST http://your-app.railway.app/api/run-learning \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "0022500123"
  }'
```

**Response:**
```json
{
  "success": true,
  "game_id": "0022500123",
  "actual_total": 215.0,
  "pred_total": 220.7,
  "sportsbook_line": 218.5,
  "model_error": -5.7,
  "line_error": -3.5,
  "model_beat_line": false,
  "total_bias_update": {
    "old": 0.0,
    "new": 0.02,
    "adjustment": 0.02
  },
  "updates": {
    "BOS_off": 0.15,
    "BOS_def": -0.08,
    "LAL_off": 0.22,
    "LAL_def": -0.14
  },
  "model_committed": true
}
```

**What happened:**
- Actual total: 215 points
- Your model predicted: 220.7 (5.7 points off)
- Sportsbook line: 218.5 (3.5 points off)
- **Line was more accurate**, so `total_bias` increased by 0.02
- Team ratings updated based on actual performance
- Model committed to GitHub (if `GH_TOKEN` is set)

---

## Real-World Example

Let's walk through a complete example with the HOU @ LAC game:

### Before the game
```bash
# 1. Save prediction
curl -X POST https://your-app.railway.app/api/save-prediction \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500255", "home_team": "LAC", "away_team": "HOU"}'

# Response: Model predicts 200.46 total points
```

### During the game
```bash
# 2. Enter sportsbook line you found
curl -X POST https://your-app.railway.app/api/submit-line \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500255", "sportsbook_total_line": 221.5}'

# Response: Line saved
```

### After the game (Final: HOU 114, LAC 104 = 218 total)
```bash
# 3. Trigger learning
curl -X POST https://your-app.railway.app/api/run-learning \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500255"}'

# Response shows:
# - Model predicted: 200.46 (17.54 points off!)
# - Sportsbook line: 221.5 (3.5 points off)
# - Line beat model → total_bias adjusted up by 0.105
# - Next time model will predict ~0.1 points higher
```

**Key insight:** Your model learned that it was predicting too low for this type of game. Over many games, it will gradually calibrate itself closer to market efficiency.

---

## Querying Your Data

You can query the SQLite database directly to analyze performance:

```python
import sqlite3

conn = sqlite3.connect('api/data/predictions.db')

# Get all predictions with learning complete
query = """
SELECT
    game_id,
    home_team,
    away_team,
    pred_total,
    sportsbook_total_line,
    actual_total,
    model_abs_error,
    line_abs_error,
    model_beat_line
FROM game_predictions
WHERE learning_completed_at IS NOT NULL
ORDER BY learning_completed_at DESC
LIMIT 20
"""

results = conn.execute(query).fetchall()
```

### Useful Queries

**Calculate your model's accuracy vs the line:**
```sql
SELECT
    COUNT(*) as total_games,
    AVG(model_abs_error) as avg_model_error,
    AVG(line_abs_error) as avg_line_error,
    SUM(CASE WHEN model_beat_line = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as model_win_rate
FROM game_predictions
WHERE learning_completed_at IS NOT NULL;
```

**Find games where your model beat the line:**
```sql
SELECT
    home_team,
    away_team,
    pred_total,
    sportsbook_total_line,
    actual_total,
    model_abs_error,
    line_abs_error
FROM game_predictions
WHERE model_beat_line = 1
ORDER BY (line_abs_error - model_abs_error) DESC
LIMIT 10;
```

---

## Railway Deployment Notes

### Database Persistence

The SQLite database (`api/data/predictions.db`) will persist across Railway restarts because:
1. It's stored in the filesystem
2. Railway's persistent disk keeps data between deployments
3. No additional database service needed (stays on $5/month plan)

### Environment Variables (Optional)

For GitHub model commits to work on Railway, set these in your Railway dashboard:

```
GH_TOKEN=ghp_your_github_personal_access_token
GH_REPO=your-username/your-repo-name
GH_MODEL_PATH=api/data/model.json
```

**Without these:** The system works fine locally, but model updates won't commit to GitHub. They'll still be saved to the local file.

### Checking Logs on Railway

```bash
# View real-time logs
railway logs

# Look for these indicators:
# [save-prediction] ✓ Saved prediction: 220.7 total
# [submit-line] ✓ Line submitted successfully
# [run-learning] ✓ Learning complete!
# [run-learning] ✓ Model committed to GitHub
```

---

## Advanced: Batch Processing

If you want to process multiple games at once, you can write a script:

```python
import requests
import time

BASE_URL = "https://your-app.railway.app"

# Get today's finished games
games_response = requests.get(f"{BASE_URL}/api/games").json()

for game in games_response['games']:
    if game['game_status'] == 'Final':
        game_id = game['game_id']

        # Check if we have a prediction for this game
        # If yes, run learning
        try:
            result = requests.post(
                f"{BASE_URL}/api/run-learning",
                json={"game_id": game_id}
            ).json()

            if result['success']:
                print(f"✓ Learned from {game_id}")
            else:
                print(f"✗ {game_id}: {result['error']}")
        except Exception as e:
            print(f"✗ {game_id}: {e}")

        time.sleep(1)  # Be nice to your API
```

---

## Monitoring Model Improvement

Track these metrics over time:

1. **Average Model Error**: Should decrease as the model learns
2. **Model Win Rate**: % of times your model beats the line (target: >50%)
3. **Total Bias**: Shows if model is systematically high/low
4. **Team Ratings**: Watch how ratings change after big wins/losses

Example analysis:

```python
# After 50 games
# avg_model_error: 8.5 points
# avg_line_error: 7.2 points
# model_win_rate: 42%
# total_bias: +1.2

# Interpretation:
# - Model is competitive (within 1.3 points of line on average)
# - Line still beats model 58% of the time (expected - books are sharp)
# - Model learned it was predicting 1.2 points too low on average
# - Keep learning - over hundreds of games, model should get closer to 50%
```

---

## Troubleshooting

### "No prediction found for game X"
- Make sure you called `/api/save-prediction` before the game started
- Check the `game_id` matches exactly

### "Game is not finished yet"
- Only run learning after game status = "Final"
- Check `/api/games` to verify status

### GitHub commit failed
- This is normal in local development without `GH_TOKEN`
- Model still updates locally (check `api/data/model.json`)
- On Railway, set `GH_TOKEN` environment variable

### Database locked error
- SQLite is single-writer
- Don't run multiple learning processes simultaneously
- Let one finish before starting another

---

## Future Enhancements

Ideas for extending this system:

1. **Automatic Learning**: Add a cron job to check for finished games every hour
2. **Context Features**: Learn from back-to-backs, pace, injuries
3. **Confidence Scores**: Predict not just totals but also uncertainty
4. **A/B Testing**: Compare this model against your complex prediction engine
5. **Bankroll Management**: Use the model win rate to size your bets

---

## Summary

You now have a complete self-learning system that:

✅ Stores predictions and outcomes in SQLite
✅ Compares your model vs sportsbook lines
✅ Updates team ratings and total bias based on performance
✅ Commits model updates to GitHub (optional)
✅ Tracks performance metrics over time
✅ Works seamlessly on Railway's $5/month plan

The system is intentionally simple, explainable, and maintainable. It won't replace the sportsbooks overnight, but over hundreds of games, it will gradually learn patterns and improve its accuracy.

**Next steps:**
1. Start saving predictions before each game
2. Enter sportsbook lines (from ESPN, FanDuel, DraftKings, etc.)
3. Run learning after games finish
4. After 20-30 games, check your performance stats
5. Watch your model improve!
