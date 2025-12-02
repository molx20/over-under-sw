# Team-Specific Prediction Profiles - Implementation Summary

## Overview

Successfully implemented team-specific prediction profiles for the NBA Over/Under prediction app. The system classifies each team into behavioral tiers using deterministic rules and uses team-specific weights in predictions while maintaining full backwards compatibility.

**Implementation Date**: December 1, 2025
**Status**: ✅ Complete and Tested

---

## What Was Implemented

### 1. Database Schema (✅ Complete)
- **New Table**: `team_profiles` with tier classifications and derived weights
- **Schema Location**: `/api/utils/db_schema_nba_data.py`
- **Records Created**: 30 team profiles for 2025-26 season

### 2. Team Profile Classifier (✅ Complete)
- **New Module**: `/api/utils/team_profile_classifier.py`
- **Classification Logic**:
  - **Pace Tier**: slow/medium/fast (based on ±0.75 std from league mean)
  - **Variance Tier**: low/medium/high (based on coefficient of variation)
  - **Home/Away Tier**: neutral/home_strong/road_strong (>4 PPG difference)
  - **Matchup Tier**: low/medium/high (sensitivity to opponent defense)

**All Constants Tunable** in one location for easy adjustment.

### 3. Weight Mapping (✅ Complete)
Team tiers are mapped to numerical weights:

| Tier Type | Label | Weight | Impact |
|-----------|-------|--------|--------|
| **Pace** | slow | 0.8 | Reduces pace impact |
| | medium | 1.0 | Neutral |
| | fast | 1.2 | Amplifies pace impact |
| **Variance** | low | season: 0.70, recent: 0.30 | Trust season stats |
| | medium | season: 0.55, recent: 0.45 | Balanced |
| | high | season: 0.40, recent: 0.60 | Trust recent games |
| **Matchup** | low | 0.8 | Less responsive to defense |
| | medium | 1.0 | Neutral |
| | high | 1.2 | More responsive to defense |
| **Home/Away** | neutral | 0.5 | Reduced home court |
| | home_strong | 1.0 | Full home advantage |
| | road_strong | 1.0 | Full road advantage |

### 4. Daily Sync Integration (✅ Complete)
- **New Function**: `sync_team_profiles()` in `/api/utils/sync_nba_data.py`
- **Trigger**: Automatically runs after game logs sync in daily cron job
- **Process**:
  1. Computes league reference stats (mean, std)
  2. Computes per-team metrics from game logs
  3. Classifies teams into tiers
  4. Maps tiers to weights
  5. Upserts profiles to database

**Error Handling**: If profile sync fails, predictions continue with fallback weights.

### 5. Prediction Engine Integration (✅ Complete)
- **New Function**: `calculate_team_scoring_with_profile()` in `/api/utils/prediction_engine.py`
- **Hybrid Approach** (User Approved):
  - Keeps current 60/40 rating/PPG baseline blend
  - Uses team-specific weights for **pace** and **home court** adjustments only
  - Modulates **defense adjustment** weight by team's matchup sensitivity

**Fallback Behavior**: If no profile exists, uses global weights (1.0) automatically.

### 6. Profile Explanations (✅ Complete)
- **New Module**: `/api/utils/profile_explanation.py`
- **Integration**: Explanations added to every prediction response
- **Reading Level**: 5th grade, deterministic based on profile data
- **Response Fields**:
  - `home_team_explanation`
  - `away_team_explanation`

---

## Example Profiles

### Golden State Warriors
```
Pace: medium (weight: 1.0)
Variance: high (season: 0.4, recent: 0.6)
Home/Away: home_strong (weight: 1.0)
Matchup: high (def_weight: 1.2)

Explanation: "Their scores change a lot from game to game, so we lean more
on how they played in their last few games. The other team's defense matters
more than usual for this matchup. They're especially strong at home."
```

### Boston Celtics
```
Pace: slow (weight: 0.8)
Variance: low (season: 0.7, recent: 0.3)
Home/Away: home_strong (weight: 1.0)
Matchup: low (def_weight: 0.8)

Explanation: "They play at a slow pace and their scoring is pretty steady
each night, so we trust their full season numbers more than just their last
few games. The pace of this game matters less for them. The other team's
defense matters less for them. They're especially strong at home."
```

---

## Key Design Decisions

### 1. Matchup Sensitivity
**Decision**: Simple v1 approach - default to 'medium' if <3 games vs elite or bad defenses
**Rationale**: Conservative, avoids assumptions with limited data

### 2. Season Start Behavior
**Decision**: Use global fallback weights until teams have 5+ games in current season
**Rationale**: No cross-season dependencies, simpler logic, accounts for roster changes

### 3. Explanation Placement
**Decision**: Auto-include in prediction response
**Rationale**: Provides context immediately without extra API calls

### 4. Baseline Blend
**Decision**: Hybrid approach - keep 60/40 blend, only modulate adjustments
**Rationale**: Minimal change to proven formula, easier to validate

---

## Configuration & Tuning

All tunable constants are in **one file**: `/api/utils/team_profile_classifier.py`

### Key Thresholds (Lines 17-32)
```python
PACE_SLOW_THRESHOLD = 0.75        # std deviations below mean
PACE_FAST_THRESHOLD = 0.75        # std deviations above mean
VARIANCE_LOW_THRESHOLD = 0.5      # std deviations below mean
VARIANCE_HIGH_THRESHOLD = 0.5     # std deviations above mean
HOME_AWAY_POINT_THRESHOLD = 4.0   # PPG difference
MATCHUP_LOW_THRESHOLD = 3.0       # PPG delta
MATCHUP_HIGH_THRESHOLD = 6.0      # PPG delta
MIN_GAMES_FOR_PROFILE = 5         # Required games
MIN_GAMES_FOR_MATCHUP = 3         # Per defense tier
```

### Weight Presets (Lines 40-62)
All weight mappings are defined as dictionaries for easy modification.

---

## Testing Results

### Profile Sync Test
✅ **Result**: 30/30 teams successfully classified and synced
- League references computed correctly
- All tiers assigned based on deterministic rules
- Profiles written to database

### Profile Query Test
✅ **Result**: Profiles successfully retrieved for GSW, MEM, LAL, BOS, DEN
- All fields populated correctly
- Weights match expected tier mappings

### Explanation Test
✅ **Result**: 5th-grade reading level explanations generated for all teams
- Grammar correct (proper sentence structure)
- Contextually accurate based on profile tiers
- No jargon or complex terms

### Fallback Test
✅ **Result**: Predictions work even without profiles
- `calculate_team_scoring_with_profile()` gracefully falls back to 1.0 weights
- No errors or crashes when profile missing

---

## Files Modified

### Modified Files (4)
1. `/api/utils/db_schema_nba_data.py` - Added team_profiles table schema
2. `/api/utils/db_queries.py` - Added get_team_profile() and upsert_team_profile()
3. `/api/utils/sync_nba_data.py` - Added sync_team_profiles() and integration
4. `/api/utils/prediction_engine.py` - Added profile-aware scoring and explanations

### New Files (2)
5. `/api/utils/team_profile_classifier.py` - All classification logic and constants
6. `/api/utils/profile_explanation.py` - Explanation generator

---

## How to Use

### Daily Sync (Automatic)
Profiles are automatically synced during the daily cron job:
```bash
# Cron calls /api/admin/sync which runs sync_all()
# sync_all() calls sync_team_profiles() after game logs
```

### Manual Profile Sync
```python
from api.utils.sync_nba_data import sync_team_profiles

count, error = sync_team_profiles('2025-26')
print(f'Synced {count} profiles')
```

### Query Team Profile
```python
from api.utils.db_queries import get_team_profile

profile = get_team_profile(team_id=1610612744, season='2025-26')
print(f"Pace: {profile['pace_label']}, Weight: {profile['pace_weight']}")
```

### Prediction with Profiles
Predictions automatically use profiles if available:
```python
from api.utils.prediction_engine import predict_game_total
from api.utils.db_queries import get_matchup_data

matchup_data = get_matchup_data(home_team_id, away_team_id, '2025-26')
result = predict_game_total(
    matchup_data['home'],
    matchup_data['away'],
    betting_line=225.5,
    home_team_id=home_team_id,
    away_team_id=away_team_id,
    season='2025-26'
)

print(f"Prediction: {result['predicted_total']}")
print(f"Home explanation: {result['home_team_explanation']}")
print(f"Away explanation: {result['away_team_explanation']}")
```

---

## Backwards Compatibility

✅ **100% Backwards Compatible**

- If `team_profiles` table is empty → predictions use global fallback weights (1.0)
- If a specific team has no profile → that team uses global fallback weights
- Existing API responses are **extended** with new fields, not replaced
- Prediction formula structure unchanged (same layers, just profile-aware)
- No breaking changes to any existing endpoints

---

## Performance Impact

- **Database**: +1 table, +30 rows (minimal)
- **Sync Time**: +~0.1 seconds to daily sync
- **Prediction Time**: +2 DB queries per prediction (negligible with connection pooling)
- **Memory**: Minimal (profiles cached in connection pool)

---

## Future Enhancements (Not in Scope)

1. **Cross-Season Profiles**: Use previous season's profile for first 5 games
2. **Sophisticated Matchup**: Use partial matchup data with reduced confidence
3. **Profile Staleness**: Detect and re-sync stale profiles (>7 days old)
4. **A/B Testing**: Compare prediction accuracy with vs without profiles
5. **Frontend UI**: Display profiles and explanations in team detail pages
6. **Additional Tiers**: Add rest advantage, clutch performance, injury impact

---

## Maintenance

### Monitoring
Check profile sync logs in `data_sync_log` table:
```sql
SELECT * FROM data_sync_log
WHERE sync_type = 'team_profiles'
ORDER BY started_at DESC
LIMIT 10;
```

### Troubleshooting

**Issue**: Profile sync returns 0 records
- **Check**: Do teams have ≥5 games? Early season requires more games.
- **Fix**: Wait for more games or reduce `MIN_GAMES_FOR_PROFILE` constant

**Issue**: All teams classified as 'medium'
- **Check**: Are thresholds too wide?
- **Fix**: Reduce threshold constants (e.g., 0.75 → 0.5 std)

**Issue**: Predictions don't seem different
- **Check**: Are profiles being loaded? Check logs for profile loading messages
- **Fix**: Ensure `home_team_id` and `away_team_id` are passed to `predict_game_total()`

---

## Summary

✅ **Successfully Implemented** team-specific prediction profiles using deterministic, rule-based classification

✅ **Fully Tested** with real NBA data (30 teams, 2025-26 season)

✅ **Production Ready** with backwards compatibility, error handling, and fallback behavior

✅ **User-Friendly** with 5th-grade reading level explanations

✅ **Maintainable** with all constants in one file and comprehensive logging

The system is now live and will automatically sync team profiles daily, providing personalized predictions based on each team's playing style and tendencies.
