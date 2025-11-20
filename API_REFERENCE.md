# Self-Learning Feature - API Reference

## Endpoints

### POST /api/save-prediction

Save a pre-game prediction for later comparison.

**Request:**
```json
{
  "game_id": "0022500123",    // Required: NBA game ID
  "home_team": "BOS",          // Required: Home team tricode
  "away_team": "LAL"           // Required: Away team tricode
}
```

**Success Response (200):**
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

**Error Responses:**
- `400` - Missing required fields or invalid team tricode
- `400` - Prediction already exists for this game
- `500` - Server error

---

### POST /api/submit-line

Submit the sportsbook closing total line for a game.

**Request:**
```json
{
  "game_id": "0022500123",         // Required: NBA game ID
  "sportsbook_total_line": 218.5   // Required: Over/under line
}
```

**Success Response (200):**
```json
{
  "success": true,
  "game_id": "0022500123",
  "line": 218.5,
  "submitted_at": "2025-11-19T19:30:00Z"
}
```

**Error Responses:**
- `400` - Missing required fields
- `400` - sportsbook_total_line must be a number
- `404` - No prediction found for this game (must save prediction first)
- `500` - Server error

---

### POST /api/run-learning

Trigger post-game learning after a game completes.

**What it does:**
1. Fetches final score from NBA API
2. Compares model vs sportsbook line vs actual result
3. Updates team ratings (offense/defense)
4. Updates total_bias if line beat model
5. Saves error metrics to database
6. Commits updated model to GitHub (if configured)

**Request:**
```json
{
  "game_id": "0022500123"    // Required: NBA game ID
}
```

**Success Response (200):**
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

**Response Fields:**
- `actual_total`: Final total points scored
- `pred_total`: Model's pre-game prediction
- `sportsbook_line`: The line you submitted (if any)
- `model_error`: actual - predicted (negative = predicted too high)
- `line_error`: actual - line
- `model_beat_line`: true if |model_error| < |line_error|
- `total_bias_update`: How the bias parameter changed
- `updates`: New team ratings after learning
- `model_committed`: true if successfully committed to GitHub

**Success Response (without line):**

If you didn't submit a sportsbook line, the response will omit line-related fields:

```json
{
  "success": true,
  "game_id": "0022500123",
  "actual_total": 215.0,
  "pred_total": 220.7,
  "updates": {
    "BOS_off": 0.15,
    "BOS_def": -0.08,
    "LAL_off": 0.22,
    "LAL_def": -0.14
  },
  "model_committed": false
}
```

**Error Responses:**
- `400` - Missing game_id
- `404` - No prediction found (must save prediction first)
- `404` - Game not found in NBA API
- `400` - Game is not finished yet
- `500` - Failed to fetch from NBA API
- `500` - Server error

---

## Database Helper Functions

These functions are available in `api/utils/db.py`:

### `init_db()`
Initialize database schema. Called automatically on server startup.

### `save_prediction(game_id, home_team, away_team, game_date, pred_home, pred_away, pred_total, model_version)`
Save a prediction to the database.

### `submit_line(game_id, sportsbook_total_line)`
Update a prediction with the sportsbook line.

### `update_actual_results(game_id, actual_home, actual_away)`
Update actual game scores after game finishes.

### `update_error_metrics(game_id, metrics)`
Save error metrics after learning completes.

### `get_prediction(game_id)`
Retrieve prediction data for a specific game.

### `get_all_predictions(limit, offset)`
Get all predictions (paginated).

### `get_predictions_with_learning(limit)`
Get predictions that have completed learning.

### `get_model_performance_stats(days)`
Calculate aggregate performance metrics.

---

## Model Functions

These functions are available in `api/utils/team_ratings_model.py`:

### `predict_with_bias(home_tricode, away_tricode)`
Generate prediction using enhanced model with total_bias.

**Returns:**
```python
{
    'home_pts': 112.5,
    'away_pts': 108.2,
    'total_raw': 220.7,        # Before bias
    'total_bias': 0.5,         # Current bias
    'predicted_total': 221.2,  # With bias applied
    'home_pts_rounded': 113,
    'away_pts_rounded': 108,
    'model_version': '2.0'
}
```

### `update_ratings(home_tricode, away_tricode, home_pts_final, away_pts_final)`
Update team ratings using gradient descent (existing logic).

### `update_from_sportsbook_line(pred_total, sportsbook_line, actual_total)`
Update total_bias based on line comparison (NEW).

**Returns:**
```python
{
    'model_error': -5.7,
    'line_error': -3.5,
    'model_abs_error': 5.7,
    'line_abs_error': 3.5,
    'model_beat_line': False,
    'line_gap': -2.2,
    'old_total_bias': 0.0,
    'new_total_bias': 0.02,
    'bias_adjustment': 0.02,
    'updated_model': {...}  # Full model dict
}
```

### `get_total_bias()`
Get current total_bias value.

### `set_total_bias(value)`
Manually set total_bias (for testing).

---

## Example Usage (Python)

```python
import requests

BASE_URL = "https://your-app.railway.app"

# 1. Save prediction
response = requests.post(
    f"{BASE_URL}/api/save-prediction",
    json={
        "game_id": "0022500123",
        "home_team": "BOS",
        "away_team": "LAL"
    }
)
print(response.json())

# 2. Submit line
response = requests.post(
    f"{BASE_URL}/api/submit-line",
    json={
        "game_id": "0022500123",
        "sportsbook_total_line": 218.5
    }
)
print(response.json())

# 3. Run learning (after game finishes)
response = requests.post(
    f"{BASE_URL}/api/run-learning",
    json={
        "game_id": "0022500123"
    }
)
result = response.json()

if result['success']:
    print(f"Model error: {result['model_error']}")
    print(f"Line error: {result['line_error']}")
    print(f"Model beat line: {result['model_beat_line']}")
```

---

## Example Usage (curl)

```bash
# 1. Save prediction
curl -X POST https://your-app.railway.app/api/save-prediction \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500123", "home_team": "BOS", "away_team": "LAL"}'

# 2. Submit line
curl -X POST https://your-app.railway.app/api/submit-line \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500123", "sportsbook_total_line": 218.5}'

# 3. Run learning
curl -X POST https://your-app.railway.app/api/run-learning \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500123"}'
```

---

## Error Handling

All endpoints return JSON with a consistent structure:

**Success:**
```json
{
  "success": true,
  ...
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message here"
}
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (missing/invalid parameters)
- `404` - Resource not found (game, prediction, etc.)
- `500` - Server error

---

## Rate Limiting

No rate limiting is currently implemented, but recommended practices:
- Don't hammer the endpoints with rapid requests
- Add 1-2 second delays between batch operations
- The NBA API has built-in caching (30 min for games)

---

## Testing Locally

Start the server:
```bash
cd "/Users/malcolmlittle/NBA OVER UNDER SW"
python3 server.py
```

Use `localhost:8080` as the base URL:
```bash
curl -X POST http://localhost:8080/api/save-prediction \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500255", "home_team": "LAC", "away_team": "HOU"}'
```

---

## Database Schema Reference

### game_predictions
```sql
CREATE TABLE game_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT UNIQUE NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_date TEXT NOT NULL,
    pred_total REAL NOT NULL,
    pred_home REAL NOT NULL,
    pred_away REAL NOT NULL,
    sportsbook_total_line REAL,
    actual_home REAL,
    actual_away REAL,
    actual_total REAL,
    model_error REAL,
    line_error REAL,
    model_abs_error REAL,
    line_abs_error REAL,
    model_beat_line INTEGER,
    prediction_created_at TEXT NOT NULL,
    line_submitted_at TEXT,
    learning_completed_at TEXT,
    model_version TEXT
);
```

### model_performance
```sql
CREATE TABLE model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    games_predicted INTEGER,
    avg_model_error REAL,
    avg_line_error REAL,
    model_win_rate REAL,
    created_at TEXT NOT NULL
);
```
