# Recent Form Update - PPG-Based Dynamic Weighting

## Summary

Updated STEP 5 (Recent Form) in the prediction engine to use PPG-only scoring adjustments with dynamic weighting based on magnitude of change. ORTG/DRTG/PACE now only affect confidence (not score) to prevent double-counting.

## Files Modified

**`api/utils/prediction_engine.py`** - Lines 776-924 and 1056-1064

## What Changed

### **Old System (Flat 25% Weight)**
```python
# Everyone gets 25% weight regardless of magnitude
home_form_delta = home_recent_ppg - home_season_ppg
home_projected += (home_form_delta * 0.25)
```

### **New System (Dynamic PPG-Based Weighting)**

#### **1. PPG Adjustment (ONLY metric that affects score)**

```python
ppg_change = recent_ppg - season_ppg

# Dynamic weighting based on magnitude
if abs(ppg_change) >= 8:
    ppg_weight = 0.40  # Large changes get more weight
elif abs(ppg_change) >= 5:
    ppg_weight = 0.35  # Medium changes
else:
    ppg_weight = 0.25  # Small changes (baseline)

# Apply with clamping
ppg_adjust = ppg_change * ppg_weight
ppg_adjust = max(-8.0, min(ppg_adjust, 8.0))  # Never exceed ±8 pts
projected_score += ppg_adjust
```

**Examples:**
- Team scoring +10 PPG over last 5: `+10 × 0.40 = +4.0 pts` (capped at +8)
- Team scoring +6 PPG over last 5: `+6 × 0.35 = +2.1 pts`
- Team scoring +3 PPG over last 5: `+3 × 0.25 = +0.75 pts`
- Team scoring -12 PPG over last 5: `-12 × 0.40 = -4.8 pts` (would be capped at -8)

#### **2. ORTG Trend (Confidence Only)**

```python
ortg_change = recent_ortg - season_ortg

if abs(ortg_change) >= 7:
    confidence += 3  # Large offensive efficiency change
elif abs(ortg_change) >= 5:
    confidence += 2  # Moderate change
```

**Does NOT change predicted score** - only boosts confidence when offense is clearly trending.

#### **3. DRTG Volatility (Confidence Penalty)**

```python
drtg_change = recent_drtg - season_drtg

if abs(drtg_change) >= 6:
    confidence -= 3  # High defensive volatility
elif abs(drtg_change) >= 4:
    confidence -= 2  # Moderate volatility
```

Penalizes inconsistent defense (whether improving or worsening) as it adds uncertainty.

#### **4. Pace Trend (Confidence Only)**

```python
pace_change = recent_pace - season_pace

if abs(pace_change) >= 3:
    confidence += 2  # Clear pace trend
elif abs(pace_change) >= 2:
    confidence += 1  # Slight trend
```

**Does NOT change predicted score** - pace already handled in STEP 1. This just adds confidence when pace is trending clearly.

## Why These Changes?

### **Problem with Old System:**
1. **Fixed 25% weight** didn't distinguish between +2 PPG and +10 PPG changes
2. **No clamping** allowed extreme adjustments (could add ±15 pts)
3. **Single metric** didn't account for offensive efficiency or defensive volatility

### **Benefits of New System:**

1. **Dynamic Weighting**
   - Larger changes get more weight (up to 40%)
   - Small noise gets less weight (25%)
   - More responsive to real hot/cold streaks

2. **Clamping Prevents Extremes**
   - Maximum ±8 points per team
   - Prevents outlier games from dominating
   - More stable predictions

3. **No Double-Counting**
   - ORTG doesn't adjust score (we already use offensive ratings in baseline)
   - Pace doesn't adjust score (already handled in STEP 1)
   - DRTG doesn't adjust score (defense handled in STEP 4)
   - These metrics only affect confidence

4. **Better Confidence Modeling**
   - Clear trends increase confidence
   - Defensive volatility decreases confidence
   - Offensive efficiency changes increase confidence
   - More nuanced than simple variance check

## Console Output Examples

### **Small Change (2 PPG difference)**
```
STEP 5 - Recent form (PPG-based with dynamic weighting):
  Home PPG: 117.2 vs season 115.0 = +2.2
    Weight: 0.25 (based on magnitude) → adjustment: +0.6 pts
  Home: 118.6 | Away: 112.3
```

### **Medium Change (6 PPG difference) with ORTG trend**
```
STEP 5 - Recent form (PPG-based with dynamic weighting):
  Home PPG: 121.4 vs season 115.0 = +6.4
    Weight: 0.35 (based on magnitude) → adjustment: +2.2 pts
    ORTG trend: +5.8 (moderate) → confidence +2
  Home: 120.8 | Away: 112.3
  Confidence modifiers: Home +2, Away +0
```

### **Large Change (10 PPG difference) with defensive volatility**
```
STEP 5 - Recent form (PPG-based with dynamic weighting):
  Away PPG: 108.2 vs season 118.5 = -10.3
    Weight: 0.40 (based on magnitude) → adjustment: -4.1 pts
    DRTG volatility: +7.2 (high) → confidence -3
  Home: 116.5 | Away: 108.1
  Confidence modifiers: Home +0, Away -3

Applied recent form confidence modifiers: -3 → final confidence: 72%
```

## Integration with Existing System

- ✅ **Fits in current pipeline** - still STEP 5, between defense and shootout
- ✅ **Uses same data sources** - recent_games array from home/away_data
- ✅ **Compatible with breakdown** - home_form_adjustment and away_form_adjustment still tracked
- ✅ **Confidence bounds maintained** - still capped at 40-95%
- ✅ **No other steps modified** - pace, turnovers, defense, shootout unchanged

## Testing Checklist

- [ ] Team with +10 PPG last 5 gets ~40% weight (capped at +8)
- [ ] Team with +3 PPG last 5 gets 25% weight (~0.75 pts)
- [ ] Team with -6 PPG last 5 gets 35% weight (~2.1 pts negative)
- [ ] ORTG change of +6 adds +2 confidence (no score change)
- [ ] DRTG change of +8 subtracts -3 confidence
- [ ] Pace change of +3.5 adds +2 confidence (no score change)
- [ ] Confidence stays within 40-95% bounds
- [ ] Console output shows all calculations clearly

## Alternative Versions Available

If you want different behavior, here are variations:

### **A. ORTG Also Affects Score**
Add after PPG adjustment:
```python
if abs(ortg_change) >= 5:
    ortg_adjust = (ortg_change / 10.0) * 0.15  # Small adjustment
    projected_score += ortg_adjust
```

### **B. Pace Trend Modifies Pace Multiplier**
In STEP 1 (pace adjustment):
```python
if recent_pace_trend >= 3:
    pace_multiplier *= 1.02  # Boost for clear uptrend
```

### **C. Standard Deviation-Based Weighting**
Instead of flat thresholds:
```python
ppg_std = calculate_std_dev(recent_games_ppg)
ppg_weight = min(0.40, 0.25 + (abs(ppg_change) / ppg_std) * 0.05)
```

## Result

The model now:
1. ✅ **Responds proportionally** to scoring changes
2. ✅ **Prevents extreme adjustments** with ±8 pt cap
3. ✅ **Avoids double-counting** recent trends
4. ✅ **Improves confidence modeling** with multiple signals
5. ✅ **Maintains mathematical consistency** with rest of pipeline
