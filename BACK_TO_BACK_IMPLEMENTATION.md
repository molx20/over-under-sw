# Back-to-Back (B2B) Detection & Team-Specific Profiles - Implementation Summary

**Date:** December 6, 2024
**Status:** ✅ Complete
**Model Version:** v4.5 (upgraded from v4.4)

---

## Overview

Implemented a comprehensive back-to-back (B2B) detection system with team-specific performance profiles. The system automatically detects when teams are playing on the second night of a back-to-back and applies historical, team-specific adjustments based on how each team performs in B2B situations.

---

## Database Schema Changes

### New Columns Added to `team_game_logs`

```sql
-- rest_days: Number of days since team's previous game
ALTER TABLE team_game_logs ADD COLUMN rest_days INTEGER DEFAULT NULL;

-- is_back_to_back: Boolean flag (1 = B2B, 0 = not B2B)
ALTER TABLE team_game_logs ADD COLUMN is_back_to_back INTEGER DEFAULT 0;
```

### Data Population Results

- **Total game logs:** 584
- **Back-to-back games:** 107 (18.3%)
- **First game of season:** `rest_days = NULL, is_back_to_back = 0`
- **Subsequent games:** `rest_days = days_since_previous_game`
- **B2B detection:** `is_back_to_back = 1` when `rest_days = 1`

---

## Files Created

### 1. **`migrate_rest_days.py`** (Migration Script)
- One-time script to populate `rest_days` and `is_back_to_back` for existing data
- Processes all teams in chronological order
- Calculates days between consecutive games
- Successfully migrated 584 game logs

### 2. **`api/utils/back_to_back_profiles.py`** (B2B Profile Engine)
- **Main Functions:**
  - `get_back_to_back_profile(team_id, season)` - Returns BackToBackProfile object
  - `is_team_on_back_to_back(team_id, game_id)` - Checks if team is on B2B for specific game
  - `get_team_rest_days(team_id, game_id)` - Returns rest days for specific game
  - `print_team_b2b_summary(team_id, season)` - Debug/testing helper

- **BackToBackProfile Class:**
  ```python
  {
    'team_id': int,
    'b2b_games': int,              # Number of B2B games played
    'b2b_ppg': float,              # Average points in B2B games
    'b2b_opp_ppg': float,          # Average points allowed in B2B games
    'b2b_pace': float,             # Average pace in B2B games
    'season_ppg': float,           # Season average points
    'season_opp_ppg': float,       # Season average points allowed
    'season_pace': float,          # Season average pace
    'b2b_off_delta': float,        # B2B PPG - Season PPG
    'b2b_def_delta': float,        # B2B Opp PPG - Season Opp PPG
    'b2b_pace_delta': float,       # B2B Pace - Season Pace
    'small_sample': bool           # True if b2b_games < 3
  }
  ```

### 3. **Test Files**
- `test_b2b_simple.py` - Standalone test for B2B detection and profile calculation
- Used to validate implementation with real game data

---

## Sync Code Updates (`api/utils/sync_nba_data.py`)

### New Helper Function: `_compute_rest_days_for_team(cursor, team_id)`

```python
def _compute_rest_days_for_team(cursor, team_id: int):
    """
    Compute rest_days and is_back_to_back for all games of a specific team.
    Called after syncing game logs for a team.
    """
    # Get all games sorted by date
    # First game: rest_days = NULL, is_back_to_back = 0
    # Subsequent games: Calculate days since previous game
    # is_back_to_back = 1 if rest_days == 1
```

### Integration Point
- Called in `_sync_game_logs_impl()` after inserting game logs
- Runs for each team after their logs are synced
- Ensures all new games automatically get B2B flags computed

---

## Prediction Engine Integration (STEP 8)

### Replaced Old STEP 8 (Fatigue Adjustment)

**Old:** Simple total-based fatigue penalty using `apply_fatigue_penalty()`
**New:** Team-specific B2B adjustments based on historical performance

### Implementation in `api/utils/prediction_engine.py`

**Location:** Lines 1483-1552 (STEP 8)

**Process:**
1. Import B2B profile functions
2. Check if each team is on B2B for this game
3. Get historical B2B profile for each team
4. Calculate adjustments (if sufficient sample size)
5. Apply adjustments to team projections
6. Log results

### Adjustment Formula (v1 - Conservative)

```python
# For each team on B2B with b2b_games >= 3:

# Offensive adjustment (affects team's own scoring)
off_adjustment = b2b_off_delta * 0.5
team_projected_score += off_adjustment

# Defensive adjustment (affects opponent's scoring, only if positive)
def_adjustment = max(0, b2b_def_delta * 0.5)
opponent_projected_score += def_adjustment
```

**Why 0.5 multiplier?**
- Conservative scaling to avoid overfitting
- Allows us to observe impact before tuning
- Can be adjusted later based on performance

**Why `max(0, ...)` for defense?**
- Only apply defensive adjustment if team allows MORE points on B2Bs
- If team defends BETTER on B2Bs (negative delta), don't penalize opponent
- Prevents double-counting (offensive delta already captures team's scoring)

### Sample Size Threshold
- **Minimum B2B games:** 3
- **If < 3 games:** Profile computed but adjustments set to 0
- **Logged as:** "Small sample (X games) - no adjustment"

---

## Debug Output in Prediction Result

### New Field: `back_to_back_debug`

```json
{
  "back_to_back_debug": {
    "home": {
      "is_b2b": true,
      "b2b_games": 4,
      "b2b_off_delta": 4.7,
      "b2b_def_delta": -0.1,
      "b2b_pace_delta": -0.0,
      "off_adj": 2.4,
      "def_adj": 0.0,
      "small_sample": false
    },
    "away": {
      "is_b2b": true,
      "b2b_games": 5,
      "b2b_off_delta": -1.9,
      "b2b_def_delta": 1.6,
      "b2b_pace_delta": -1.2,
      "off_adj": -1.0,
      "def_adj": 0.8,
      "small_sample": false
    }
  }
}
```

**Fields Explained:**
- `is_b2b` - Whether team is on back-to-back
- `b2b_games` - Number of B2B games in profile
- `b2b_off_delta` - How many more/fewer points team scores on B2Bs
- `b2b_def_delta` - How many more/fewer points team allows on B2Bs
- `b2b_pace_delta` - How much faster/slower team plays on B2Bs
- `off_adj` - Actual offensive adjustment applied (delta * 0.5)
- `def_adj` - Actual defensive adjustment applied (max(0, delta * 0.5))
- `small_sample` - Whether sample size is too small (< 3 games)

---

## Example: Game 0022500338 (Both Teams on B2B)

### Situation
- **Home Team (BOS - 1610612738):** On B2B
- **Away Team (LAL - 1610612747):** On B2B

### B2B Profiles

**Boston Celtics (Home):**
```
B2B Games: 4
Season PPG: 112.8  →  B2B PPG: 117.5  =  +4.7 delta
Season Opp PPG: 103.9  →  B2B Opp PPG: 103.8  =  -0.1 delta
Season Pace: 93.8  →  B2B Pace: 93.7  =  -0.0 delta
```

**Los Angeles Lakers (Away):**
```
B2B Games: 5
Season PPG: 105.7  →  B2B PPG: 103.8  =  -1.9 delta
Season Opp PPG: 105.4  →  B2B Opp PPG: 107.0  =  +1.6 delta
Season Pace: 93.1  →  B2B Pace: 92.0  =  -1.2 delta
```

### Adjustments Applied

**Home Team (BOS):**
- Offensive: +4.7 * 0.5 = **+2.4 pts** (to home score)
- Defensive: max(0, -0.1 * 0.5) = **+0.0 pts** (to away score)
- *Interpretation: BOS scores better on B2Bs, defense unchanged*

**Away Team (LAL):**
- Offensive: -1.9 * 0.5 = **-1.0 pts** (to away score)
- Defensive: max(0, +1.6 * 0.5) = **+0.8 pts** (to home score)
- *Interpretation: LAL scores worse and allows more on B2Bs*

**Net Impact:**
- Home team gets: +2.4 (own offense) + 0.8 (opponent defense) = **+3.2 pts**
- Away team gets: -1.0 (own offense) + 0.0 (opponent defense) = **-1.0 pts**
- **Total difference: +2.2 pts** (favors higher total due to BOS's strong B2B performance)

---

## Console Output Example

```
[prediction_engine] STEP 8 - Back-to-Back Adjustment (Team-Specific):
  Home Team (B2B): 4 B2B games
    Off Delta: +4.7 → Adjustment: +2.4
    Def Delta: -0.1 → Adjustment: +0.0 (to away)
  Away Team (B2B): 5 B2B games
    Off Delta: -1.9 → Adjustment: -1.0
    Def Delta: +1.6 → Adjustment: +0.8 (to home)
[prediction_engine] FINAL PREDICTION: 218.2 (Home: 111.5 + Away: 106.7)
```

---

## Key Design Decisions

### 1. **Why Team-Specific Profiles?**
- Different teams respond differently to B2Bs
- Some teams (deeper rosters) handle B2Bs better
- Some coaches rest starters differently
- Historical data is more predictive than generic penalties

### 2. **Why Separate Offensive and Defensive Adjustments?**
- B2B fatigue can affect offense and defense independently
- Offense: Legs are tired → worse shooting, lower energy
- Defense: Can't guard as intensely → allow more points
- Allows model to capture nuanced team behaviors

### 3. **Why 0.5 Multiplier (v1)?**
- Conservative first implementation
- Prevents overfitting to small sample sizes
- Allows validation of impact before tuning
- Can be increased to 0.6, 0.7, etc. based on results

### 4. **Why Exclude Small Samples (< 3 games)?**
- 1-2 games can be outliers
- Not statistically meaningful
- Better to wait for more data
- Prevents noise from skewing predictions

### 5. **Why `max(0, def_delta)` for Defense?**
- Only penalize if team allows MORE points on B2Bs
- If team defends better on B2Bs, don't help opponent
- Avoids double-counting (offense already captured)

---

## Future Tuning Opportunities

### 1. **Adjust Multipliers**
Current: `0.5`
Options: `0.6`, `0.7`, `0.8`, `1.0`
Method: Backtest on historical B2B games, measure accuracy improvement

### 2. **Lower Sample Size Threshold**
Current: 3 games
Option: 2 games (but with lower weight)
Method: Use weighted average based on sample size

### 3. **Add Pace Adjustment**
Currently: Only offense and defense
Option: Apply `b2b_pace_delta` to game pace calculation
Impact: Capture teams that slow down or speed up on B2Bs

### 4. **Distinguish 1st vs 2nd B2B**
Currently: Treats all B2Bs the same
Option: First night of B2B vs second night could differ
Data: Need to track position in B2B set

### 5. **Travel Distance Factor**
Currently: Pure rest days
Option: Weight by travel miles (road B2B cross-country vs local)
Data: Would need game location data

### 6. **Time Zone Adjustments**
Currently: Not considered
Option: East coast team traveling west vs west traveling east
Data: Would need game location + time zone data

---

## Validation & Testing

### Test Results
✅ Schema migration successful (584 games)
✅ B2B detection working (18.3% of games = realistic)
✅ Profile calculation accurate (matches manual calculations)
✅ Prediction engine integration complete
✅ Debug output present in results
✅ Both teams on B2B handled correctly
✅ Small sample exclusion working (< 3 games)

### Test Case: Game 0022500338
- Home team on B2B ✓
- Away team on B2B ✓
- Profiles calculated correctly ✓
- Adjustments applied correctly ✓
- Net impact: +2.2 pts to predicted total ✓

---

## Impact on Model Version

### Updated from v4.4 → v4.5

**Previous STEP 8:** Fatigue Penalty (total-based)
**New STEP 8:** Back-to-Back Adjustment (team-specific)

**What Changed:**
- Removed generic fatigue penalty
- Added team-specific B2B profiles
- Added offensive and defensive adjustments
- Added sample size filtering
- Added comprehensive debug output

**What Stayed the Same:**
- All other steps (1-7) unchanged
- Baseline, pace, defense, HCA, shootout logic intact
- Prediction flow and structure preserved

---

## Documentation Updates Needed

**`PREDICTION_MODEL_DOCUMENTATION.md`** should be updated to reflect:
1. Version bump to v4.5
2. STEP 8 replacement details
3. New data schema (rest_days, is_back_to_back)
4. B2B profile calculation methodology
5. Adjustment formula (v1)
6. Future tuning section

---

## Next Steps (Optional Enhancements)

1. **Backtest B2B Impact**
   - Run predictions on historical B2B games
   - Measure accuracy improvement
   - Validate 0.5 multiplier is appropriate

2. **Tune Multipliers**
   - Test 0.6, 0.7, 0.8 multipliers
   - Find optimal balance between signal and noise
   - May vary by offensive vs defensive adjustment

3. **Add Frontend Display**
   - Show B2B status in game cards
   - Display adjustments in prediction breakdown
   - Add tooltip explaining B2B impact

4. **Monitor Performance**
   - Track prediction accuracy on B2B vs non-B2B games
   - Identify teams that outperform/underperform profiles
   - Refine profiles as more data accumulates

5. **Extend to 3-in-4 or 4-in-5**
   - Detect multi-game stretches (not just B2Bs)
   - Apply cumulative fatigue for dense schedules
   - Weight by games played in timeframe

---

## Files Modified Summary

### Created:
1. `migrate_rest_days.py` - One-time migration script
2. `api/utils/back_to_back_profiles.py` - B2B profile engine
3. `test_b2b_simple.py` - Testing script

### Modified:
1. `api/data/nba_data.db` - Added rest_days and is_back_to_back columns
2. `api/utils/sync_nba_data.py` - Added `_compute_rest_days_for_team()` function
3. `api/utils/prediction_engine.py` - Replaced STEP 8 with B2B adjustment

### Schema Changes:
```sql
team_game_logs:
  + rest_days INTEGER
  + is_back_to_back INTEGER
```

---

## Conclusion

Successfully implemented a comprehensive back-to-back detection and adjustment system with team-specific historical profiles. The system automatically detects B2B situations, computes team-specific performance deltas, and applies conservative adjustments to predictions. The v1 implementation uses a 0.5 multiplier and excludes small samples (< 3 games) for safety. All components are tested and working correctly.

**Status:** ✅ Production Ready
**Model Version:** v4.5
**Next Action:** Monitor performance and tune multipliers as needed

---

*Generated: December 6, 2024*
*Implementation Time: ~2 hours*
*B2B Games in Database: 107 (18.3%)*
*Teams with 3+ B2B Games: Most teams*
*Conservative Multiplier: 0.5*
