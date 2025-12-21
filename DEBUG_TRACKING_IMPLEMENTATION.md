# Debug Tracking Implementation - Summary

**Date:** December 6, 2024
**Status:** ✅ Complete

---

## Problem

The MIA vs SAC game was showing obvious fallback values:
- Home Projected: 110.0
- Away Projected: 110.0
- Game Pace: 100.0
- Total Difference: 0.0

This indicated the full v4.5 pipeline was not running and an exception was triggering the fallback path.

---

## Root Cause

**Error:** `NameError: name 'fatigue_penalty' is not defined`

**Location:** `api/utils/prediction_engine.py` line 1700

**Cause:** When we replaced STEP 8 (Fatigue Adjustment) with Back-to-Back Adjustment, we removed the `fatigue_penalty` variable but forgot to remove the code that referenced it in the result dict.

---

## Solution Implemented

### 1. Added Comprehensive Debug Tracking

**File:** `api/utils/prediction_engine.py`

Added `debug_info` dictionary at the start of `predict_game_total()`:

```python
debug_info = {
    'using_fallback': False,
    'fallback_reasons': [],
    'raw_inputs': {},
    'missing_data': []
}
```

### 2. Track Raw Inputs

Added after initial data extraction (line 846):

```python
debug_info['raw_inputs'] = {
    'home_team_id': home_team_id,
    'away_team_id': away_team_id,
    'game_id': game_id,
    'home_season_pace': home_season_pace if home_advanced and home_advanced.get('PACE') else None,
    'away_season_pace': away_season_pace if away_advanced and away_advanced.get('PACE') else None,
    'home_has_advanced': bool(home_advanced),
    'away_has_advanced': bool(away_advanced),
    'home_has_stats': bool(home_stats.get('overall')),
    'away_has_stats': bool(away_stats.get('overall')),
    'betting_line': betting_line
}
```

### 3. Track Missing Data

```python
if not home_advanced or not home_advanced.get('PACE'):
    debug_info['missing_data'].append('home_season_pace')
if not away_advanced or not away_advanced.get('PACE'):
    debug_info['missing_data'].append('away_season_pace')
```

### 4. Enhanced Exception Handler

Updated exception handler to:
- Print full traceback
- Set `using_fallback: true`
- Capture exception message in `fallback_reasons`

```python
except Exception as e:
    print(f"Error in predict_game_total: {str(e)}")
    import traceback
    traceback.print_exc()

    debug_info['using_fallback'] = True
    debug_info['fallback_reasons'].append(f'exception: {str(e)}')
```

### 5. Add Debug to Result Object

```python
# Add debug info to result
result['debug'] = debug_info

# Also add to fallback return
return {
    ...
    'error': str(e),
    'debug': debug_info
}
```

### 6. Fixed Fatigue Penalty Reference

Replaced the old fatigue_adjustment code with backward-compatible stub:

```python
# Note: Fatigue adjustment was replaced by B2B adjustment in STEP 8
# Legacy field kept for backward compatibility
result['fatigue_adjustment'] = {
    'penalty': 0.0,
    'explanation': 'Replaced by team-specific B2B adjustment',
    'total_before_fatigue': predicted_total
}
```

### 7. Updated Server Integration

**File:** `server.py`

Updated `get_cached_prediction()` to accept and pass `game_id`:

```python
def get_cached_prediction(home_team_id, away_team_id, betting_line, game_id=None):
    ...
    prediction = predict_game_total(
        ...
        game_id=game_id
    )
```

Updated `game_detail()` endpoint to pass `game_id`:

```python
prediction, matchup_data = get_cached_prediction(
    int(home_team_id),
    int(away_team_id),
    betting_line,
    game_id=game_id
)
```

---

## Debug Output Structure

### Normal Execution (No Fallback)

```json
{
  "debug": {
    "using_fallback": false,
    "fallback_reasons": [],
    "raw_inputs": {
      "home_team_id": 1610612748,
      "away_team_id": 1610612758,
      "game_id": "0022500354",
      "home_season_pace": 105.63,
      "away_season_pace": 102.02,
      "home_has_advanced": true,
      "away_has_advanced": true,
      "home_has_stats": true,
      "away_has_stats": true,
      "betting_line": 220.5
    },
    "missing_data": []
  }
}
```

### Fallback Triggered

```json
{
  "debug": {
    "using_fallback": true,
    "fallback_reasons": [
      "exception: name 'fatigue_penalty' is not defined"
    ],
    "raw_inputs": {
      ...
    },
    "missing_data": []
  },
  "error": "name 'fatigue_penalty' is not defined"
}
```

### Missing Data Detected

```json
{
  "debug": {
    "using_fallback": false,
    "fallback_reasons": [],
    "raw_inputs": {
      "home_season_pace": null,  // NULL value flagged
      ...
    },
    "missing_data": [
      "home_season_pace"
    ]
  }
}
```

---

## Test Results

### MIA vs SAC Game (0022500354)

**Before Fix:**
```
Predicted Total: 220.5 (fallback)
Home Projected: 110.0 (fallback)
Away Projected: 110.0 (fallback)
Game Pace: 100.0 (fallback)
Difference: 0.0 (fallback)

Debug: using_fallback: true
Reason: exception: name 'fatigue_penalty' is not defined
```

**After Fix:**
```
Predicted Total: 222.7 ✓
Home Projected: 126.5 ✓
Away Projected: 96.3 ✓
Game Pace: 103.1 ✓
Difference: 2.2 ✓

Debug: using_fallback: false
Missing Data: []
```

**Pipeline Steps Executed:**
- ✓ Smart Baseline
- ✓ STEP 1: Pace Adjustment
- ✓ STEP 2: Turnover Adjustment
- ✓ STEP 4: Defense Adjustment
- ✓ STEP 4B: Defense Quality Adjustment
- ✓ STEP 5: Home Court Advantage
- ✓ STEP 5B: Road Penalty
- ✓ STEP 6: Matchup Adjustments
- ✓ STEP 7: 3PT Shootout Detection
- ✓ STEP 8: Back-to-Back Adjustment

---

## Benefits

### 1. **Immediate Error Detection**
- Can see in JSON response if fallback was triggered
- Know exactly which exception caused the failure

### 2. **Missing Data Visibility**
- Track which critical inputs are null/missing
- Can add more granular checks as needed

### 3. **Input Validation**
- See all raw inputs that went into the model
- Verify team IDs, game ID, betting line

### 4. **Future Extensibility**
- Easy to add more debug flags
- Can track warnings, not just errors
- Can add step-by-step execution trace

---

## Future Enhancements (Optional)

### 1. **Step-by-Step Execution Trace**
```python
debug_info['steps_executed'] = [
    'smart_baseline',
    'pace_adjustment',
    'turnover_adjustment',
    ...
]
```

### 2. **Warning Flags**
```python
debug_info['warnings'] = [
    'small_sample_b2b',
    'limited_recent_games',
    ...
]
```

### 3. **Data Quality Score**
```python
debug_info['data_quality'] = {
    'home': 'good',  # good | limited | fallback
    'away': 'limited'
}
```

### 4. **Performance Metrics**
```python
debug_info['timing'] = {
    'total_ms': 1234,
    'steps': {
        'pace_calculation': 45,
        'defense_adjustment': 123,
        ...
    }
}
```

---

## Files Modified

### Modified (2 files):
1. `api/utils/prediction_engine.py`
   - Added `debug_info` tracking
   - Added `game_id` parameter
   - Enhanced exception handler
   - Fixed `fatigue_penalty` reference
   - Added debug to result object

2. `server.py`
   - Updated `get_cached_prediction()` to accept `game_id`
   - Updated `game_detail()` to pass `game_id`

### Created (1 file):
1. `test_debug_mia_sac.py` - Test script for debugging

---

## Conclusion

Successfully implemented comprehensive debug tracking throughout the prediction pipeline. The MIA vs SAC game now produces correct predictions instead of fallback values. The debug output clearly shows:

- Whether fallback was triggered
- What exception or missing data caused the issue
- All raw inputs to the model
- Success/failure status

This makes it trivial to diagnose future issues by simply looking at the `debug` field in the JSON response.

**Status:** ✅ Production Ready

---

*Generated: December 6, 2024*
*Issue: Fallback values (110/110/100)*
*Root Cause: Undefined fatigue_penalty variable*
*Fix: Removed legacy fatigue reference, added debug tracking*
*Test Result: MIA vs SAC now predicts 222.7 correctly*
