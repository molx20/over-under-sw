# Dynamic Home Court Advantage Implementation

**Date:** December 6, 2024
**Version:** 4.1
**Status:** ✅ Implemented and Tested

## Overview

Replaced the static 2.5-point home court advantage with a dynamic calculation that ranges from 0-6 points based on:
- Home team's home win percentage
- Away team's road win percentage
- Home team's momentum (last 3 home games)

## Implementation Details

### New Files Created

1. **`api/utils/home_court_advantage.py`**
   - Core calculation function
   - Implements the dynamic HCA formula with 0-6 point range
   - Includes comprehensive docstrings

2. **`api/utils/home_court_stats.py`**
   - Queries database for home/road records
   - Calculates win percentages from `team_game_logs` table
   - Gets last 3 home games performance

3. **`test_home_court_advantage.py`**
   - Comprehensive test suite
   - Tests 6 different scenarios
   - Validates clamping behavior

### Modified Files

1. **`api/utils/prediction_engine.py`**
   - Added STEP 5: Home Court Advantage (Dynamic)
   - Renumbered subsequent steps (STEP 6-8)
   - Integrated HCA calculation into prediction pipeline
   - Added fallback to static 2.5 pts if calculation fails
   - Added `home_court_advantage` to breakdown results

2. **`PREDICTION_MODEL_DOCUMENTATION.md`**
   - Updated version to 4.1
   - Added comprehensive STEP 5 documentation
   - Updated pipeline order (now 9 steps)
   - Added formula explanation with examples
   - Updated version history
   - Updated complete pipeline example

## Formula

```python
Base_Home_Advantage = 2.5

# Factor 1: Home record strength (±1.5 pts at extremes)
Home_Record_Multiplier = (home_win_pct - 0.500) * 3

# Factor 2: Opponent road weakness (±1.0 pts at extremes)
Road_Weakness_Multiplier = (0.500 - road_win_pct) * 2

# Factor 3: Recent momentum (±1.0 pts)
IF last3_home_wins >= 2:
    Home_Momentum = +1.0  # Hot at home
ELSE IF last3_home_wins == 0:
    Home_Momentum = -1.0  # Cold at home
ELSE:
    Home_Momentum = 0     # Neutral

# Final calculation
HCA = Base_Home_Advantage * (1 + Home_Record_Multiplier + Road_Weakness_Multiplier) + Home_Momentum

# Clamp to valid range
HCA = max(0, min(6, HCA))
```

## Test Results

All 6 test scenarios passed:

| Scenario | Home Record | Road Record | Last 3 | Expected | Actual | Status |
|----------|-------------|-------------|--------|----------|--------|--------|
| Elite vs Weak, Hot | 0.800 | 0.320 | 3/3 | ~6.0 | 6.0 | ✅ |
| Average vs Average | 0.500 | 0.500 | 1/3 | ~2.5 | 2.5 | ✅ |
| Weak vs Strong, Cold | 0.320 | 0.720 | 0/3 | ~0.0 | 0.0 | ✅ |
| Strong vs Average, Hot | 0.650 | 0.435 | 2/3 | 4-5 | 5.0 | ✅ |
| Upper Bound Clamp | 1.000 | 0.000 | 3/3 | 6.0 | 6.0 | ✅ |
| Lower Bound Clamp | 0.000 | 1.000 | 0/3 | 0.0 | 0.0 | ✅ |

## Integration into Prediction Pipeline

The dynamic HCA is now **STEP 5** in the pipeline:

1. Smart Baseline
2. Pace Adjustment
3. Turnover Adjustment
4. Defense Adjustment (Dynamic)
5. **Home Court Advantage (Dynamic)** ← NEW
6. Matchup Adjustments
7. Shootout Detection (DISABLED)
8. Fatigue/Rest Adjustment

Applied **only to the home team** as a positive adjustment.

## Example Output

```
[prediction_engine] STEP 5 - Home Court Advantage (Dynamic):
  Home team record at home: 15-8 (65.2%)
  Away team record on road: 10-13 (43.5%)
  Home team last 3 home games: 2/3 wins
  Home court advantage: +5.0 pts to home team
  Home: 115.1 + 5.0 = 120.1 | Away: 108.7
```

## Impact Analysis

### Before (Static 2.5 pts):
- Every home team got exactly 2.5 points regardless of context
- Warriors at Chase Center vs Pistons: +2.5 pts
- Trail Blazers at home vs Nuggets: +2.5 pts
- **Problem:** Didn't reflect reality of home court strength

### After (Dynamic 0-6 pts):
- Elite home team vs weak road team: 5-6 pts
- Average matchup: ~2.5 pts (maintains baseline)
- Weak home team vs elite road team: 0-1 pts
- **Benefit:** Accurately reflects actual home court impact

## Data Sources

All data comes from the `team_game_logs` table in `nba_data.db`:
- **home_win_pct:** COUNT(wins) / COUNT(games) WHERE is_home = 1
- **road_win_pct:** COUNT(wins) / COUNT(games) WHERE is_home = 0
- **last3_home_wins:** Recent 3 home games ordered by game_date DESC

## Error Handling

If the calculation fails for any reason:
1. Logs error to console
2. Falls back to static 2.5-point advantage
3. Prediction continues without interruption
4. User sees: "Using fallback static home advantage: +2.5 pts"

## Future Enhancements (Optional)

Potential improvements for future versions:
- Consider time zone differences for cross-country games
- Factor in altitude (Denver effect)
- Account for back-to-back home/road situations
- Include rest days difference between teams
- Add playoff intensity multiplier

## Validation Checklist

- [x] Function implementation complete
- [x] Database queries working
- [x] Integration into prediction_engine.py
- [x] Test suite passing
- [x] Documentation updated
- [x] Error handling implemented
- [x] Clamping behavior verified
- [x] Pipeline order corrected

## Files Changed Summary

```
Created:
  ✓ api/utils/home_court_advantage.py
  ✓ api/utils/home_court_stats.py
  ✓ test_home_court_advantage.py
  ✓ DYNAMIC_HOME_COURT_ADVANTAGE.md (this file)

Modified:
  ✓ api/utils/prediction_engine.py
  ✓ PREDICTION_MODEL_DOCUMENTATION.md
```

## Conclusion

The dynamic home court advantage feature has been successfully implemented and tested. It provides a more accurate, context-aware adjustment that reflects the reality of NBA home court advantage based on team performance and momentum.

**Ready for production use.** ✅
