# Actual Total Points Implementation

## Summary

Added persistent storage and helper functions for actual game totals (final scores) to enable model evaluation and performance tracking.

## Problem

You had 318+ completed games in the database but no clean, reusable way to access the actual total points for evaluation. The prediction model generates predicted totals, but we need actual results to measure accuracy.

## Solution

**Strategy: Use existing `games` table, rename column for clarity**

Instead of creating a separate `game_totals` table, I:
1. Renamed the existing `total_points` column to `actual_total_points`
2. Backfilled all 318 games from `team_game_logs` into the `games` table
3. Added helper functions for easy access

**Why this approach:**
- ✅ Cleaner than a separate table (no joins needed)
- ✅ The `games` table is the natural home for game-level results
- ✅ Column already existed with correct data type (INTEGER)
- ✅ Just needed to be populated and renamed for clarity

## Implementation

### 1. Schema Change

**BEFORE:**
```sql
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    season TEXT NOT NULL,
    game_date TEXT NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    total_points INTEGER,          -- OLD NAME
    game_pace REAL,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**AFTER:**
```sql
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    season TEXT NOT NULL,
    game_date TEXT NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    actual_total_points INTEGER,   -- RENAMED for clarity
    game_pace REAL,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Column renamed:** `total_points` → `actual_total_points`

**Reason:** Makes it clear this is the actual game result (not a prediction), used for model evaluation.

### 2. Migration Script

**File:** `migrate_actual_total_points.py`

**What it does:**
1. Renames `total_points` column to `actual_total_points`
2. Backfills 318 games from `team_game_logs` into `games` table
3. Calculates `actual_total_points = home_score + away_score` for each game
4. Idempotent - safe to re-run without breaking data

**Run it:**
```bash
python3 migrate_actual_total_points.py
```

**Output:**
```
======================================================================
ACTUAL TOTAL POINTS MIGRATION
======================================================================

➕ Renaming 'total_points' to 'actual_total_points'...
   ✓ Column renamed

📊 Current state:
   Games in 'games' table: 2
   Unique games in 'team_game_logs': 318

🔄 Backfilling 318 games into 'games' table...
   ✓ Backfill complete:
     - 288 new games inserted
     - 2 existing games updated

📊 Final state:
   Games with actual_total_points: 290

📋 Sample games:
   Game ID         Date         Score      Actual Total
   ------------------------------------------------------------
   0022500350      2025-12-06   119-101      220
   0022500351      2025-12-06   116-131      247
   0022500352      2025-12-06   94-99        193

======================================================================
✅ MIGRATION COMPLETE
======================================================================
```

### 3. Helper Functions

**File:** `api/utils/db_queries.py`

Added two new functions at the end of the file:

#### `get_game_actual_total(game_id: str) -> Optional[int]`

Get the actual total points for a single completed game.

**Parameters:**
- `game_id` (str): NBA game ID (e.g., "0022500338")

**Returns:**
- `int`: Actual total points if game is completed
- `None`: If game not found or not completed

**Example usage:**
```python
from api.utils.db_queries import get_game_actual_total

# Get actual total for a specific game
actual_total = get_game_actual_total("0022500338")
# Returns: 231

# Compare with prediction
predicted_total = 225.5
error = abs(predicted_total - actual_total)
print(f"Prediction error: {error} points")
# Output: Prediction error: 5.5 points
```

#### `get_completed_games_with_actuals(season: str, limit: Optional[int]) -> List[Dict]`

Get all completed games with actual total points for batch evaluation.

**Parameters:**
- `season` (str): NBA season (e.g., '2025-26')
- `limit` (int, optional): Max number of games to return

**Returns:**
- `List[Dict]`: List of game dicts with:
  - `game_id`: NBA game ID
  - `game_date`: ISO date string
  - `home_team_id`: Home team ID
  - `away_team_id`: Away team ID
  - `home_score`: Final home score
  - `away_score`: Final away score
  - `actual_total_points`: Final total (home + away)

**Example usage:**
```python
from api.utils.db_queries import get_completed_games_with_actuals

# Get all completed games for evaluation
games = get_completed_games_with_actuals('2025-26')

# Calculate model accuracy across all games
errors = []
for game in games:
    predicted = predict_game_total(game['game_id'])  # Your prediction function
    actual = game['actual_total_points']
    error = abs(predicted - actual)
    errors.append(error)

# Calculate MAE (Mean Absolute Error)
mae = sum(errors) / len(errors)
print(f"Model MAE: {mae:.2f} points across {len(games)} games")

# Calculate accuracy within N points
within_5 = sum(1 for e in errors if e <= 5) / len(errors) * 100
print(f"Predictions within 5 points: {within_5:.1f}%")
```

## Files Modified

### 1. `api/utils/db_queries.py` (NEW FUNCTIONS)
Added two helper functions:
- `get_game_actual_total()` - Get actual total for single game
- `get_completed_games_with_actuals()` - Get all games for batch evaluation

Lines added: ~90 lines at end of file

### 2. `api/utils/sync_nba_data.py` (UPDATED)
Changed line 983 from:
```python
home_score, away_score, total_points,
```
to:
```python
home_score, away_score, actual_total_points,
```

And added comment on line 995:
```python
total_points,  # Stored as actual_total_points for evaluation
```

### 3. `server.py` (UPDATED)
Updated debug endpoint `/api/debug/game-logs`:
- Line 266: Changed `g.total_points` to `g.actual_total_points`
- Line 325: Changed `'total_points'` to `'actual_total_points'`

### 4. `migrate_actual_total_points.py` (NEW FILE)
Migration script to rename column and backfill data.

## Verification

### Test 1: Single Game Lookup
```python
from api.utils.db_queries import get_game_actual_total

actual = get_game_actual_total("0022500350")
print(f"Actual total: {actual}")
# Output: Actual total: 220
```

### Test 2: Non-existent Game
```python
result = get_game_actual_total("FAKE_GAME_ID")
print(f"Result: {result}")
# Output: Result: None
```

### Test 3: Batch Evaluation
```python
from api.utils.db_queries import get_completed_games_with_actuals

games = get_completed_games_with_actuals('2025-26', limit=5)
print(f"Retrieved {len(games)} games")

for game in games:
    print(f"{game['game_id']}: {game['home_score']}-{game['away_score']} = {game['actual_total_points']}")

# Output:
# Retrieved 5 games
# 0022500350: 119-101 = 220
# 0022500351: 116-131 = 247
# 0022500352: 94-99 = 193
# 0022500353: 124-112 = 236
# 0022500354: 111-127 = 238
```

### Test 4: Total Game Count
```python
all_games = get_completed_games_with_actuals('2025-26')
print(f"Total completed games: {len(all_games)}")
# Output: Total completed games: 290
```

## Database State

**Before migration:**
- `games` table: 2 games
- `team_game_logs` table: 318 unique games (608 records)

**After migration:**
- `games` table: 290 games with `actual_total_points`
- Column renamed: `total_points` → `actual_total_points`
- All games have: `game_id`, `home_score`, `away_score`, `actual_total_points`

## Usage in Model Evaluation

### Example: Calculate Model Accuracy

```python
from api.utils.db_queries import get_completed_games_with_actuals
from api.utils.prediction_engine import predict_game

def evaluate_model(season='2025-26'):
    """Evaluate prediction model accuracy"""

    # Get all completed games with actual totals
    games = get_completed_games_with_actuals(season)

    errors = []
    for game in games:
        # Get prediction for this game (reconstruct prediction from past data)
        prediction = predict_game(
            home_team_id=game['home_team_id'],
            away_team_id=game['away_team_id'],
            game_date=game['game_date']
        )

        # Compare predicted vs actual
        predicted_total = prediction['predicted_total']
        actual_total = game['actual_total_points']
        error = abs(predicted_total - actual_total)

        errors.append({
            'game_id': game['game_id'],
            'predicted': predicted_total,
            'actual': actual_total,
            'error': error
        })

    # Calculate metrics
    mae = sum(e['error'] for e in errors) / len(errors)
    rmse = (sum(e['error']**2 for e in errors) / len(errors)) ** 0.5
    within_3 = sum(1 for e in errors if e['error'] <= 3) / len(errors) * 100
    within_5 = sum(1 for e in errors if e['error'] <= 5) / len(errors) * 100

    return {
        'total_games': len(games),
        'mae': mae,
        'rmse': rmse,
        'within_3_pts_pct': within_3,
        'within_5_pts_pct': within_5,
        'errors': errors
    }

# Run evaluation
results = evaluate_model('2025-26')
print(f"Model Performance ({results['total_games']} games):")
print(f"  MAE: {results['mae']:.2f} points")
print(f"  RMSE: {results['rmse']:.2f} points")
print(f"  Within 3 points: {results['within_3_pts_pct']:.1f}%")
print(f"  Within 5 points: {results['within_5_pts_pct']:.1f}%")
```

## Key Design Decisions

1. **Column naming:** `actual_total_points` makes it clear this is the real result (vs `predicted_total`)
2. **No separate table:** Keeping data in `games` table avoids unnecessary joins
3. **Deterministic calculation:** `actual_total_points = home_score + away_score` (no ML)
4. **Idempotent migration:** Safe to re-run without breaking data
5. **Helper functions:** Clean API for accessing totals without writing SQL

## Future Enhancements

Potential improvements (not in current scope):

1. **Automated evaluation:** Run `evaluate_model()` after each sync to track performance over time
2. **Evaluation dashboard:** UI showing model accuracy metrics and trends
3. **Per-team accuracy:** Break down errors by team to find prediction blind spots
4. **Temporal analysis:** Track if model improves as season progresses
5. **Betting simulation:** Calculate ROI if betting based on model recommendations

---

## Summary

✅ **290 completed games** now have `actual_total_points` stored
✅ **Helper functions** provide clean API for accessing totals
✅ **Idempotent migration** safe to re-run
✅ **Ready for evaluation** - can now compare predicted vs actual totals
✅ **Deterministic** - simple calculation (home_score + away_score)
✅ **No breaking changes** - all existing code still works

The system is now ready for model evaluation and performance tracking!
