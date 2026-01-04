# Possession-Based UI Enhancements

## Overview
This document outlines the UI enhancements made to expose possession-based insights in the pre-game analysis interface.

---

## Updated Component List

### 1. **EmptyPossessionsGauge.jsx**

#### New Components Added:
- `PregamePossessionOutlook` - Displays game-level possession projections at the top of the card

#### Modified Components:
- `TeamSection` - Enhanced with "Expected Team Possessions" subsection and "Main Drivers" breakdown

---

### 2. **OpponentResistancePanel.jsx**

#### Modified Components:
- `ResistanceCard` - Replaced "Expected Empty Index" (0-100 scale) with "Opponent Impact on Possessions" (actual counts)

---

### 3. **PossessionInsightsPanel.jsx**

#### Modified Components:
- `Section3TotalLens` - Added clarification caption and updated field labels for clarity

---

## New Props Expected from Backend

### **EmptyPossessionsGauge** (`emptyPossessionsData`)

```javascript
{
  // === NEW FIELDS NEEDED ===
  projected_game_possessions: 200,        // Total expected possessions for the game
  expected_empty_possessions_game: 82,    // Total expected empty possessions
  expected_empty_rate: 41.0,              // Expected empty rate (percentage)
  league_avg_empty_rate: 40.0,            // League average for comparison

  // === EXISTING FIELDS (unchanged) ===
  matchup_score: 65,
  matchup_summary: "Good possession conversion expected...",

  home_team: {
    team_id: 1610612738,

    // === NEW FIELDS NEEDED (per team) ===
    projected_team_possessions: 100,      // Expected possessions for this team
    expected_empty_possessions: 41,       // Expected empties for this team
    empty_rate: 41.0,                     // Team's expected empty rate

    // Main drivers (counts, not percentages)
    driver_turnovers_empty: 12,           // Empty possessions from turnovers
    driver_oreb_empty: 8,                 // Empty possessions saved by OREBs
    driver_fts_points: 15,                // Expected points from free throws

    // === EXISTING FIELDS (unchanged) ===
    season: { to_pct: 13.5, oreb_pct: 25.0, ftr: 22.0, score: 60 },
    last5: { to_pct: 14.0, oreb_pct: 24.0, ftr: 21.0, score: 58 },
    blended_score: 59,
    opp_context: {
      to_trend: 'up',
      oreb_trend: 'down',
      ftr_trend: 'neutral'
    }
  },

  away_team: {
    // Same structure as home_team
  }
}
```

### **OpponentResistancePanel** (`resistanceData`)

```javascript
{
  team: {
    season: {
      // === EXISTING FIELDS (unchanged) ===
      to_pct: 13.5,
      oreb_pct: 25.0,
      ftr: 22.0,
      expected_to_pct: 14.2,
      expected_oreb_pct: 23.5,
      expected_ftr: 23.0,
      expected_to_delta: 0.7,
      expected_oreb_delta: -1.5,
      expected_ftr_delta: 1.0,
      avg_possessions: 100,

      // === REMOVED FIELD (no longer displayed) ===
      // expected_empty_index: 52  // NOT shown in UI anymore
    },
    last5: {
      // Same structure as season
    }
  },

  opp: {
    // Same structure as team
  },

  expected: {
    empty_edge_index_season: 5.2,
    empty_edge_index_last5: 3.8
  }
}
```

**Note:** The `deltaEmptyTO` and `deltaEmptyOREB` are calculated on the frontend using:
- `calculateDeltaEmptyTO(teamPossessions, expected_to_delta)`
- `calculateDeltaEmptyOREB(teamPossessions, expected_oreb_delta)`

---

## Example Render with Dummy Data

### **Example 1: Empty Possessions Analysis Card**

```
┌─────────────────────────────────────────────────────────────┐
│  Empty Possessions Analysis                        [Glossary]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Pregame Possession Outlook                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Projected Game Possessions:              200          │  │
│  │ Expected Empty Possessions:               82          │  │
│  │ Expected Empty Rate:                    41.0%         │  │
│  │ Expected Scoring Possessions:            118          │  │
│  │                                                        │  │
│  │ League Avg Empty Rate: 40.0% | This Game: +1.0%      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  [████████████████████████████████████░░░░░░░] 65            │
│   Poor                                     Excellent          │
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │ Boston Celtics       │  │ LA Lakers            │         │
│  │                      │  │                      │         │
│  │ TO%: 13.5% | L5: 14%│  │ TO%: 12.8% | L5: 13%│         │
│  │ OREB%: 25% | L5: 24%│  │ OREB%: 27% | L5: 28%│         │
│  │ FTr: 22% | L5: 21%  │  │ FTr: 24% | L5: 23%  │         │
│  │                      │  │                      │         │
│  │ Expected Team        │  │ Expected Team        │         │
│  │ Possessions          │  │ Possessions          │         │
│  │                      │  │                      │         │
│  │ Projected Team       │  │ Projected Team       │         │
│  │ Possessions:    100  │  │ Possessions:    100  │         │
│  │ Expected Empty       │  │ Expected Empty       │         │
│  │ Possessions:     41  │  │ Possessions:     41  │         │
│  │ Empty Rate:    41.0% │  │ Empty Rate:    41.0% │         │
│  │                      │  │                      │         │
│  │ Main Drivers         │  │ Main Drivers         │         │
│  │ Turnovers:           │  │ Turnovers:           │         │
│  │   +12 empty poss     │  │   +11 empty poss     │         │
│  │ Offensive Rebounds:  │  │ Offensive Rebounds:  │         │
│  │   −8 empty poss      │  │   −9 empty poss      │         │
│  │ Fouls (FTs):         │  │ Fouls (FTs):         │         │
│  │   +15 expected pts   │  │   +16 expected pts   │         │
│  │                      │  │                      │         │
│  │ Conversion Score: 59 │  │ Conversion Score: 61 │         │
│  └──────────────────────┘  └──────────────────────┘         │
│                                                               │
│  Good possession conversion expected with balanced offense   │
│  expected from both teams.                                    │
└─────────────────────────────────────────────────────────────┘
```

---

### **Example 2: Opponent Resistance Panel**

```
┌─────────────────────────────────────────────────────────────┐
│  Opponent Resistance Impact          [Season] [Last 5] [Both]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────┐  ┌────────────────────────┐     │
│  │ BOSTON CELTICS (Away)  │  │ LA LAKERS (Home)       │     │
│  ├────────────────────────┤  ├────────────────────────┤     │
│  │                        │  │                        │     │
│  │ ⚠ TO Pressure          │  │ ⚠ TO Pressure          │     │
│  │ 13.5% → 14.2% (+0.7)   │  │ 12.8% → 13.5% (+0.7)   │     │
│  │ Turnover rate adjusted │  │ Turnover rate adjusted │     │
│  │ for opponent defense   │  │ for opponent defense   │     │
│  │ ≈ +0.7 empty poss      │  │ ≈ +0.7 empty poss      │     │
│  │                        │  │                        │     │
│  │ ↻ OREB Impact          │  │ ↻ OREB Impact          │     │
│  │ 25.0% → 23.5% (−1.5)   │  │ 27.0% → 25.0% (−2.0)   │     │
│  │ Offensive rebound rate │  │ Offensive rebound rate │     │
│  │ adjusted for opponent  │  │ adjusted for opponent  │     │
│  │ ≈ −0.8 empty poss      │  │ ≈ −1.1 empty poss      │     │
│  │                        │  │                        │     │
│  │ ✓ Foul Rate            │  │ ✓ Foul Rate            │     │
│  │ 22.0% → 23.0% (+1.0)   │  │ 24.0% → 25.0% (+1.0)   │     │
│  │ Free throw rate        │  │ Free throw rate        │     │
│  │ adjusted for opponent  │  │ adjusted for opponent  │     │
│  │                        │  │                        │     │
│  │ Opponent Impact on     │  │ Opponent Impact on     │     │
│  │ Possessions            │  │ Possessions            │     │
│  │                        │  │                        │     │
│  │ From Turnover Pressure:│  │ From Turnover Pressure:│     │
│  │   +0.7 empty poss      │  │   +0.7 empty poss      │     │
│  │ From Offensive         │  │ From Offensive         │     │
│  │ Rebounding:            │  │ Rebounding:            │     │
│  │   −0.8 empty poss      │  │   −1.1 empty poss      │     │
│  │ ───────────────────────│  │ ───────────────────────│     │
│  │ Net Opponent Effect:   │  │ Net Opponent Effect:   │     │
│  │   −0.1 empty poss      │  │   −0.4 empty poss      │     │
│  └────────────────────────┘  └────────────────────────┘     │
│                                                               │
│  ━ Empty Edge  ━━━━━━━━━━━━━━━  LAL vs BOS  ━━  +2.3  ━━━  │
│                                               Home Advantage  │
└─────────────────────────────────────────────────────────────┘
```

---

### **Example 3: Possession Insights Panel (Total Lens)**

```
┌─────────────────────────────────────────────────────────────┐
│  Total Lens                                                   │
│  Combined Opportunities = Projected Game Possessions          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Projected Game Possessions:                           200    │
│  Expected Empty Possessions:                          82.0    │
│                                                               │
│  [Variance: High variance]                                    │
│                                                               │
│  Translation (Counts)                           [Projected]   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Projected Possessions (Game):              200.0     │    │
│  │ Expected Empty Possessions:                 82.0     │    │
│  │ Expected Scoring Possessions:              118.0     │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Notes

### Rules Followed:
- ✅ All values are PRE-GAME projections
- ✅ Whole numbers used (roundWhole for counts)
- ✅ Numbers < 0.5 round to 0
- ✅ No tooltips except for formula explanations
- ✅ No color gradients (only discrete green/red for deltas)
- ✅ NO indexes or 0-100 scales displayed
- ✅ Only possession COUNTS shown in opponent impact sections

### Calculations Used:
- `roundWhole(x)` - Rounds to nearest integer, returns 0 if < 0.5
- `round1(x)` - Rounds to 1 decimal place
- `formatSigned(x)` - Adds +/− sign to number
- `getDeltaVsLeagueColor(delta)` - Returns green if below league avg, red if above
- `getDeltaEmptyColor(delta)` - Returns orange if positive (more empties), green if negative (fewer empties)
- `calculateDeltaEmptyTO(possessions, deltaPct)` - Converts TO% change to empty possession count
- `calculateDeltaEmptyOREB(possessions, deltaPct)` - Converts OREB% change to empty possession count (negative)

### Data Availability:
**NO PLACEHOLDERS** - All new UI sections only render when real data is provided by the backend.

- `PregamePossessionOutlook` - Returns `null` if any required field is missing
- `Expected Team Possessions` - Only renders if possession counts are available
- `Main Drivers` - Only renders if driver data is available
- `Opponent Impact on Possessions` - Renders using calculated values from existing `expected_to_delta` and `expected_oreb_delta` fields

---

## Files Modified

1. **src/components/EmptyPossessionsGauge.jsx**
   - Added `PregamePossessionOutlook` component
   - Enhanced `TeamSection` with possession counts and main drivers
   - De-emphasized Conversion Score (still visible but smaller)

2. **src/components/OpponentResistancePanel.jsx**
   - Removed Expected Empty Index (0-100 scale) from display
   - Added "Opponent Impact on Possessions" with possession counts

3. **src/components/PossessionInsightsPanel.jsx**
   - Added clarification caption to Total Lens
   - Updated field labels for clarity
   - Emphasized projected game possessions

---

## Next Steps (Backend)

**See `BACKEND_REQUIREMENTS.md` for complete implementation guide.**

### Summary:

**NO PLACEHOLDERS** - UI sections only render when backend provides real data.

**Currently Working:**
- ✅ Opponent Impact on Possessions (uses existing `opponent_resistance` data)
- ✅ Total Lens (uses existing `possession_insights` data)

**Blocked (need backend implementation):**
- ❌ Pregame Possession Outlook (needs 4 game-level fields)
- ❌ Expected Team Possessions (needs 3 per-team fields)
- ❌ Main Drivers (needs 3 per-team count fields)

**Behavior:**
- Missing data = section invisibly skipped (no errors, no fake numbers)
- Partial data = partial rendering (graceful degradation)
- Full data = all sections visible

---

## Visual Design Principles Applied

1. **No Abstractions** - Every number directly answers a possession question
2. **Counts Over Percentages** - Main metrics shown as actual possession counts
3. **Clear Hierarchy** - Most important numbers (game projections) at the top
4. **Minimal Color** - Only green/red on deltas vs meaningful thresholds
5. **Direct Language** - "Expected Empty Possessions" instead of "Empty Index"
6. **Signed Numbers** - Always show +/− for deltas and impacts
