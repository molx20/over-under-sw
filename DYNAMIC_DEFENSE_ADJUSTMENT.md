# Dynamic Defensive Adjustment - Implementation Summary

## Overview
Implemented a **dynamic defensive adjustment system** that scales defensive impact based on recent offensive form. This prevents the model from over-penalizing hot offenses against strong defenses and under-penalizing cold offenses even against weak defenses.

## Problem Solved

### Before (Static Defense)
- Strong defenses suppressed scoring too much, even when an offense was on fire
- Weak defenses didn't penalize enough when an offense was ice cold
- Defense had the same impact regardless of whether a team was hot, normal, or cold

### After (Dynamic Defense)
- **Hot offenses** (ORTG +4 or better): Defense impact reduced significantly
- **Cold offenses** (ORTG -4 or worse): Defense impact amplified
- **Normal offenses**: Defense impact unchanged (baseline behavior)

## Implementation

### 1. New Helper Function: `calculate_defensive_multiplier()`
**Location:** `api/utils/prediction_engine.py` (lines 523-567)

**Signature:**
```python
def calculate_defensive_multiplier(recent_ortg_change, recent_ppg_change, opponent_def_rank):
    """
    Calculate how much to scale defensive adjustments based on recent offensive form.

    Returns: Multiplier (0.30 to 1.50)
    """
```

**Logic:**
```python
# Determine offensive status using ORTG change (primary) or PPG change (fallback)
offense_change = recent_ortg_change if abs(recent_ortg_change) > 1 else recent_ppg_change

if offense_change >= 4.0:  # HOT OFFENSE
    if opponent_def_rank <= 10:
        return 0.30  # Top-10 defense: reduce to 30%
    elif opponent_def_rank <= 25:
        return 0.40  # Average defense: reduce to 40%
    else:
        return 0.50  # Weak defense: reduce to 50%

elif offense_change <= -4.0:  # COLD OFFENSE
    return 1.50  # Amplify all defenses to 150%

else:  # NORMAL OFFENSE
    return 1.00  # Keep at 100% (unchanged)
```

### 2. Integration into STEP 4
**Location:** `api/utils/prediction_engine.py` (lines 1195-1243)

**Changes:**
1. Calculate PPG change for both teams
2. Call `calculate_defensive_multiplier()` for each team
3. Determine offensive status (hot/normal/cold) for logging
4. Apply multiplier to defensive adjustment: `base_delta × 0.3 × multiplier`
5. Enhanced logging shows offensive status and multiplier

**Code Flow:**
```python
# Calculate offensive changes
home_ppg_change = home_recent_ppg - home_season_ppg
away_ppg_change = away_recent_ppg - away_season_ppg

# Get dynamic multipliers
home_def_multiplier = calculate_defensive_multiplier(
    home_recent_ortg_change,
    home_ppg_change,
    away_def_rank
)
away_def_multiplier = calculate_defensive_multiplier(
    away_recent_ortg_change,
    away_ppg_change,
    home_def_rank
)

# Apply: base_weight (30%) × dynamic_multiplier
home_defense_adjustment = home_defense_delta * 0.3 * home_def_multiplier
away_defense_adjustment = away_defense_delta * 0.3 * away_def_multiplier
```

## Multiplier Table

| Offensive Status | vs Elite Def (1-10) | vs Avg Def (11-25) | vs Weak Def (26-30) |
|------------------|---------------------|-------------------|---------------------|
| **Hot (+4 or more)** | 0.30x (reduce 70%) | 0.40x (reduce 60%) | 0.50x (reduce 50%) |
| **Normal (-3.9 to +3.9)** | 1.00x (unchanged) | 1.00x (unchanged) | 1.00x (unchanged) |
| **Cold (-4 or worse)** | 1.50x (amplify 50%) | 1.50x (amplify 50%) | 1.50x (amplify 50%) |

## Example Scenarios

### Scenario 1: Hot Offense vs Elite Defense
```
Team: BOS
Season PPG: 115.3
Recent PPG: 122.0 (+6.7)
Recent ORTG change: +0.0 (using PPG change instead)
Opponent: NYK (Defense rank #14 - average)

Offensive Status: HOT (PPG change +6.7 >= +4)
Defense Multiplier: 0.40x (hot vs average defense)

Base defensive penalty: -6.8 points
OLD system: -6.8 × 0.30 = -2.04 pts
NEW system: -6.8 × 0.30 × 0.40 = -0.82 pts

Result: Hot BOS offense reduces NYK defense impact from -2.04 to -0.82 pts
        Defense matters less when offense is rolling!
```

### Scenario 2: Normal Offense vs Strong Defense
```
Team: NYK
Season PPG: 120.2
Recent PPG: 119.8 (-0.4)
Recent ORTG change: +0.0
Opponent: BOS (Defense rank #19 - average)

Offensive Status: NORMAL (PPG change -0.4, between -4 and +4)
Defense Multiplier: 1.00x (unchanged)

Base defensive penalty: -21.2 points
OLD system: -21.2 × 0.30 = -6.36 pts
NEW system: -21.2 × 0.30 × 1.00 = -6.36 pts

Result: Normal offense keeps defense impact exactly the same
```

### Scenario 3: Cold Offense vs Weak Defense (Hypothetical)
```
Team: Hypothetical
Season PPG: 110.0
Recent PPG: 105.0 (-5.0)
Recent ORTG change: -5.5
Opponent: Defense rank #28 (weak)

Offensive Status: COLD (ORTG change -5.5 <= -4)
Defense Multiplier: 1.50x (amplify)

Base defensive penalty: -3.0 points
OLD system: -3.0 × 0.30 = -0.9 pts
NEW system: -3.0 × 0.30 × 1.50 = -1.35 pts

Result: Cold offense amplifies even weak defense from -0.9 to -1.35 pts
        Bad offenses struggle more against ANY defense!
```

## Test Results

### Unit Tests (`test_dynamic_defense.py`)
**All 11 tests passed:**

✓ Hot offense vs Elite defense (rank #3) → 0.30x
✓ Hot offense vs Average defense (rank #15) → 0.40x
✓ Hot offense vs Weak defense (rank #28) → 0.50x
✓ Cold offense vs Elite defense (rank #2) → 1.50x
✓ Cold offense vs Average defense (rank #16) → 1.50x
✓ Cold offense vs Weak defense (rank #27) → 1.50x
✓ Normal offense vs Elite defense (rank #5) → 1.00x
✓ Normal offense vs Average defense (rank #18) → 1.00x
✓ Normal offense vs Weak defense (rank #29) → 1.00x
✓ Exactly +4 ORTG (threshold) → 0.30x (hot)
✓ Exactly -4 ORTG (threshold) → 1.50x (cold)

### Integration Test (`test_dynamic_defense_integration.py`)
**BOS vs NYK:**
```
[prediction_engine] STEP 4 - Defense adjustment (dynamic based on offensive form):
  Home offense: hot (ORTG: +0.0, PPG: +6.7)
    vs Away defense rank #14 → multiplier: 0.40x
    Base delta: -6.8 pts → applied: -0.8
  Away offense: normal (ORTG: +0.0, PPG: -0.4)
    vs Home defense rank #19 → multiplier: 1.00x
    Base delta: -21.2 pts → applied: -6.4
  Home: 115.1 | Away: 108.7
```

✓ BOS detected as HOT offense (+6.7 PPG)
✓ NYK detected as NORMAL offense (-0.4 PPG)
✓ Multipliers correctly applied (0.40x for hot, 1.00x for normal)
✓ Final projections reflect scaled defensive adjustments

## Console Output

### New STEP 4 Logging
```
[prediction_engine] STEP 4 - Defense adjustment (dynamic based on offensive form):
  Home offense: hot (ORTG: +0.0, PPG: +6.7)
    vs Away defense rank #14 → multiplier: 0.40x
    Base delta: -6.8 pts → applied: -0.8
  Away offense: normal (ORTG: +0.0, PPG: -0.4)
    vs Home defense rank #19 → multiplier: 1.00x
    Base delta: -21.2 pts → applied: -6.4
  Home: 115.1 | Away: 108.7
```

**What it shows:**
- Offensive status for each team (hot/normal/cold)
- Recent ORTG and PPG changes
- Opponent defense rank
- Dynamic multiplier applied
- Base defensive delta vs final applied adjustment

## Files Modified

### `api/utils/prediction_engine.py`
**Added:**
- `calculate_defensive_multiplier()` function (lines 523-567)
  - Calculates multiplier based on offensive form and opponent defense rank
  - Returns 0.30-1.50x depending on hot/normal/cold status

**Modified:**
- STEP 4 defensive adjustment (lines 1195-1243)
  - Calculate PPG changes for both teams
  - Call multiplier function for each team
  - Determine offensive status for logging
  - Apply multiplier to base defensive adjustment
  - Enhanced logging with offensive status and multiplier

**Total lines added:** ~90 (including comprehensive comments)

### Test Files Created
1. `test_dynamic_defense.py` - Unit tests for multiplier logic
2. `test_dynamic_defense_integration.py` - Integration test with real prediction
3. `DYNAMIC_DEFENSE_ADJUSTMENT.md` - This documentation

## Key Benefits

1. **Context-Aware Defense**: Defense impact adapts to offensive form
2. **Prevents Over-Suppression**: Hot offenses aren't killed by elite defenses
3. **Punishes Cold Streaks**: Struggling offenses face amplified defensive pressure
4. **Transparent**: Clear logging shows exactly what's happening
5. **Tunable**: Thresholds and multipliers easy to adjust
6. **Battle-Tested**: Comprehensive unit and integration tests

## Tuning Guide

To adjust thresholds or multipliers, edit `calculate_defensive_multiplier()`:

**Change hot/cold thresholds:**
```python
if offense_change >= 5.0:  # Was 4.0 - more strict
if offense_change <= -5.0:  # Was -4.0 - more strict
```

**Change multipliers:**
```python
# Hot offense
return 0.20  # Was 0.30 - even less defense impact
return 0.35  # Was 0.40 - slightly less reduction

# Cold offense
return 1.75  # Was 1.50 - amplify even more
return 1.25  # Was 1.50 - amplify less
```

**Add more granular tiers:**
```python
if offense_change >= 7.0:  # Very hot
    return 0.20
elif offense_change >= 4.0:  # Hot
    return 0.35
# ... etc
```

## Impact on Model Behavior

### Before Dynamic Defense
- Team on 6-game scoring tear still got crushed by elite defense
- Team in 5-game slump got away with minimal penalty vs weak defense
- Defense had uniform impact regardless of context

### After Dynamic Defense
- Hot offense: "Yes, they're playing great defense, but we're on fire!"
  → Defense penalty reduced to 30-50% of normal

- Cold offense: "We can't score on anyone right now, even weak defenses hurt"
  → Defense penalty amplified to 150% of normal

- Normal offense: "Standard adjustment based on defensive quality"
  → Defense penalty unchanged at 100%

## Edge Cases Handled

1. **No ORTG data**: Falls back to PPG change
2. **Minimal changes**: Uses ORTG if |change| > 1, else PPG
3. **Missing defense rank**: Multiplier still calculated (treats as weak defense)
4. **Exactly at threshold**: +4 counts as hot, -4 counts as cold (inclusive)

## Future Enhancements

Potential improvements (not implemented):
- [ ] Different thresholds for home vs away teams
- [ ] Graduated multipliers (e.g., very hot = 0.20x, hot = 0.40x)
- [ ] Consider defensive form too (hot defense vs cold defense)
- [ ] Weight recent games differently (last 3 vs last 5)
- [ ] Adjust based on opponent quality (hot vs top-5 different than hot vs top-10)

## Summary

The dynamic defensive adjustment system successfully addresses the rigid defense problem by:

1. **Reducing defensive penalties 50-70%** when offenses are hot (+4 or better)
2. **Amplifying defensive penalties 50%** when offenses are cold (-4 or worse)
3. **Keeping defensive penalties unchanged** when offenses are normal

This creates a more realistic model where:
- A team on a scoring tear isn't completely neutralized by elite defense
- A struggling team faces even more pressure from any quality of defense
- Normal scenarios continue to work as before

The system is transparent (clear logging), tested (11 unit tests + integration), and tunable (easy to adjust thresholds and multipliers).
