# NBA Possession Pattern Discovery Analysis

**Date Range:** October 21, 2025 - January 1, 2026
**Data Source:** `team_game_logs` table (nba_data.db)
**Approach:** Rule-based pattern discovery (no machine learning)

---

## Overview

This analysis discovers repeatable possession patterns from NBA games using quantitative, exploratory methods. The goal is to identify what drives game outcomes beyond traditional box score stats.

### Key Metrics

- **Opportunity Edge:** `(-TO) + OREB + (0.44*FTA)` - measures extra possession opportunities
- **PPP (Points Per Possession):** Direct scoring efficiency
- **Conversion Score:** Weighted blend of TO%, OREB%, FTr (0-100 scale)
- **Empty Possessions:** Possessions without points scored

---

## Research Questions

1. **What wins games?** - Opportunity differential → win rate correlation
2. **Scoring environments** - Identify FT-driven, rebound-heavy, grind, shootout patterns
3. **Efficiency overrides** - When conversion rate matters more than possession volume
4. **Opponent context** - How opponent defensive pressure alters outcomes
5. **Data-first archetypes** - Cluster teams by TO%, OREB%, FTr (NOT pace/PPP)
6. **Prop environments** - High assist/rebound/scoring conditions (player-agnostic)
7. **Failure analysis** - Games where possession patterns broke down

---

## Project Structure

```
/Users/malcolmlittle/NBA OVER UNDER SW/
├── analysis/
│   ├── notebooks/
│   │   └── possession_pattern_discovery.ipynb    # Interactive exploration
│   ├── outputs/
│   │   ├── findings/                             # CSV results
│   │   └── reports/                              # Markdown summaries
│   └── README.md
│
├── api/utils/
│   ├── possession_dataset_builder.py             # Core dataset builder
│   ├── possession_metrics.py                     # Bucketing/classification
│   ├── pattern_analyzer.py                       # 7 analysis functions
│   └── empty_possessions_calculator.py           # Existing utilities (reused)
```

---

## Modules

### 1. `possession_dataset_builder.py`

Transforms `team_game_logs` into possession-focused analysis dataset.

**Key Function:**
```python
build_possession_dataset(
    season='2025-26',
    start_date='2024-10-21',  # Auto-adjusted to 2025-10-21 for season
    end_date='2026-01-01',
    output_format='dataframe'  # or 'csv', 'json'
)
```

**Output Columns (~40):**
- Identifiers: `game_id`, `team_id`, `opponent_id`, `game_date`, `is_home`, `win_loss`
- Raw stats: `FGA`, `FGM`, `FTA`, `FTM`, `OREB`, `DREB`, `TO`, `points`, `assists`
- Possessions: `possessions`, `opp_possessions`
- Opportunity metrics: `opportunity_edge`, `opportunity_diff`
- Efficiency: `ppp`, `empty_rate`, `conversion_score`
- Core levers: `TO_pct`, `OREB_pct`, `FTr`
- Game context: `pace`, `off_rating`, `def_rating`
- Opponent context: `opp_TO_pct`, `opp_OREB_pct`, `opp_FTr`

**Critical Fixes Applied:**
1. **Season-aware dates:** Oct 21 = 2025, Jan 1 = 2026 for '2025-26' season
2. **Opportunity edge:** `(-TO) + OREB + (0.44*FTA)` instead of possession_diff
3. **Separate metrics:** PPP, conversion_score, empty_rate are distinct

---

### 2. `possession_metrics.py`

Bucketing, classification, and efficiency scoring.

**Key Functions:**
- `classify_scoring_environment(row)` - FT-driven, Rebound-heavy, Grind, Shootout, etc.
- `bucket_by_percentile(series, buckets=5)` - Quintile bucketing
- `calculate_efficiency_override_score(row)` - Conversion vs volume tradeoff
- `identify_failure_games(df)` - Unexpected losses
- `calculate_team_archetype_percentiles(df)` - Cluster on TO%/OREB%/FTr ONLY

---

### 3. `pattern_analyzer.py`

Statistical pattern discovery for 7 research questions.

**Analysis Functions:**
- `analyze_opportunity_differential_patterns(df)` - Q1
- `analyze_scoring_environments(df)` - Q2
- `analyze_efficiency_overrides(df)` - Q3
- `analyze_opponent_context_effects(df)` - Q4
- `cluster_by_possession_behavior(df)` - Q5
- `identify_prop_environments(df)` - Q6
- `analyze_failure_cases(df)` - Q7

**Orchestration:**
```python
run_all_analyses(df)  # Runs all 7 analyses, returns combined results
```

---

## Usage

### Option 1: Jupyter Notebook (Interactive)

```bash
cd "/Users/malcolmlittle/NBA OVER UNDER SW/analysis/notebooks"
jupyter notebook possession_pattern_discovery.ipynb
```

Run all cells sequentially to:
1. Load dataset
2. Execute 7 analyses with visualizations
3. Save findings to CSV

---

### Option 2: Python Script (Programmatic)

```python
import sys
sys.path.append('/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.possession_dataset_builder import build_possession_dataset
from api.utils.pattern_analyzer import run_all_analyses

# Load data
df = build_possession_dataset(season='2025-26')

# Run all analyses
results = run_all_analyses(df)

# Access specific results
print(results['q1_opportunity_differential']['correlation'])
print(results['q5_possession_archetypes']['archetype_distribution'])
```

---

## Output Files

Generated in `/analysis/outputs/findings/`:

- `possession_dataset.csv` - Full dataset (optional)
- `q1_failure_games.csv` - Games where opportunity advantage didn't translate to win
- `q3_override_games.csv` - Games where efficiency overcame volume deficit
- `q5_team_archetypes.csv` - Team percentiles and archetype labels
- `q6_multi_prop_games.csv` - Games with multiple favorable prop conditions
- `q7_failure_games.csv` - Unexpected losses with severity scores

---

## Pattern Strength Criteria

**Production-Ready (Strong):**
- Sample size > 100 games
- Correlation > 0.5 OR win rate difference > 20%
- Stable across time windows

**Moderate:**
- Correlation 0.3-0.5
- Needs validation before production use

**Weak (Exploratory):**
- Correlation < 0.3
- Informational only, not actionable

---

## Key Implementation Details

### Date Range Handling

The season `'2025-26'` spans calendar years:
- October-December 2025 (first year)
- January-June 2026 (second year)

`build_possession_dataset()` automatically adjusts dates based on month:
- Oct 21 → 2025-10-21
- Jan 1 → 2026-01-01

### Opportunity Edge vs Possession Differential

**Opportunity Edge** is preferred because it measures *extra opportunities* rather than possession count:

```python
# OLD (possession_diff): Just counts total possessions
possession_diff = team_poss - opp_poss

# NEW (opportunity_edge): Measures opportunity-creating actions
opportunity_edge = (-TO) + OREB + (0.44*FTA)
opportunity_diff = team_edge - opp_edge
```

**Why this matters:**
- Turnovers create opponent possessions (negative impact)
- Offensive rebounds create extra possessions (positive impact)
- Free throws create scoring without using a possession (positive impact)

### PPP vs Conversion Score

**PPP (Points Per Possession):** Direct scoring efficiency
```python
ppp = points / possessions  # e.g., 1.08
```

**Conversion Score:** Normalized blend of possession levers (0-100 scale)
```python
conversion_score = (
    normalize_to_pct(TO_pct) * 0.40 +
    normalize_oreb_pct(OREB_pct) * 0.30 +
    normalize_ftr(FTr) * 0.30
)
```

**Use cases:**
- PPP: Compare raw scoring efficiency
- Conversion Score: Evaluate process quality (independent of shooting variance)

---

## Dependencies

- `pandas` - Data manipulation
- `sqlite3` - Database access
- `matplotlib`, `seaborn` - Visualizations (notebook only)
- Existing modules: `empty_possessions_calculator.py`, `db_config.py`

---

## Next Steps

1. **Run initial analysis** - Execute notebook to validate findings
2. **Identify strong patterns** - Correlations > 0.5 or win rate diff > 20%
3. **Integrate into production** - Add actionable patterns to main app
4. **Iterate** - Refine thresholds based on validation results

---

## Questions or Issues?

Contact: Malcolm Little
Project: NBA Over/Under Prediction System
