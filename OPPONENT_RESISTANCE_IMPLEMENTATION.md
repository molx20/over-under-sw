# Opponent Resistance Implementation Summary

## Overview
Implemented **Opponent Resistance** as a possession-only pregame module that calculates how opponent defensive pressure affects turnovers, offensive rebounds, and free throws.

**Date Range:** Oct 21, 2025 - Jan 2, 2026
**Database:** `api/data/nba_data.db` (team_game_logs table)
**Status:** ✅ Backend Complete, Frontend Pending

---

## 1. Database Schema Used

### Available Fields from `team_game_logs`:
```
Team Stats:
- fgm, fga (for possessions calculation)
- ftm, fta (for possessions and FTr)
- turnovers
- offensive_rebounds, defensive_rebounds
- possessions (pre-calculated)

Opponent Stats (directly available!):
- opp_fgm, opp_fga
- opp_ftm, opp_fta
- opp_turnovers
- opp_offensive_rebounds, opp_defensive_rebounds
- opp_possessions
```

**Key Finding:** All opponent stats are available in each row - no complex joins needed!

---

## 2. Files Created/Modified

### Created:
1. **`/api/utils/opponent_resistance.py`** (500+ lines)
   - Core module with all calculation functions
   - Functions:
     - `get_team_identity()` - Team's own TO%, OREB%, Empty Possessions
     - `get_opponent_resistance()` - How opponents perform against this team
     - `get_expected_matchup_metrics()` - Blend identity + resistance
     - `compute_expected_empty()` - Expected empty possessions index
   - In-memory caching for season aggregates

2. **`/api/utils/verify_opponent_resistance.py`** (200+ lines)
   - Verification script that tests 10 random games
   - Validates:
     - No NaN values
     - Rates within plausible ranges (0-30% TO%, 0-50% OREB%, etc.)
     - Expected matchup blending works correctly
   - ✅ All 10 games passed validation

### Modified:
3. **`/server.py`** (lines 1341-1365, 1383)
   - Added opponent resistance calculation to `/api/game_detail` endpoint
   - Calculates metrics based on game date
   - Returns `opponent_resistance` field in response

---

## 3. Formulas & Definitions

### A) Possessions Estimate
```python
possessions_est = FGA + 0.44*FTA - OREB + TO
```

### B) Empty Possessions
```python
empty_possessions = (FGA - FGM) + (FTA - FTM) + TO - OREB
```

### C) Team Identity Rates
```python
TO_pct = (Total TO / Total Possessions) * 100
OREB_pct = (Total OREB / (Total OREB + Total Opp DREB)) * 100
FTr = (Total FTA / Total FGA) * 100
Empty_rate = (Total Empty / Total Possessions) * 100
```

### D) Opponent Resistance (from defensive team's perspective)
```python
# When teams play against defensive team X:
opp_forces_to_pct = avg(opponent TO% in games vs X)
opp_oreb_allowed_pct = avg(opponent OREB% in games vs X)
opp_ftr_allowed = avg(opponent FTr in games vs X)
```

### E) Expected Matchup Blending
```python
expected_to_pct(teamA vs oppB) = mean(teamA_TO_pct, oppB_forces_to_pct)
expected_oreb_pct(teamA vs oppB) = mean(teamA_OREB_pct, oppB_oreb_allowed_pct)
expected_ftr(teamA vs oppB) = mean(teamA_FTr, oppB_ftr_allowed)
```

### F) Expected Empty Index (0-100 scale)
```python
to_delta = expected_to_pct - team_identity_to_pct
oreb_delta = expected_oreb_pct - team_identity_oreb_pct

empty_pressure = 50 + (to_delta * 2) - (oreb_delta * 2)
empty_pressure = clamp(empty_pressure, 0, 100)
```

---

## 4. Example JSON Response

**Endpoint:** `GET /api/game_detail?game_id=0022500479`
**Game:** ATL @ NYK (Jan 2, 2026)

```json
{
  "opponent_resistance": {
    "team": {
      "season": {
        "team_id": 1610612737,
        "games_count": 36,
        "avg_possessions": 102.34,
        "to_pct": 14.77,
        "oreb_pct": 23.51,
        "ftr": 34.38,
        "avg_empty_possessions": 46.83,
        "empty_rate": 45.76,
        "expected_to_pct": 16.42,
        "expected_oreb_pct": 22.09,
        "expected_ftr": 37.86,
        "expected_empty_index": 56.1,
        "expected_to_delta": 1.65,
        "expected_oreb_delta": -1.42
      },
      "last5": {
        "team_id": 1610612737,
        "games_count": 5,
        "avg_possessions": 102.2,
        "to_pct": 14.09,
        "oreb_pct": 21.79,
        "ftr": 33.02,
        "avg_empty_possessions": 46.0,
        "empty_rate": 45.01,
        "expected_to_pct": 14.59,
        "expected_oreb_pct": 20.96,
        "expected_ftr": 39.05,
        "expected_empty_index": 52.7,
        "expected_to_delta": 0.5,
        "expected_oreb_delta": -0.82
      }
    },
    "opp": {
      "season": {
        "team_id": 1610612752,
        "games_count": 34,
        "to_pct": 13.36,
        "oreb_pct": 29.82,
        "expected_to_pct": 16.49,
        "expected_oreb_pct": 26.97,
        "expected_empty_index": 62.0,
        "expected_to_delta": 3.13,
        "expected_oreb_delta": -2.85
      },
      "last5": { ... }
    },
    "expected": {
      "team_expected_to_pct_season": 16.42,
      "team_expected_oreb_pct_season": 22.09,
      "team_expected_empty_index_season": 56.1,
      "opp_expected_to_pct_season": 16.49,
      "opp_expected_oreb_pct_season": 26.97,
      "opp_expected_empty_index_season": 62.0,
      "empty_edge_index_season": -5.9,
      "team_expected_to_pct_last5": 14.59,
      "team_expected_oreb_pct_last5": 20.96,
      "team_expected_empty_index_last5": 52.7,
      "opp_expected_to_pct_last5": 14.55,
      "opp_expected_oreb_pct_last5": 24.98,
      "opp_expected_empty_index_last5": 49.2,
      "empty_edge_index_last5": 3.5
    }
  }
}
```

### Interpretation (ATL vs NYK):
- **ATL Season:** Identity TO% = 14.77%, Expected = 16.42% (+1.65% due to NYK's defense)
- **ATL Season:** Identity OREB% = 23.51%, Expected = 22.09% (-1.42% due to NYK's rebounding)
- **Empty Edge (Season):** -5.9 (NYK has advantage)
- **Empty Edge (Last5):** +3.5 (ATL has advantage based on recent trends)

---

## 5. Verification Results

**Test:** 10 random games from Oct 21 - Jan 2 range

**Result:** ✅ **All 10 games passed validation with no errors**

Sample Output:
```
GAME 1/10: ATL @ NYK
✅ All validation checks passed
  Home TO%: 14.77 → 16.42 (Δ+1.65)
  Home OREB%: 23.51 → 22.09 (Δ-1.42)
  Empty Edge: -5.9 (season), +3.5 (last5)

GAME 2/10: GSW @ ORL
✅ All validation checks passed
  Home TO%: 18.05 → 18.41 (Δ+0.36)
  Home OREB%: 23.32 → 22.73 (Δ-0.59)
  Empty Edge: -1.1 (season), +3.3 (last5)

[... 8 more games ...]

VERIFICATION COMPLETE
✅ SUCCESS: All 10 games passed validation with no errors
```

---

## 6. Key Observations

### Reasonable Ranges Found:
- **TO%:** 8-18% (expected)
- **OREB%:** 8-42% (wide range - some teams don't crash offensive glass)
- **Empty Rate:** 37-57% (expected)
- **Expected Deltas:** Typically ±0 to ±3% for TO/OREB

### Empty Edge Insights:
- Negative edge = opponent has advantage
- Positive edge = team has advantage
- Season vs Last5 can differ significantly (shows trend changes)

---

## 7. Notes & Approximations

### No Major Approximations Needed:
✅ Possessions available directly in DB
✅ All opponent stats (TO, OREB, DREB, FTA, FGA) available in same row
✅ No complex joins required
✅ No missing critical fields

### Design Decisions:
1. **Blending Method:** Simple mean of team identity and opponent resistance
   - Could be weighted in future (e.g., 60% team, 40% opponent)
   - Current approach is transparent and interpretable

2. **Empty Index Scale:** 0-100 with 50 as neutral
   - Formula: `50 + (to_delta * 2) - (oreb_delta * 2)`
   - Higher = more empty possessions expected
   - Lower = fewer empty possessions expected

3. **Caching:** In-memory dict for season aggregates
   - Reduces redundant calculations
   - Keyed by `season + as_of_date`

---

## 8. Frontend Integration (TODO)

### Required Changes to Game Card:

**Top Section:**
- Keep existing "Empty Possessions" display (Season + Last5)

**New Middle Section:** "Opponent Resistance"
```
┌─────────────────────────────────────────┐
│ OPPONENT RESISTANCE                     │
├─────────────────────────────────────────┤
│ TO Pressure:  14.77% → 16.42%  ▲ +1.65 │
│ OREB Impact:  23.51% → 22.09%  ▼ -1.42 │
│ Empty Index:  56.1  (vs 62.0)   -5.9   │
└─────────────────────────────────────────┘
```

**Component Structure:**
```jsx
<OpponentResistancePanel>
  <ResistanceMetric
    label="TO Pressure"
    identity={14.77}
    expected={16.42}
    delta={+1.65}
  />
  <ResistanceMetric
    label="OREB Impact"
    identity={23.51}
    expected={22.09}
    delta={-1.42}
  />
  <EmptyEdgeMetric
    teamIndex={56.1}
    oppIndex={62.0}
    edge={-5.9}
  />
</OpponentResistancePanel>
```

**Data Access:**
```javascript
const { opponent_resistance } = gameData;

// Home team metrics
const homeSeasonTO = opponent_resistance?.team?.season?.to_pct;
const homeExpectedTO = opponent_resistance?.team?.season?.expected_to_pct;
const homeTODelta = opponent_resistance?.team?.season?.expected_to_delta;

// Empty edge
const emptyEdgeSeason = opponent_resistance?.expected?.empty_edge_index_season;
const emptyEdgeLast5 = opponent_resistance?.expected?.empty_edge_index_last5;
```

---

## 9. Testing Commands

### Test Backend Module:
```bash
cd "/Users/malcolmlittle/NBA OVER UNDER SW"

# Test single game
python3 -c "
from api.utils.opponent_resistance import get_expected_matchup_metrics
import json
metrics = get_expected_matchup_metrics(1610612737, 1610612752, '2025-26', '2026-01-02')
print(json.dumps(metrics, indent=2))
"

# Run verification script
cd api/utils
python3 verify_opponent_resistance.py
```

### Test API Endpoint:
```bash
# Start server
python3 server.py

# In another terminal:
curl "http://localhost:5001/api/game_detail?game_id=0022500479" | jq '.opponent_resistance'
```

---

## 10. Success Criteria

✅ **Backend Complete:**
- [x] Schema discovered and documented
- [x] Core module created with all functions
- [x] Team identity calculation working
- [x] Opponent resistance calculation working
- [x] Expected matchup blending working
- [x] Empty index calculation working
- [x] API endpoint integration complete
- [x] Verification script passing (10/10 games)
- [x] Example JSON response generated

⏳ **Frontend Pending:**
- [ ] Create `OpponentResistancePanel` component
- [ ] Add to game card layout
- [ ] Wire up data from API
- [ ] Add visual indicators (▲/▼ arrows)
- [ ] Test responsive layout

---

## 11. Next Steps

1. **Frontend Implementation:**
   - Create React component for opponent resistance display
   - Integrate into existing game card
   - Add visual indicators (arrows, color coding)
   - Test mobile responsiveness

2. **Potential Enhancements:**
   - Add weighted blending (60% identity, 40% resistance)
   - Cache results in database for faster loads
   - Add confidence intervals based on games played
   - Add historical accuracy tracking

3. **Documentation:**
   - Add user-facing explanations of metrics
   - Create tooltip descriptions for each metric
   - Document interpretation guidelines

---

## Contact
Implementation completed by: Claude Code
Date: January 3, 2026
Backend Status: ✅ Complete
Frontend Status: ⏳ Pending
