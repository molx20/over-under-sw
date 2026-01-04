# Backend Requirements for Possession UI

## Critical: NO PLACEHOLDERS

All UI enhancements only render when real data is provided. Missing fields = no display.

---

## Required Backend Changes

### **1. Empty Possessions Endpoint** (`/game_detail` → `empty_possessions`)

Add the following fields to make `PregamePossessionOutlook` appear:

```python
{
  # === GAME-LEVEL (required for pregame outlook) ===
  "projected_game_possessions": int,        # Total expected possessions
  "expected_empty_possessions_game": int,   # Total expected empty possessions
  "expected_empty_rate": float,             # Expected empty rate (%)
  "league_avg_empty_rate": float,           # League average for comparison

  # === EXISTING FIELDS (keep as-is) ===
  "matchup_score": float,
  "matchup_summary": str,

  "home_team": {
    # === NEW FIELDS (required for team possession section) ===
    "projected_team_possessions": int,      # Expected possessions for this team
    "expected_empty_possessions": int,      # Expected empties for this team
    "empty_rate": float,                    # Team's expected empty rate (%)

    # === NEW FIELDS (required for main drivers) ===
    "driver_turnovers_empty": int,          # Empty possessions from turnovers (COUNT)
    "driver_oreb_empty": int,               # Empty possessions saved by OREBs (COUNT)
    "driver_fts_points": int,               # Expected points from free throws (NOT empties)

    # === EXISTING FIELDS (keep as-is) ===
    "season": { "to_pct": float, "oreb_pct": float, "ftr": float, "score": float },
    "last5": { "to_pct": float, "oreb_pct": float, "ftr": float, "score": float },
    "blended_score": float,
    "opp_context": { "to_trend": str, "oreb_trend": str, "ftr_trend": str }
  },

  "away_team": {
    # Same structure as home_team
  }
}
```

---

## UI Rendering Logic

### **Section 1: Pregame Possession Outlook**

**Renders if ALL of these exist:**
- `projected_game_possessions`
- `expected_empty_possessions_game`
- `expected_empty_rate`
- `league_avg_empty_rate`

**Returns `null` if any field is missing.**

---

### **Section 2: Expected Team Possessions**

**Renders if ALL of these exist (per team):**
- `projected_team_possessions`
- `expected_empty_possessions`
- `empty_rate`

**Main Drivers sub-section renders if ALL of these exist:**
- `driver_turnovers_empty`
- `driver_oreb_empty`
- `driver_fts_points`

**Returns `null` if any required field is missing.**

---

### **Section 3: Opponent Impact on Possessions**

**Always renders** - uses existing fields from `opponent_resistance`:
- `expected_to_delta` (percentage points)
- `expected_oreb_delta` (percentage points)
- `avg_possessions`

Frontend calculates:
- `deltaEmptyTO = avg_possessions * (expected_to_delta / 100)`
- `deltaEmptyOREB = -(avg_possessions * 0.55) * (expected_oreb_delta / 100)`
- `Net Effect = deltaEmptyTO + deltaEmptyOREB`

**Note:** Currently uses hardcoded `0.55` for misses per possession. Backend should ideally provide `misses_per_possession` field.

---

### **Section 4: Total Lens**

**Already works** - uses existing `combined_opportunities` and `combined_empty` fields.

---

## Example Backend Response

```json
{
  "success": true,
  "prediction": { ... },
  "empty_possessions": {
    "projected_game_possessions": 200,
    "expected_empty_possessions_game": 82,
    "expected_empty_rate": 41.0,
    "league_avg_empty_rate": 40.2,

    "home_team": {
      "team_id": 1610612738,
      "projected_team_possessions": 100,
      "expected_empty_possessions": 41,
      "empty_rate": 41.0,
      "driver_turnovers_empty": 12,
      "driver_oreb_empty": 8,
      "driver_fts_points": 15,

      "season": { "to_pct": 13.5, "oreb_pct": 25.0, "ftr": 22.0, "score": 60 },
      "last5": { "to_pct": 14.0, "oreb_pct": 24.0, "ftr": 21.0, "score": 58 },
      "blended_score": 59,
      "opp_context": {
        "to_trend": "up",
        "oreb_trend": "down",
        "ftr_trend": "neutral"
      }
    },

    "away_team": {
      "team_id": 1610612747,
      "projected_team_possessions": 100,
      "expected_empty_possessions": 41,
      "empty_rate": 41.0,
      "driver_turnovers_empty": 11,
      "driver_oreb_empty": 9,
      "driver_fts_points": 16,

      "season": { "to_pct": 12.8, "oreb_pct": 27.0, "ftr": 24.0, "score": 62 },
      "last5": { "to_pct": 13.0, "oreb_pct": 28.0, "ftr": 23.0, "score": 61 },
      "blended_score": 61,
      "opp_context": {
        "to_trend": "neutral",
        "oreb_trend": "up",
        "ftr_trend": "down"
      }
    },

    "matchup_score": 65,
    "matchup_summary": "Good possession conversion expected with balanced offense expected from both teams."
  },

  "opponent_resistance": {
    "team": {
      "season": {
        "to_pct": 13.5,
        "oreb_pct": 25.0,
        "ftr": 22.0,
        "expected_to_pct": 14.2,
        "expected_oreb_pct": 23.5,
        "expected_ftr": 23.0,
        "expected_to_delta": 0.7,
        "expected_oreb_delta": -1.5,
        "expected_ftr_delta": 1.0,
        "avg_possessions": 100
      },
      "last5": { /* same structure */ }
    },
    "opp": { /* same structure */ },
    "expected": {
      "empty_edge_index_season": 5.2,
      "empty_edge_index_last5": 3.8
    }
  }
}
```

---

## Calculation Formulas for Backend

### **Projected Game Possessions**
```python
projected_game_possessions = (
    home_team_avg_possessions + away_team_avg_possessions
)
```

### **Expected Empty Possessions (per team)**
```python
expected_empty_possessions = projected_team_possessions * (empty_rate / 100)
```

### **Expected Empty Possessions (game)**
```python
expected_empty_possessions_game = (
    home_expected_empty_possessions + away_expected_empty_possessions
)
```

### **Driver Counts**
```python
# Turnovers (COUNT not %)
driver_turnovers_empty = projected_team_possessions * (to_pct / 100)

# OREB (COUNT not %)
projected_misses = projected_team_possessions * misses_per_possession
driver_oreb_empty = projected_misses * (oreb_pct / 100)

# Free throws (POINTS not empties)
driver_fts_points = projected_team_possessions * (ftr / 100) * avg_ft_pct
```

### **Empty Rate**
```python
empty_rate = (expected_empty_possessions / projected_team_possessions) * 100
```

---

## Testing Checklist

- [ ] `projected_game_possessions` returns realistic value (190-210 range)
- [ ] `expected_empty_possessions_game` returns realistic value (75-90 range)
- [ ] `league_avg_empty_rate` is stable (around 40%)
- [ ] Per-team `projected_team_possessions` sums to game total
- [ ] Per-team `expected_empty_possessions` sums to game total
- [ ] Driver counts are whole numbers (no decimals)
- [ ] Driver counts are reasonable (turnovers: 10-15, OREBs: 7-12, FT points: 12-20)
- [ ] All fields present = all 4 UI sections visible
- [ ] Missing any field = that section invisible (graceful degradation)

---

## Current State

**Working Sections:**
- ✅ Section 3: Opponent Impact (uses existing data)
- ✅ Section 4: Total Lens (uses existing data)

**Blocked Sections (need backend data):**
- ❌ Section 1: Pregame Possession Outlook
- ❌ Section 2: Expected Team Possessions
- ❌ Section 2: Main Drivers

**Graceful Degradation:**
All blocked sections simply don't render. No errors, no placeholders, no fake data.
