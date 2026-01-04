# Expected FT Points - Backend API Specification

## Overview

New fields required to display Free Throw scoring impact as pregame projections (points, not possessions).

---

## Data Structure

### **Opponent Resistance Endpoint** (`opponent_resistance`)

Add `free_throw_points` object to each team's data (both `season` and `last5` windows):

```json
{
  "team": {
    "season": {
      // === EXISTING FIELDS (keep as-is) ===
      "to_pct": 13.5,
      "oreb_pct": 25.0,
      "ftr": 22.0,
      "expected_to_pct": 14.2,
      "expected_oreb_pct": 23.5,
      "expected_ftr": 23.0,
      "expected_to_delta": 0.7,
      "expected_oreb_delta": -1.5,
      "expected_ftr_delta": 1.0,
      "avg_possessions": 100,

      // === NEW FIELD ===
      "free_throw_points": {
        "baseline_ftr": 22.0,                      // Team's identity FTr (FTA/FGA)
        "adjusted_ftr": 23.0,                      // Opponent-adjusted FTr
        "expected_fga": 85.0,                      // Projected field goal attempts
        "expected_fta_baseline": 18.7,             // Expected FTA (baseline)
        "expected_fta_adjusted": 19.6,             // Expected FTA (adjusted)
        "ft_pct_used": 0.78,                       // FT% used in calculation
        "expected_ft_points_baseline": 14.6,       // Baseline FT points
        "expected_ft_points_adjusted": 15.3,       // Opponent-adjusted FT points
        "net_ft_points_impact": 0.7                // Adjusted - Baseline (in points)
      }
    },
    "last5": {
      // Same structure as season
    }
  },

  "opp": {
    "season": {
      // Same structure as team
    },
    "last5": {
      // Same structure as team
    }
  }
}
```

---

### **Possession Insights Endpoint** (`possession_insights`)

Add `combined_ft_points` to the `section_3_total` object:

```json
{
  "home_team": {
    "section_3_total": {
      // === EXISTING FIELDS (keep as-is) ===
      "combined_empty": 41.0,
      "combined_opportunities": 200,
      "label": "High variance",

      // === NEW FIELD ===
      "combined_ft_points": {
        "adjusted": 30.6,        // Sum of both teams' adjusted FT points
        "net_impact": 1.4         // Sum of both teams' net impacts
      }
    }
  },

  "away_team": {
    // Same structure as home_team
  }
}
```

---

## Calculation Formulas

### **Per Team (in `opponent_resistance`)**

```python
# 1. Baseline FT Points
expected_fga = projected_team_possessions * (1 - to_pct/100)  # Possessions minus turnovers
baseline_ftr = team_identity_ftr
expected_fta_baseline = expected_fga * (baseline_ftr / 100)
expected_ft_points_baseline = expected_fta_baseline * ft_pct_used

# 2. Opponent-Adjusted FT Points
adjusted_ftr = (team_identity_ftr + opp_resistance_ftr_allowed) / 2
expected_fta_adjusted = expected_fga * (adjusted_ftr / 100)
expected_ft_points_adjusted = expected_fta_adjusted * ft_pct_used

# 3. Net Impact
net_ft_points_impact = expected_ft_points_adjusted - expected_ft_points_baseline
```

**Notes:**
- `ft_pct_used`: Team's FT% (typically 75-80%). Use season average.
- `expected_fga`: Can approximate as `possessions * 0.85` if exact FGA unavailable
- All values should be floats with 1 decimal precision

---

### **Combined (in `possession_insights`)**

```python
# For each team's section_3_total
combined_ft_points = {
    "adjusted": home_adjusted + away_adjusted,
    "net_impact": home_net_impact + away_net_impact
}
```

---

## Field Definitions

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `baseline_ftr` | float | Team's identity FTr (no opponent adjustment) | 22.0 |
| `adjusted_ftr` | float | FTr blended with opponent's FTr allowed | 23.0 |
| `expected_fga` | float | Projected field goal attempts | 85.0 |
| `expected_fta_baseline` | float | Expected FTA using baseline FTr | 18.7 |
| `expected_fta_adjusted` | float | Expected FTA using adjusted FTr | 19.6 |
| `ft_pct_used` | float | FT% used in calculation (0.75 - 0.85 range) | 0.78 |
| `expected_ft_points_baseline` | float | Baseline FT points (pregame) | 14.6 |
| `expected_ft_points_adjusted` | float | Opponent-adjusted FT points (pregame) | 15.3 |
| `net_ft_points_impact` | float | Adjusted minus Baseline (delta in points) | 0.7 |

---

## UI Rendering Rules

### **OpponentResistancePanel**

**Shows:**
- Baseline FT Points
- Opponent-Adjusted FT Points
- Net FT Impact (with +/− sign and color)

**Color Logic:**
- `net_ft_points_impact > 0.5` → GREEN (more points = good)
- `net_ft_points_impact < -0.5` → RED (fewer points = bad)
- `-0.5 ≤ net_ft_points_impact ≤ 0.5` → GRAY (neutral)

**Only renders if:** `data.free_throw_points` exists

---

### **PossessionInsightsPanel**

**Shows:**
- Combined FT Points (Adj)
- Net FT Impact (with +/− sign and color)

**Only renders if:** `total.combined_ft_points` exists

---

## Example API Response

```json
{
  "success": true,
  "opponent_resistance": {
    "team": {
      "season": {
        "to_pct": 13.5,
        "oreb_pct": 25.0,
        "ftr": 22.0,
        "expected_ftr": 23.0,
        "expected_ftr_delta": 1.0,
        "avg_possessions": 100,

        "free_throw_points": {
          "baseline_ftr": 22.0,
          "adjusted_ftr": 23.0,
          "expected_fga": 85.0,
          "expected_fta_baseline": 18.7,
          "expected_fta_adjusted": 19.6,
          "ft_pct_used": 0.78,
          "expected_ft_points_baseline": 14.6,
          "expected_ft_points_adjusted": 15.3,
          "net_ft_points_impact": 0.7
        }
      }
    }
  },

  "possession_insights": {
    "home_team": {
      "section_3_total": {
        "combined_empty": 41.0,
        "combined_opportunities": 200,
        "label": "High variance",

        "combined_ft_points": {
          "adjusted": 30.6,
          "net_impact": 1.4
        }
      }
    }
  }
}
```

---

## Testing Checklist

- [ ] `baseline_ftr` matches team's identity FTr
- [ ] `adjusted_ftr` is blended with opponent's FTr allowed
- [ ] `expected_fga` is realistic (80-90 range for most teams)
- [ ] `expected_fta_baseline` and `expected_fta_adjusted` are reasonable (15-25 range)
- [ ] `ft_pct_used` is between 0.70 and 0.85
- [ ] `expected_ft_points_baseline` and `adjusted` are realistic (12-20 range per team)
- [ ] `net_ft_points_impact` is reasonable (-5 to +5 range)
- [ ] Combined values sum correctly across both teams
- [ ] UI section appears when data is present
- [ ] UI section is hidden when data is missing (graceful degradation)
- [ ] Green/red colors display correctly based on net impact
- [ ] Works for both Season and Last 5 windows

---

## Current State

**Working Sections (no backend changes needed):**
- ✅ Foul Rate row (already displays FTr with correct scoring logic)
- ✅ Opponent Impact on Possessions (excludes FT points correctly)

**Blocked Sections (need backend data):**
- ❌ Expected FT Points (in OpponentResistancePanel)
- ❌ FT Points Environment (in PossessionInsightsPanel)

**Graceful Degradation:**
Both new sections use conditional rendering - they simply don't appear if data is missing. No errors, no placeholders.
