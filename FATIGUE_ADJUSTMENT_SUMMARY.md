# Fatigue / Rest Adjustment - Implementation Summary

## Overview
Added a new **STEP 7: Fatigue Adjustment** to the prediction pipeline that applies penalties to the final game total based on rest days and recent game intensity.

## Integration Point
- **Location:** `api/utils/prediction_engine.py`
- **Position:** After all team projections are calculated, before final result is returned
- **Executes:** Between STEP 6 (Shootout detection) and final prediction output

## Implementation Details

### 1. New Helper Function: `apply_fatigue_penalty()`
**Location:** Lines 391-516 in `prediction_engine.py`

**Signature:**
```python
def apply_fatigue_penalty(predicted_total, home_recent_games, away_recent_games):
    """
    Apply fatigue-based penalty to the final predicted total.

    Returns: (adjusted_total, penalty_applied, explanation)
    """
```

**Parameters:**
- `predicted_total`: The unadjusted predicted total (home + away)
- `home_recent_games`: List of home team's recent games (most recent first)
- `away_recent_games`: List of away team's recent games (most recent first)

**Returns:**
- `adjusted_total`: Predicted total after fatigue penalty
- `penalty`: Points deducted (0, 4, or 7)
- `explanation`: Human-readable reason for penalty

### 2. Penalty Rules

#### Constants (easy to tune):
```python
B2B_PENALTY = 4.0              # Normal back-to-back penalty
OT_SHOOTOUT_PENALTY = 7.0      # Extreme game penalty
SHOOTOUT_THRESHOLD = 280       # Combined points threshold
```

#### Rule 1: Extreme Recent Game (Priority)
**Condition:** Either team played within 2 days AND that game had:
- Combined total ≥ 280 points (shootout), OR
- Combined total ≥ 270 points (likely OT)

**Penalty:** -7 points from final total

**Example:**
```
Home team played 2 days ago: 145-140 (285 total)
Penalty: -7 points
Explanation: "Home team played extreme game 2d ago (285 pts, shootout)"
```

#### Rule 2: Back-to-Back Game
**Condition:** At least one team played yesterday (1 day ago) AND previous game was NOT extreme

**Penalty:** -4 points from final total

**Example:**
```
Away team played yesterday: 110-105 (215 total, normal)
Penalty: -4 points
Explanation: "Away team on back-to-back"
```

If both teams on B2B:
```
Explanation: "Both teams on back-to-back"
```

#### Rule 3: Well-Rested
**Condition:** Both teams have 2+ days rest OR no recent game data

**Penalty:** 0 points (no adjustment)

**Example:**
```
Home: 3 days rest, Away: 4 days rest
Penalty: 0 points
Explanation: "Well-rested teams (Home: 3d, Away: 4d rest)"
```

### 3. Pipeline Integration

**Location:** Lines 1290-1313 in `prediction_engine.py`

```python
# Calculate base total
predicted_total_before_fatigue = home_projected + away_projected

# STEP 7: Apply fatigue adjustment
predicted_total, fatigue_penalty, fatigue_explanation = apply_fatigue_penalty(
    predicted_total_before_fatigue,
    home_data.get('recent_games', []),
    away_data.get('recent_games', [])
)

# Log the adjustment
if fatigue_penalty > 0:
    print(f'  {fatigue_explanation}')
    print(f'  Penalty: -{fatigue_penalty:.1f} pts')
    print(f'  Total: {predicted_total_before_fatigue:.1f} → {predicted_total:.1f}')
```

### 4. Result Structure

Added to prediction result (lines 1430-1435):

```python
result['fatigue_adjustment'] = {
    'penalty': round(fatigue_penalty, 1),
    'explanation': fatigue_explanation,
    'total_before_fatigue': round(predicted_total_before_fatigue, 1)
}
```

## Data Sources

### Recent Games Data
Uses existing `home_data['recent_games']` and `away_data['recent_games']` which include:
- `GAME_DATE`: Date of game (format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- `PTS`: Team's points
- `OPP_PTS`: Opponent's points

### Rest Calculation
```python
def get_days_since_last_game(recent_games):
    # Parses GAME_DATE from most recent game
    # Calculates days between that date and today
    # Returns: days_rest (int) or None
```

### Extreme Game Detection
```python
def was_extreme_game(recent_games):
    # Checks most recent game's combined total
    # Returns: (is_extreme, total_points, game_type)
    # Types: 'shootout' (280+), 'likely_ot' (270+), 'normal', 'none'
```

## Test Results

### Unit Tests (`test_fatigue_adjustment.py`)
All 7 tests pass:

1. ✓ Well-rested teams (3d, 4d rest) → No penalty
2. ✓ Home team B2B (1d rest) → -4 points
3. ✓ Both teams B2B → -4 points
4. ✓ Recent 280+ game (2d ago, 285 pts) → -7 points
5. ✓ Recent likely OT (1d ago, 275 pts) → -7 points
6. ✓ B2B with extreme game (1d ago, 290 pts) → -7 points (not -4)
7. ✓ No recent data → No penalty

### Integration Test (`test_fatigue_integration.py`)
✓ BOS vs NYK prediction runs successfully
✓ NYK on back-to-back detected
✓ -4 point penalty applied (222.6 → 218.6)
✓ Result includes fatigue_adjustment field

## Example Output

### Console Logs
```
[prediction_engine] STEP 7 - Fatigue adjustment:
  Away team on back-to-back
  Penalty: -4.0 pts
  Total: 222.6 → 218.6
[prediction_engine] FINAL PREDICTION: 218.6 (Home: 113.8 + Away: 108.7, Fatigue: -4.0)
```

### API Response
```json
{
  "predicted_total": 218.6,
  "breakdown": {
    "home_projected": 113.8,
    "away_projected": 108.7
  },
  "fatigue_adjustment": {
    "penalty": 4.0,
    "explanation": "Away team on back-to-back",
    "total_before_fatigue": 222.6
  }
}
```

## Files Modified

### 1. `api/utils/prediction_engine.py`
**Changes:**
- Added `apply_fatigue_penalty()` helper function (lines 391-516)
- Integrated STEP 7 into pipeline (lines 1290-1313)
- Added fatigue_adjustment to result dict (lines 1430-1435)

**Lines added:** ~160 (including docstrings and comments)

### 2. Created Test Files
- `test_fatigue_adjustment.py` - Unit tests for fatigue logic
- `test_fatigue_integration.py` - Integration test with real predictions
- `FATIGUE_ADJUSTMENT_SUMMARY.md` - This documentation

## Benefits

1. **Context-Aware:** Accounts for real-world fatigue factors (B2B, extreme games)
2. **Transparent:** Clear penalties with human-readable explanations
3. **Conservative:** Only applies when data supports it (no penalty if no data)
4. **Tunable:** Constants clearly defined and easy to adjust
5. **Non-Invasive:** Doesn't change team projections, only final total

## Edge Cases Handled

1. **No recent games data:** Returns 0 penalty with explanation
2. **Date parsing errors:** Handles both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS formats
3. **Missing field data:** Safe dict access with `.get()` fallbacks
4. **Priority rules:** Extreme game penalty (7) overrides B2B penalty (4)
5. **Both teams affected:** Only applies one penalty (not double-counted)

## Future Enhancements

Potential improvements (not implemented):
- [ ] Actual OT flag from game data (currently inferred from 270+ total)
- [ ] Travel distance consideration (cross-country vs local games)
- [ ] Third game in 4 nights detection
- [ ] Altitude adjustment for Denver home games
- [ ] Rest differential between teams (e.g., 1d rest vs 5d rest)

## Tuning Guide

To adjust penalty values, edit constants in `apply_fatigue_penalty()`:

```python
# Conservative (less aggressive penalties)
B2B_PENALTY = 3.0
OT_SHOOTOUT_PENALTY = 5.0
SHOOTOUT_THRESHOLD = 285

# Aggressive (more aggressive penalties)
B2B_PENALTY = 5.0
OT_SHOOTOUT_PENALTY = 9.0
SHOOTOUT_THRESHOLD = 275
```

To adjust thresholds:

```python
# Stricter B2B detection (only same-day games)
home_is_b2b = (home_days_rest == 0)

# Include 3-in-4 nights as fatigue
home_played_within_four_days = (home_days_rest <= 4)
```

## Verification Commands

Run unit tests:
```bash
python3 test_fatigue_adjustment.py
```

Run integration test:
```bash
python3 test_fatigue_integration.py
```

Check specific game:
```bash
# View STEP 7 logs in prediction output
python3 test_fatigue_integration.py 2>&1 | grep -A 5 "STEP 7"
```

## Summary

The fatigue adjustment system is now fully integrated into the prediction pipeline as **STEP 7**, positioned strategically after all team-level adjustments but before the final result. It applies conservative, data-driven penalties (0, -4, or -7 points) to account for back-to-back games and extreme recent game fatigue, making predictions more accurate for fatigued teams.
