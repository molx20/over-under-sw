# Deterministic Prediction System (v4.0)

## Summary

The NBA Over/Under prediction system has been converted from a self-learning system to a **100% deterministic analytics-based system**. All automated parameter learning has been removed.

---

## What Was Removed

### 1. Learning Files (Deleted)
- `api/utils/auto_learning.py` - Automated learning orchestration
- `api/utils/scheduler.py` - Hourly background scheduler
- `api/utils/github_persistence.py` - GitHub model commits
- `AUTO_LEARNING_GUIDE.md` - Learning documentation
- `LEARNING_MODEL_README.md` - Model documentation
- `IMPLEMENTATION_SUMMARY.md` - Implementation docs
- `SELF_LEARNING_GUIDE.md` - Self-learning guide

### 2. Learning Endpoints (Removed)
- `POST /api/run-learning` - Manual learning trigger
- `POST /api/auto-learning/run` - Auto-learning cycle
- `POST /api/auto-learning/save-predictions` - Auto-save predictions
- `POST /api/auto-learning/run-learning` - Auto-run learning

### 3. Learning Logic (Removed)
- **Team Rating Updates**: Gradient descent on offensive/defensive ratings
- **Feature Weight Learning**: Gradient descent on 9 feature weights
- **Sportsbook Line Learning**: Adjusting total_bias toward market wisdom
- **Background Scheduler**: Hourly automated learning cycle

### 4. Model Parameters (Removed from model.json)
- `learning_rate: 0.02`
- `line_learning_rate: 0.005`
- `feature_learning_rate: 0.01`
- `total_bias: 0.21`
- `feature_weights: {...}` (entire section)
- `teams: {...}` (learned off/def ratings)

### 5. Functions Removed
- `team_ratings_model.update_ratings()` - Gradient descent
- `team_ratings_model.update_from_sportsbook_line()` - Line learning
- `feature_builder.compute_feature_correction()` - Apply learned weights

### 6. UI Changes
- Removed "Automated Learning System" dashboard from admin.html
- Removed "Run Post-Game Learning" section
- Updated labels to reflect deterministic mode
- Removed auto-learning JavaScript functions

---

## What Was Preserved

### Core Prediction Engine
✅ **prediction_engine.py** - Complex deterministic prediction system
- Uses NBA API stats (OFF_RTG, DEF_RTG, PACE, PPG)
- Recent form analysis (last N games)
- Home court advantage calculations
- All calculations are deterministic

✅ **team_rankings.py** - Live NBA stats
- Fetches current season stats from NBA API
- Refreshes every 6 hours
- Provides OFF_RTG, DEF_RTG for team ratings
- Completely deterministic (no learning)

✅ **Opponent Profile Adjustments**
- Historical matchup analytics
- Deterministic adjustments based on opponent strength
- No gradient descent or learning

✅ **Feature Vector Calculations**
- Still builds feature vectors for analytics
- Shows recent form, matchup profiles
- Saved to database for analysis
- **No learned weights applied** (feature_correction = 0)

### Database Tables
✅ **All historical data preserved**:
- `game_predictions` - Complete prediction history
- `model_performance` - Aggregate stats
- `team_game_history` - Game-by-game history
- `matchup_profile_cache` - Opponent profiles

**Note**: Deprecated columns (feature_vector, learning_completed_at, etc.) are marked in code but kept for historical analysis.

### API Endpoints (Still Working)
✅ `GET /api/games` - Today's games
✅ `GET /api/game_detail?game_id=X` - Game predictions
✅ `POST /api/save-prediction` - Generate prediction
✅ `POST /api/submit-line` - Save sportsbook line (for tracking)
✅ `GET /api/prediction-history` - View historical predictions

---

## New Prediction Flow (Deterministic)

```
1. Base Prediction (from prediction_engine.py)
   ├─ NBA API stats via team_rankings.py
   │  ├─ OFF_RTG, DEF_RTG (advanced ratings)
   │  ├─ PPG, PACE (basic stats)
   │  └─ Refreshed every 6 hours from live NBA data
   ├─ Recent form (last N games from NBA API)
   ├─ Home court advantage (+2.5 pts)
   └─ → base_total

2. Opponent Profile Adjustment (deterministic)
   ├─ Historical performance vs opponent strength
   ├─ Matchup-specific context from team_game_history
   └─ → opponent_adjustment

3. Final Prediction = base_total + opponent_adjustment
```

**Key characteristics**:
- Same inputs → Same outputs (100% deterministic)
- model.json never changes after startup
- No runtime parameter updates
- No background learning processes

---

## Configuration (model.json v4.0)

```json
{
  "version": "4.0-deterministic",
  "last_updated": "2025-11-29T00:00:00Z",
  "description": "Deterministic prediction system using NBA API stats (no self-learning)",
  "parameters": {
    "base": 100,
    "hca": 2,
    "recent_games_n": 10
  }
}
```

**Static constants**:
- `base: 100` - Base points per team
- `hca: 2` - Home court advantage
- `recent_games_n: 10` - Number of recent games to analyze

---

## Deployment Notes

### What to Expect
1. **Startup message**:
   ```
   [startup] Running in deterministic mode (no automated learning)
   ```

2. **No background processes**: No hourly scheduler running

3. **Consistent predictions**: Same game data always produces same prediction

4. **No model.json updates**: File never changes during runtime

### Testing Deterministic Behavior

Test same inputs produce same outputs:
```bash
# Make two predictions for same game
curl -X POST http://localhost:8080/api/save-prediction \
  -H "Content-Type: application/json" \
  -d '{"game_id": "0022500123", "home_team": "BOS", "away_team": "LAL"}'

# Second call should return identical prediction
```

### What Changed for Users
- **Predictions are faster** (no learning overhead)
- **More transparent** (pure analytics, no black box)
- **Still accurate** (complex engine uses live NBA stats)
- **Historical data intact** (can analyze past performance)

---

## Files Modified

1. **server.py**:
   - Removed learning endpoints (lines 754-1031, 1070-1141)
   - Updated startup logic (removed scheduler)
   - Updated save_prediction to set feature_correction=0

2. **api/utils/feature_builder.py**:
   - Removed `compute_feature_correction()` function
   - Kept `build_feature_vector()` for analytics

3. **api/data/model.json**:
   - Removed all learned parameters
   - Kept only static constants

4. **api/utils/db.py**:
   - Added deprecation comments to schema

5. **public/admin.html**:
   - Removed auto-learning UI
   - Removed learning JavaScript functions
   - Updated labels to "Deterministic" mode

---

## Migration Complete

The system is now a **pure analytics engine** using:
- ✅ Live NBA stats (refreshed every 6 hours)
- ✅ Recent form analysis
- ✅ Opponent matchup profiles
- ✅ Deterministic calculations

**No more**:
- ❌ Gradient descent
- ❌ Parameter learning
- ❌ Background schedulers
- ❌ GitHub model commits
- ❌ Runtime model updates

---

## Questions?

For implementation details, see:
- `/Users/malcolmlittle/.claude/plans/deep-exploring-bunny.md` - Full implementation plan
- `api/utils/prediction_engine.py` - Core prediction logic
- `api/utils/team_rankings.py` - NBA API stats source
