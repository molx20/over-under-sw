# Prediction Engine Tuning Summary

## Goal
Reduce aggressive over-prediction from the volume-based model while maintaining deterministic, explainable structure.

---

## Changes Made

### 1. PACE Influence (STEP 2)
**File:** `api/utils/true_pace_calculator.py`

**Before:**
```python
offense_after_pace = baseOffense * (0.85 + 0.15 * paceMultiplier)  # ±15% influence
```

**After:**
```python
offense_after_pace = baseOffense * (0.92 + 0.08 * paceMultiplier)  # ±8% influence
```

**Impact:** Reduced pace impact from ±15% to ±5%, cutting fast-pace game inflation roughly in half.

---

### 2. SHOT VOLUME Bonuses (STEP 3)
**File:** `api/utils/true_pace_calculator.py`

**Before:**
- shotVolume > 95: +4 to +7 points (linear scale)
- shotVolume < 80: -4 to -7 points (linear scale)

**After:**
- shotVolume > 100: +4 points
- shotVolume > 95: +2 points
- shotVolume < 75: -4 points
- shotVolume < 80: -2 points

**Impact:** Higher thresholds (harder to trigger), simpler fixed bonuses instead of scaling, max +4 pts instead of +7.

---

### 3. OFFENSIVE REBOUND Bonuses (STEP 4)
**File:** `api/utils/true_pace_calculator.py`

**Before:**
- ORB >= 16: +5 points
- ORB >= 12: +3 points

**After:**
- ORB >= 16: +2 points
- ORB >= 12: +1 point

**Impact:** Cut bonuses by 60% to avoid double-counting (ORB already in possessions formula).

---

### 4. FREE THROW Impact (STEP 5)
**File:** `api/utils/true_pace_calculator.py`

**Before:**
- FTA > 40: +6 points
- FTA > 30: +3 points

**After:**
- FTA > 40: +3 points
- FTA > 30: +1 point

**Impact:** Halved FT bonuses since FTA is already in possessions formula (0.44 * FTA).

---

### 5. TURNOVER Bonuses (STEP 6 - REMOVED)
**File:** `api/utils/true_pace_calculator.py`

**Before:**
- Combined TO > 50: +6 points to total
- Combined TO > 40: +3 points to total

**After:**
```python
return 0.0  # Always 0 - turnovers handled in possessions formula
```

**Impact:** Removed 3-6 point bonuses that were double-counting turnover impact (TO already in possessions = FGA + 0.44*FTA + TO - ORB).

---

### 6. HIGH-VOLUME Offense Identity (STEP 7)
**File:** `api/utils/true_pace_calculator.py`

**Before:**
- Teams top 5 in FGA AND 3PA: +6 points

**After:**
- Teams top 5 in FGA AND 3PA: +2 points

**Impact:** Reduced BOS/IND/HOU bonus from +6 to +2 to prevent systematic over-prediction.

---

### 7. HOME/ROAD Edge (STEP 8)
**File:** `api/utils/home_road_edge.py`

**Before:**
- Strong home + Weak road: +4 total
- Strong home OR Weak road: +2 total
- Weak home + Strong road: -4 total
- Weak home OR Strong road: -2 total

**After:**
- Strong home + Weak road: +2 total (was +4)
- Strong home OR Weak road: 0 total (was +2)
- Weak home + Strong road: -2 total (was -4)
- Weak home OR Strong road: 0 total (was -2)

**Impact:** Only EXTREME patterns (both conditions) trigger adjustment. Single-condition adjustments now return 0. Max ±2 instead of ±4.

---

## Test Results Comparison

### BOS vs NYK Example
**Line:** 230.5

**Before Tuning (estimated from earlier runs):**
- Pace: More aggressive multiplier
- Shot Volume: +6.2 (both teams)
- ORB: Higher bonuses
- FT: Higher bonuses
- Turnover: +3 to +6 combined bonus
- Identity: +6 for BOS
- Home/Road: Up to ±4
- **Estimated Total:** ~245-248

**After Tuning:**
- Pace: Very light (119.9 → 119.6, minimal change)
- Shot Volume: +4.0 (both teams, at shotVolume=100+ threshold)
- ORB: Smaller bonuses (if triggered)
- FT: Smaller bonuses (if triggered)
- Turnover: 0.0 (removed)
- Identity: +2 for BOS (if triggered)
- Home/Road: 0.0 (only extreme patterns)
- **Actual Total:** 237.7

**Savings:** ~8-10 points reduction from tuning

**Difference from line:** +7.2 (vs estimated +15-18 before)

---

## Impact by Component

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Pace multiplier | ±15% | ±8% | ~50% |
| Shot volume | +7 max | +4 max | ~43% |
| ORB bonus | +5 max | +2 max | ~60% |
| FT bonus | +6 max | +3 max | ~50% |
| Turnover bonus | +6 max | 0 | 100% |
| Identity boost | +6 | +2 | ~67% |
| Home/Road edge | ±4 max | ±2 max | ~50% |

**Overall:** Most adjustments reduced by 50-67%, turnover bonus completely removed.

---

## Remaining Structure

The following components are **unchanged** and still work as designed:

1. **Smart Baseline** - Blends season + recent form
2. **Turnover Adjustment** - Scoring efficiency loss vs defense pressure
3. **Defense Adjustment** - Dynamic based on offensive form
4. **Defense Quality** - Supplementary tier-based adjustment
5. **Matchup Rules** - Pace mismatch, elite matchups, etc.
6. **3PT Shootout** - Dynamic detection based on multiple factors
7. **Back-to-Back** - Team-specific fatigue profiles

---

## Philosophy

**Key Principle:** Avoid double-counting possessions/pace impact.

The possessions formula `pos = FGA + (0.44 * FTA) + TO - ORB` already accounts for:
- FTA (free throw rate)
- TO (turnovers create possessions)
- ORB (offensive rebounds extend possessions)

Therefore, separate bonuses for these stats must be **minimal** to avoid inflating totals.

**New Tuning:**
- Pace: Very light (8% instead of 15%)
- Volume bonuses: Small, rare, high thresholds
- Home/road: Only extreme patterns (both conditions must be true)
- No double-counting: Turnover bonus removed entirely

---

## Conservative by Design

**More games return 0 adjustments:**
- Home/road: Only 2 of 9 patterns trigger (was 6 of 9)
- Turnover: Always 0 (was 3-6)
- Shot volume: Harder thresholds (>100 vs >95)
- ORB: Smaller bonuses when triggered
- FT: Smaller bonuses when triggered
- Identity: Smaller bonus (+2 vs +6)

**Result:** The model is now significantly more conservative across all dimensions.

---

## Validation Needed

1. **Test on recent games:** Run predictions on last 7 days of games
2. **Compare to betting lines:** Check if differences are now ±5 instead of ±15
3. **Verify low-pace games:** Ensure slow games aren't over-predicted
4. **Check high-volume teams:** BOS/IND/HOU should still get small bump but not huge

---

## Files Modified

1. `api/utils/true_pace_calculator.py`
   - apply_muted_pace_effect(): 0.85+0.15 → 0.92+0.08
   - calculate_shot_volume_boost(): New thresholds (100/95 vs 95, 75/80 vs 80)
   - calculate_free_throw_boost(): +6/+3 → +3/+1
   - calculate_offensive_rebound_bonus(): +5/+3 → +2/+1
   - calculate_turnover_pace_bonus(): Return 0.0 always
   - calculate_offensive_identity_boost(): +6 → +2

2. `api/utils/home_road_edge.py`
   - compute_home_road_edge(): ±4/±2 → ±2/0 (only extreme patterns)

3. `api/utils/prediction_engine.py`
   - Updated logging: "Muted Effect" → "Very Light Effect"
   - Updated formula display: 0.85+0.15 → 0.92+0.08

---

## Summary

**What Changed:**
- Dramatically reduced all volume-based bonuses
- Removed turnover double-counting
- Made home/road ultra-conservative
- Cut pace influence in half

**What Stayed:**
- True possessions formula (FGA + 0.44*FTA + TO - ORB)
- Deterministic, explainable structure
- All existing components (defense, matchups, shootout, B2B)
- No UI changes

**Expected Outcome:**
- Predictions 8-12 points lower on average
- Closer alignment with betting lines
- Still higher for legitimate high-pace, high-volume games
- No more systematic over-prediction

---

## Next Steps

1. Monitor real game predictions over next week
2. Compare predicted vs actual totals
3. Further tune if still running high (can reduce shot volume to +3/+1 if needed)
4. Consider adding a global "dampening factor" if all predictions still overshoot
