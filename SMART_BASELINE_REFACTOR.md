# Smart Baseline Refactor - Summary

## Overview
Refactored the prediction model to eliminate double-counting of recent form by creating a **single smart baseline** that blends season and recent performance adaptively.

## Problem Fixed

### Before (Double-Counting Issue)
```
1. Start with pure season average (115.3 PPG)
2. Apply pace, defense, turnover adjustments
3. THEN add separate recent form adjustment (+2.3 pts for hot team)
   → This double-counts recent trends!
```

### After (Smart Baseline)
```
1. Start with SMART BASELINE that already blends season + recent
   - Season: 115.3 PPG, Recent: 122.0 PPG
   - Trend: normal (70% season / 30% recent)
   - Baseline: 117.3 PPG ← Recent form already integrated!
2. Apply pace, defense, turnover adjustments
3. NO separate recent form step (it's already in the baseline)
```

## Implementation

### 1. New Function: `compute_baseline_ppg()`
**Location:** `api/utils/prediction_engine.py` (lines 35-77)

**Signature:**
```python
def compute_baseline_ppg(season_ppg, recent_ppg, recent_ortg_change):
    """
    Compute a smart baseline PPG that blends season and recent form.

    Returns: (baseline, trend_type, season_weight, recent_weight)
    """
```

**Logic:**
- **Extreme trend** (PPG change >10 OR ORTG change >8):
  - 60% season / 40% recent
  - Team clearly playing very differently

- **Normal trend** (PPG change >3 OR ORTG change >3):
  - 70% season / 30% recent
  - Noticeable shift in performance

- **Minimal trend** (otherwise):
  - 80% season / 20% recent
  - Team playing close to season average

**Example:**
```python
season_ppg = 115.3
recent_ppg = 122.0  # Hot streak
recent_ortg_change = 0.0

baseline, trend, s_wt, r_wt = compute_baseline_ppg(115.3, 122.0, 0.0)
# → baseline = 117.3 (70% × 115.3 + 30% × 122.0)
# → trend = "normal"
```

### 2. Smart Baseline Integration
**Location:** `api/utils/prediction_engine.py` (lines 575-655)

**Changes:**
- Moved baseline calculation BEFORE all adjustments
- Computes recent_ppg and recent_ortg_change from last 5 games
- Calls `compute_baseline_ppg()` for both teams
- Uses result as starting point for all subsequent adjustments

**New Logging:**
```
[prediction_engine] Smart Baseline (blends season + recent form):
  Home: 115.3 season, 122.0 recent (L5), ORTG Δ+0.0
    → normal trend (70% season / 30% recent) = 117.3 PPG
  Away: 120.2 season, 119.8 recent (L5), ORTG Δ+0.0
    → minimal trend (80% season / 20% recent) = 120.1 PPG
```

### 3. STEP 5 Disabled
**Location:** `api/utils/prediction_engine.py` (lines 863-876)

**Old STEP 5:**
```python
# Calculate recent PPG
# Apply 25-40% weight based on magnitude
# ADD to projected points ← DOUBLE-COUNTING!
home_projected += ppg_adjust
```

**New STEP 5:**
```python
# Recent form is now baked into the smart baseline.
# This prevents double-counting of trends.
print('STEP 5 - Recent form: ALREADY IN BASELINE (no additional adjustment)')
home_form_adjustment = 0.0  # Always 0
away_form_adjustment = 0.0
```

## Test Results

### BOS vs NYK (Line: 230.5)
```
Smart Baseline:
  Home (BOS): 115.3 season, 122.0 recent → normal trend → 117.3 baseline
  Away (NYK): 120.2 season, 119.8 recent → minimal trend → 120.1 baseline

After all adjustments:
  Home: 113.8 | Away: 108.7
  Total: 222.6 (vs line 230.5)

✓ Recent form adjustment: 0.0 / 0.0 (in baseline)
✓ Recommendation: UNDER
```

### GSW vs LAL (Line: 225.0)
```
Smart Baseline:
  Home (GSW): 114.4 season, 114.6 recent → minimal trend → 114.4 baseline
  Away (LAL): 119.1 season, 122.6 recent → normal trend → 120.1 baseline

After all adjustments:
  Home: 106.4 | Away: 111.4
  Total: 217.8 (vs line 225.0)

✓ Recent form adjustment: 0.0 / 0.0 (in baseline)
✓ Recommendation: UNDER
```

## Key Benefits

### ✅ Eliminates Double-Counting
- Recent form is counted ONCE in the baseline
- Not added again in STEP 5
- More accurate projections

### ✅ Adaptive to Trend Strength
- **Hot/Cold Teams:** 40% recent weight (trusts the trend)
- **Normal Trends:** 30% recent weight (balanced)
- **Noisy Data:** 20% recent weight (trust season more)

### ✅ Maintains Model Structure
- Pace, defense, turnover, matchup adjustments unchanged
- Applied on top of smart baseline
- No breaking changes to other components

### ✅ Better Projections
- Baselines are closer to reality when teams are hot/cold
- Baselines stay conservative when recent form is noisy
- Prevents wild swings from small sample sizes

## Pipeline Flow (Updated)

```
START: Smart Baseline
├─ Extract season PPG, recent PPG (L5), ORTG change
├─ Blend using trend-adaptive weights
└─ Result: home_baseline, away_baseline

STEP 1: Pace Adjustment
├─ Apply pace multiplier to baseline
└─ Result: home_projected, away_projected

STEP 2: Turnover Adjustment
├─ Add/subtract points for turnover matchup
└─ Result: adjusted projections

STEP 3: 3PT Data Collection
├─ Fetch 3PT splits (for shootout detection)
└─ No projection changes

STEP 4: Defense Adjustment (30% weight)
├─ Adjust for opponent defense tier
└─ Result: defense-adjusted projections

STEP 5: Recent Form - DISABLED
├─ NO ADJUSTMENT (already in baseline)
└─ form_adjustment = 0.0

STEP 6: Shootout Bonus - DISABLED
├─ Detection runs but no bonus applied
└─ shootout_bonus = 0.0

FINAL: home_projected + away_projected
```

## Files Modified

1. **api/utils/prediction_engine.py**
   - Added `compute_baseline_ppg()` function (lines 35-77)
   - Refactored baseline calculation (lines 575-655)
   - Updated STEP 1 logging (lines 657-669)
   - Disabled STEP 5 (lines 863-876)

2. **test_smart_baseline.py** (new file)
   - Comprehensive test for 3 matchups
   - Verifies form_adjustment = 0
   - Shows different trend types in action

## Verification

Run the test:
```bash
python3 test_smart_baseline.py
```

Expected output:
- Smart Baseline logs showing trend-adaptive weights
- STEP 5 showing "ALREADY IN BASELINE"
- form_adjustment = 0.0 for all teams
- ✓ checkmarks confirming recent form in baseline

## Migration Notes

### What Changed
- Baseline now includes recent form (no longer pure season average)
- STEP 5 is a no-op (doesn't modify projections)
- `home_form_adjustment` / `away_form_adjustment` are always 0

### What Stayed the Same
- All other adjustment steps (pace, defense, turnover)
- Confidence calculation logic
- Output structure (still has form_adjustment field, just = 0)
- Bet recommendation logic

### Breaking Changes
- None! The API is unchanged
- Existing code reading `form_adjustment` will see 0 instead of a value
- This is by design (form is in baseline now)

## Future Enhancements

Possible improvements (not implemented yet):
- [ ] Use more sophisticated ORTG weighting (currently just a threshold)
- [ ] Consider home/away splits in recent form calculation
- [ ] Add logging for "why" a team got a specific trend classification
- [ ] Tune threshold values based on historical accuracy

## Bottom Line

**Before:** Season baseline → adjustments → add recent form (double-count!)

**After:** Smart baseline (season + recent blended) → adjustments → done!

This produces more accurate baselines that already reflect whether teams are hot, cold, or playing normally, without the risk of double-counting recent trends.
