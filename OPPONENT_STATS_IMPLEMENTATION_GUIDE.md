# Opponent Statistics - Complete Implementation Guide

## Executive Summary

**Status: 60% COMPLETE ✅**

### ✅ Completed:
1. Database schema extended (59 new columns across 2 tables)
2. Opponent stats computation module created (`opponent_stats_calculator.py`)
3. Possession formula implemented and validated
4. All 896 existing game records backfilled with opponent stats
5. Migration scripts created and executed

### 🔄 Remaining (40%):
1. Season aggregation module (aggregate per-game → season averages)
2. ETL integration (update `sync_nba_data.py`)
3. Prediction engine integration (use opponent stats in predictions)
4. AI Coach enhancement (explain using opponent stats)
5. Frontend display updates

---

## Implementation Progress

### Part 1: Database Schema ✅ COMPLETE

**Files Created:**
- `migrate_opponent_stats_schema.py`

**Columns Added to `team_game_logs` (28):**
- Opponent shooting: `opp_fgm`, `opp_fga`, `opp_fg_pct`, `opp_fg2m`, `opp_fg2a`, `opp_fg2_pct`, `opp_fg3m`, `opp_fg3a`, `opp_fg3_pct`
- Opponent free throws: `opp_ftm`, `opp_fta`, `opp_ft_pct`
- Opponent rebounds: `opp_offensive_rebounds`, `opp_defensive_rebounds`, `opp_rebounds`
- Opponent playmaking: `opp_assists`, `opp_turnovers`, `opp_steals`, `opp_blocks`
- Opponent advanced: `opp_pace`, `opp_off_rating`, `opp_def_rating`
- Opponent scoring: `opp_points_off_turnovers`, `opp_fast_break_points`, `opp_points_in_paint`, `opp_second_chance_points`
- Possessions: `possessions`, `opp_possessions`

**Columns Added to `team_season_stats` (31):**
- Same stats as above (season averages)
- Plus rankings: `opp_fg_pct_rank`, `opp_ft_pct_rank`, `opp_rebounds_rank`, `opp_assists_rank`, `opp_pace_rank`, `opp_off_rating_rank`, `opp_def_rating_rank`

### Part 2: Opponent Stats Computation ✅ COMPLETE

**Files Created:**
- `api/utils/opponent_stats_calculator.py`

**Key Functions:**
```python
def compute_possessions(fga, fta, oreb, tov) -> float:
    """Formula: FGA + 0.44*FTA - OREB + TOV"""
    return fga + (0.44 * fta) - oreb + tov

def compute_opponent_stats_for_game(game_id, conn) -> Dict:
    """For each team in a game, opponent stats = other team's stats"""
    # Extracts both teams' stats
    # Swaps them (team A's opponent = team B, team B's opponent = team A)
    # Updates database with opponent stats + possessions

def backfill_all_opponent_stats(season, limit) -> Dict:
    """Processes all games and computes opponent stats"""
    # Processed 448 games, updated 896 team records
```

**Validation Results:**
```
✅ Possession formula: FGA=85, FTA=24, OREB=10, TOV=14 → 99.6 possessions
✅ 448 games processed successfully
✅ 896 team records updated
✅ 0 errors
✅ Sample: Game 0022500351 - Team 3PA=39, Opp 3PA=38, Possessions=113.2
```

---

## Part 3: Season Aggregation Module (TO IMPLEMENT)

Create file: `api/utils/season_opponent_stats_aggregator.py`

```python
"""
Season Opponent Statistics Aggregator

Aggregates per-game opponent stats into season averages for each team.
This computes what each team ALLOWS their opponents to do on average.
"""

import sqlite3
from typing import Dict, Optional
from api.utils.db_config import get_db_path

NBA_DATA_DB_PATH = get_db_path('nba_data.db')

def aggregate_season_opponent_stats(
    team_id: int,
    season: str,
    split_type: str = 'overall',
    conn: Optional[sqlite3.Connection] = None
) -> Dict:
    """
    Aggregate opponent stats for a team's season.

    Args:
        team_id: Team ID
        season: Season (e.g., '2025-26')
        split_type: 'overall', 'home', or 'away'
        conn: Optional database connection

    Returns:
        Dictionary of season-average opponent stats
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(NBA_DATA_DB_PATH)
        should_close = True

    cursor = conn.cursor()

    # Build WHERE clause for split type
    where_clause = "team_id = ? AND season = ?"
    params = [team_id, season]

    if split_type == 'home':
        where_clause += " AND is_home = 1"
    elif split_type == 'away':
        where_clause += " AND is_home = 0"

    # Aggregate opponent stats (what this team ALLOWED)
    cursor.execute(f'''
        SELECT
            COUNT(*) as games_played,
            AVG(opp_fgm) as opp_fgm,
            AVG(opp_fga) as opp_fga,
            AVG(opp_fg_pct) as opp_fg_pct,
            AVG(opp_fg2m) as opp_fg2m,
            AVG(opp_fg2a) as opp_fg2a,
            AVG(opp_fg2_pct) as opp_fg2_pct,
            AVG(opp_fg3m) as opp_fg3m,
            AVG(opp_fg3a) as opp_fg3a,
            AVG(opp_fg3_pct) as opp_fg3_pct,
            AVG(opp_ftm) as opp_ftm,
            AVG(opp_fta) as opp_fta,
            AVG(opp_ft_pct) as opp_ft_pct,
            AVG(opp_offensive_rebounds) as opp_offensive_rebounds,
            AVG(opp_defensive_rebounds) as opp_defensive_rebounds,
            AVG(opp_rebounds) as opp_rebounds,
            AVG(opp_assists) as opp_assists,
            AVG(opp_turnovers) as opp_turnovers,
            AVG(opp_steals) as opp_steals,
            AVG(opp_blocks) as opp_blocks,
            AVG(opp_pace) as opp_pace,
            AVG(opp_off_rating) as opp_off_rating,
            AVG(opp_def_rating) as opp_def_rating,
            AVG(opp_points_off_turnovers) as opp_points_off_turnovers,
            AVG(opp_fast_break_points) as opp_fast_break_points,
            AVG(opp_points_in_paint) as opp_points_in_paint,
            AVG(opp_second_chance_points) as opp_second_chance_points,
            AVG(possessions) as possessions,
            AVG(opp_possessions) as opp_possessions
        FROM team_game_logs
        WHERE {where_clause}
    ''', params)

    row = cursor.fetchone()

    if should_close:
        conn.close()

    if not row or row[0] == 0:
        return None

    return {
        'games_played': row[0],
        'opp_fgm': round(row[1], 1) if row[1] else None,
        'opp_fga': round(row[2], 1) if row[2] else None,
        'opp_fg_pct': round(row[3], 3) if row[3] else None,
        'opp_fg2m': round(row[4], 1) if row[4] else None,
        'opp_fg2a': round(row[5], 1) if row[5] else None,
        'opp_fg2_pct': round(row[6], 3) if row[6] else None,
        'opp_fg3m': round(row[7], 1) if row[7] else None,
        'opp_fg3a': round(row[8], 1) if row[8] else None,
        'opp_fg3_pct': round(row[9], 3) if row[9] else None,
        'opp_ftm': round(row[10], 1) if row[10] else None,
        'opp_fta': round(row[11], 1) if row[11] else None,
        'opp_ft_pct': round(row[12], 3) if row[12] else None,
        'opp_offensive_rebounds': round(row[13], 1) if row[13] else None,
        'opp_defensive_rebounds': round(row[14], 1) if row[14] else None,
        'opp_rebounds': round(row[15], 1) if row[15] else None,
        'opp_assists': round(row[16], 1) if row[16] else None,
        'opp_turnovers': round(row[17], 1) if row[17] else None,
        'opp_steals': round(row[18], 1) if row[18] else None,
        'opp_blocks': round(row[19], 1) if row[19] else None,
        'opp_pace': round(row[20], 1) if row[20] else None,
        'opp_off_rating': round(row[21], 1) if row[21] else None,
        'opp_def_rating': round(row[22], 1) if row[22] else None,
        'opp_points_off_turnovers': round(row[23], 1) if row[23] else None,
        'opp_fast_break_points': round(row[24], 1) if row[24] else None,
        'opp_points_in_paint': round(row[25], 1) if row[25] else None,
        'opp_second_chance_points': round(row[26], 1) if row[26] else None,
        'possessions': round(row[27], 1) if row[27] else None,
        'opp_possessions': round(row[28], 1) if row[28] else None,
    }


def update_team_season_opponent_stats(team_id: int, season: str, split_type: str = 'overall'):
    """
    Update team_season_stats with aggregated opponent stats.

    Callapproach after game logs are populated with opponent stats.
    """
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    # Get aggregated stats
    stats = aggregate_season_opponent_stats(team_id, season, split_type, conn)

    if not stats:
        print(f"No stats found for team {team_id}, season {season}, split {split_type}")
        conn.close()
        return

    # Update team_season_stats
    cursor.execute('''
        UPDATE team_season_stats
        SET
            opp_fgm = ?,
            opp_fga = ?,
            opp_fg_pct = ?,
            opp_fg2m = ?,
            opp_fg2a = ?,
            opp_fg2_pct = ?,
            opp_fg3m = ?,
            opp_fg3a = ?,
            opp_fg3_pct = ?,
            opp_ftm = ?,
            opp_fta = ?,
            opp_ft_pct = ?,
            opp_offensive_rebounds = ?,
            opp_defensive_rebounds = ?,
            opp_rebounds = ?,
            opp_assists = ?,
            opp_turnovers = ?,
            opp_steals = ?,
            opp_blocks = ?,
            opp_pace = ?,
            opp_off_rating = ?,
            opp_def_rating = ?,
            opp_points_off_turnovers = ?,
            opp_fast_break_points = ?,
            opp_points_in_paint = ?,
            opp_second_chance_points = ?,
            possessions = ?,
            opp_possessions = ?
        WHERE team_id = ? AND season = ? AND split_type = ?
    ''', (
        stats['opp_fgm'], stats['opp_fga'], stats['opp_fg_pct'],
        stats['opp_fg2m'], stats['opp_fg2a'], stats['opp_fg2_pct'],
        stats['opp_fg3m'], stats['opp_fg3a'], stats['opp_fg3_pct'],
        stats['opp_ftm'], stats['opp_fta'], stats['opp_ft_pct'],
        stats['opp_offensive_rebounds'], stats['opp_defensive_rebounds'], stats['opp_rebounds'],
        stats['opp_assists'], stats['opp_turnovers'], stats['opp_steals'], stats['opp_blocks'],
        stats['opp_pace'], stats['opp_off_rating'], stats['opp_def_rating'],
        stats['opp_points_off_turnovers'], stats['opp_fast_break_points'],
        stats['opp_points_in_paint'], stats['opp_second_chance_points'],
        stats['possessions'], stats['opp_possessions'],
        team_id, season, split_type
    ))

    conn.commit()
    conn.close()

    print(f"✓ Updated opponent stats for team {team_id}, {season}, {split_type}")


def backfill_all_season_opponent_stats(season: str = '2025-26'):
    """Backfill season opponent stats for all teams"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    # Get all teams with season stats
    cursor.execute('''
        SELECT DISTINCT team_id, split_type
        FROM team_season_stats
        WHERE season = ?
    ''', (season,))

    teams = cursor.fetchall()
    conn.close()

    print(f"Updating opponent stats for {len(teams)} team/split combinations...")

    for team_id, split_type in teams:
        update_team_season_opponent_stats(team_id, season, split_type)

    print("✅ All season opponent stats updated!")
```

**To execute:**
```bash
# After creating the file above:
python3 -c "from api.utils.season_opponent_stats_aggregator import backfill_all_season_opponent_stats; backfill_all_season_opponent_stats('2025-26')"
```

---

## Part 4: ETL Integration (sync_nba_data.py)

**Location:** `api/utils/sync_nba_data.py`

**Add these imports at top:**
```python
from api.utils.opponent_stats_calculator import compute_opponent_stats_for_game, compute_possessions
```

**After syncing game logs, add opponent stats computation:**

Find the section where game logs are inserted (search for `INSERT INTO team_game_logs`), and add AFTER the commit:

```python
# NEW: Compute opponent stats for this game
try:
    compute_opponent_stats_for_game(game_id, conn)
    logger.info(f"[OPPONENT STATS] Computed for game {game_id}")
except Exception as e:
    logger.error(f"[OPPONENT STATS] Error for game {game_id}: {e}")
```

**After syncing season stats, add opponent aggregation:**

Find where season stats are updated, add:

```python
# NEW: Aggregate opponent stats for season
try:
    from api.utils.season_opponent_stats_aggregator import update_team_season_opponent_stats
    update_team_season_opponent_stats(team_id, season, 'overall')
    update_team_season_opponent_stats(team_id, season, 'home')
    update_team_season_opponent_stats(team_id, season, 'away')
    logger.info(f"[OPP SEASON STATS] Updated for team {team_id}")
except Exception as e:
    logger.error(f"[OPP SEASON STATS] Error for team {team_id}: {e}")
```

---

## Part 5: Prediction Engine Integration

**Location:** `api/utils/prediction_engine.py` (or your main prediction file)

**Step 1: Load opponent stats in team profiles**

When building team profiles, add opponent stats:

```python
def get_team_opponent_stats(team_id: int, season: str = '2025-26') -> Dict:
    """Get opponent stats allowed by team (defensive metrics)"""
    conn = sqlite3.connect(NBA_DATA_DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            opp_fg_pct, opp_fg3_pct, opp_ft_pct,
            opp_rebounds, opp_assists, opp_turnovers,
            opp_pace, opp_off_rating, opp_def_rating,
            opp_points_in_paint, opp_fast_break_points,
            opp_ppg
        FROM team_season_stats
        WHERE team_id = ? AND season = ? AND split_type = 'overall'
    ''', (team_id, season))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}

    return {
        'opp_fg_pct_allowed': row[0],  # What % opponents shoot
        'opp_3p_pct_allowed': row[1],  # What % opponents shoot from 3
        'opp_ft_pct_allowed': row[2],
        'opp_reb_allowed': row[3],
        'opp_ast_allowed': row[4],
        'opp_tov_forced': row[5],  # Turnovers team forces
        'opp_pace_allowed': row[6],
        'opp_off_rtg_allowed': row[7],  # Opponent offensive rating allowed
        'opp_def_rtg_allowed': row[8],
        'opp_paint_pts_allowed': row[9],
        'opp_fastbreak_pts_allowed': row[10],
        'opp_ppg_allowed': row[11],
    }
```

**Step 2: Create matchup adjustment function**

```python
def compute_matchup_adjustment(
    team_offense: Dict,
    opponent_defense: Dict
) -> Dict:
    """
    Compare team's offensive stats to what opponent allows.

    Returns adjustments to apply to predicted scoring.
    """
    adjustments = {
        'fg_pct_adjustment': 0.0,
        '3p_pct_adjustment': 0.0,
        'pace_adjustment': 0.0,
        'paint_pts_adjustment': 0.0,
        'explanation': []
    }

    # Example: Team shoots 48% FG, opponent allows 46% FG
    # → Expect team to shoot better than average (+2%)
    if team_offense.get('fg_pct') and opponent_defense.get('opp_fg_pct_allowed'):
        team_fg = team_offense['fg_pct']
        opp_allows_fg = opponent_defense['opp_fg_pct_allowed']
        fg_advantage = team_fg - opp_allows_fg

        # Convert FG% advantage to points (rough: +1% FG = +2 points)
        adjustments['fg_pct_adjustment'] = fg_advantage * 2.0
        adjustments['explanation'].append(
            f"Team FG% {team_fg:.1%} vs Opp allows {opp_allows_fg:.1%} → {fg_advantage:+.1%} advantage"
        )

    # 3-point matchup
    if team_offense.get('fg3_pct') and opponent_defense.get('opp_3p_pct_allowed'):
        team_3p = team_offense['fg3_pct']
        opp_allows_3p = opponent_defense['opp_3p_pct_allowed']
        three_advantage = team_3p - opp_allows_3p

        # +1% 3P% ≈ +1.5 points (assuming ~40 3PA)
        adjustments['3p_pct_adjustment'] = three_advantage * 1.5
        adjustments['explanation'].append(
            f"Team 3P% {team_3p:.1%} vs Opp allows {opp_allows_3p:.1%} → {three_advantage:+.1%} advantage"
        )

    # Pace matchup
    if team_offense.get('pace') and opponent_defense.get('opp_pace_allowed'):
        team_pace = team_offense['pace']
        opp_allows_pace = opponent_defense['opp_pace_allowed']
        pace_diff = team_pace - opp_allows_pace

        # Higher pace = more possessions = more points
        # +1 possession ≈ +1 point
        adjustments['pace_adjustment'] = pace_diff * 0.5  # Blended impact
        adjustments['explanation'].append(
            f"Team pace {team_pace:.1f} vs Opp allows {opp_allows_pace:.1f} → {pace_diff:+.1f} diff"
        )

    return adjustments
```

**Step 3: Integrate into main prediction**

```python
# In your main prediction function, add:

# Load opponent stats
home_opp_stats = get_team_opponent_stats(home_team_id, season)
away_opp_stats = get_team_opponent_stats(away_team_id, season)

# Compute matchup adjustments
home_matchup_adj = compute_matchup_adjustment(home_offense, away_opp_stats)
away_matchup_adj = compute_matchup_adjustment(away_offense, home_opp_stats)

# Apply adjustments
home_predicted += home_matchup_adj['fg_pct_adjustment']
home_predicted += home_matchup_adj['3p_pct_adjustment']
home_predicted += home_matchup_adj['pace_adjustment']

away_predicted += away_matchup_adj['fg_pct_adjustment']
away_predicted += away_matchup_adj['3p_pct_adjustment']
away_predicted += away_matchup_adj['pace_adjustment']

# Log adjustments
logger.info(f"[MATCHUP] Home adjustments: {home_matchup_adj}")
logger.info(f"[MATCHUP] Away adjustments: {away_matchup_adj}")
```

---

## Part 6: AI Coach Enhancement

**Location:** `api/utils/openai_client.py`

**Add to system prompt (around line 544 after "Compare Actual Stats vs Expected Stats"):**

```python
## 2.2. Analyze Opponent Matchup Stats (Team vs Defense)

You will receive opponent statistics showing what each team ALLOWED their opponents to do this season.

**How to Use Opponent Stats:**

1. **Compare Team Offense to Opponent Defense Allowed:**
   - Example: "Miami shoots 37.5% from 3, but Oklahoma City allows only 34.2% from 3. This is a TOUGH matchup for Miami's 3-point shooting."
   - Example: "Phoenix averages 118 PPG, and Sacramento allows 115 PPG. Phoenix has an offensive advantage in this matchup."

2. **Compare Team Pace to Opponent Pace Allowed:**
   - Example: "Milwaukee plays at 102.5 pace, but Denver allows only 98.3 pace. Expect a slower game than Milwaukee prefers."

3. **Turnovers Forced vs Turnovers Committed:**
   - Example: "Phoenix forces 15.2 turnovers per game, but Oklahoma City only commits 12.8. Phoenix's pressure defense may not be as effective."

4. **Paint Points and Fastbreak Opportunities:**
   - Example: "The Knicks allow only 44 points in the paint per game, but tonight gave up 62. Their interior defense broke down."

**What to Include:**
- Identify where team strengths met opponent weaknesses (or vice versa)
- Explain which matchups favored which team
- Note when actual results differed from matchup expectations
- Quantify the impact: "This 3% shooting advantage typically adds 6-8 points"

**If opponent stats are missing:** Fall back to general team stats analysis.
```

**Add opponent stats to game_data payload:**

Around line 468-473 where you add `detailed_style_stats`, also add:

```python
# Add opponent matchup stats if available
if home_team_stats and away_team_stats:
    game_data["opponent_matchup_stats"] = {
        "home_offense_vs_away_defense": {
            "home_fg3_pct": home_team_stats.get('fg3_pct'),
            "away_allows_fg3_pct": away_team_stats.get('opp_fg3_pct'),
            "home_pace": home_team_stats.get('pace'),
            "away_allows_pace": away_team_stats.get('opp_pace'),
            "home_ppg": home_team_stats.get('ppg'),
            "away_allows_ppg": away_team_stats.get('opp_ppg'),
        },
        "away_offense_vs_home_defense": {
            "away_fg3_pct": away_team_stats.get('fg3_pct'),
            "home_allows_fg3_pct": home_team_stats.get('opp_fg3_pct'),
            "away_pace": away_team_stats.get('pace'),
            "home_allows_pace": home_team_stats.get('opp_pace'),
            "away_ppg": away_team_stats.get('ppg'),
            "home_allows_ppg": home_team_stats.get('opp_ppg'),
        }
    }
```

---

## Part 7: Validation Checklist

```bash
# 1. Verify opponent stats exist in database
sqlite3 api/data/nba_data.db "SELECT COUNT(*) FROM team_game_logs WHERE opp_fg3a IS NOT NULL;"
# Expected: 896 (all games)

# 2. Verify possessions calculated
sqlite3 api/data/nba_data.db "SELECT COUNT(*) FROM team_game_logs WHERE possessions IS NOT NULL;"
# Expected: 896

# 3. Sample opponent stats query
sqlite3 api/data/nba_data.db "
SELECT
    game_id,
    fg3a as team_3pa,
    opp_fg3a as opponent_3pa,
    fg3_pct as team_3p_pct,
    opp_fg3_pct as opponent_3p_pct
FROM team_game_logs
WHERE opp_fg3a IS NOT NULL
LIMIT 5;
"

# 4. Verify season aggregation
sqlite3 api/data/nba_data.db "
SELECT
    team_id,
    ppg as team_ppg,
    opp_ppg as opponent_ppg_allowed,
    fg3_pct as team_3p_pct,
    opp_fg3_pct as opponent_3p_allowed
FROM team_season_stats
WHERE season = '2025-26' AND split_type = 'overall'
LIMIT 5;
"

# 5. Test prediction with opponent stats
python3 -c "
from api.utils.prediction_engine import get_team_opponent_stats
stats = get_team_opponent_stats(1610612760, '2025-26')  # OKC
print('OKC Opponent Stats:', stats)
"

# 6. Verify ETL integration
# Run a sync and check logs for "[OPPONENT STATS]" messages

# 7. Test AI Coach with opponent stats
# Upload a game screenshot and verify AI review mentions opponent matchups
```

---

## Quick Start Commands

```bash
# 1. Run migrations (ALREADY DONE ✅)
python3 migrate_opponent_stats_schema.py

# 2. Backfill all games (ALREADY DONE ✅)
python3 -c "from api.utils.opponent_stats_calculator import backfill_all_opponent_stats; backfill_all_opponent_stats('2025-26')"

# 3. Aggregate season stats (TO DO)
python3 -c "from api.utils.season_opponent_stats_aggregator import backfill_all_season_opponent_stats; backfill_all_season_opponent_stats('2025-26')"

# 4. Test opponent stats
python3 -c "
import sqlite3
from api.utils.db_config import get_db_path
conn = sqlite3.connect(get_db_path('nba_data.db'))
cursor = conn.cursor()
cursor.execute('SELECT game_id, fg3a, opp_fg3a, possessions FROM team_game_logs WHERE opp_fg3a IS NOT NULL LIMIT 3')
for row in cursor.fetchall():
    print(f'Game: {row[0]}, Team 3PA: {row[1]}, Opp 3PA: {row[2]}, Possessions: {row[3]}')
conn.close()
"
```

---

## File Structure

```
api/utils/
├── opponent_stats_calculator.py          ✅ CREATED
├── season_opponent_stats_aggregator.py   📝 TO CREATE
├── db_config.py                          ✅ EXISTS
├── sync_nba_data.py                      🔄 TO MODIFY
└── prediction_engine.py                  🔄 TO MODIFY

migrate_opponent_stats_schema.py          ✅ CREATED
OPPONENT_STATS_IMPLEMENTATION_GUIDE.md    ✅ THIS FILE
```

---

## Expected Impact

### On Predictions:
- **More accurate baselines**: Team 3P% vs opponent 3P% defense
- **Better pace predictions**: Compare team pace to opponent pace allowed
- **Defensive adjustments**: Factor in what opponent typically allows
- **Matchup-specific scoring**: High-octane offense vs weak defense = higher total

### On AI Coach:
- **Richer explanations**: "Miami normally allows 34% from 3, but Orlando shot 40.5%"
- **Matchup analysis**: "Phoenix forces 15 turnovers but OKC only committed 8"
- **Possession context**: "Expected 102 possessions but only had 95"
- **Style clash insights**: "Fast-paced team vs slow-paced defense = tempo battle"

### On Frontend:
- New stat comparisons in prediction cards
- Opponent stats in team profiles
- Matchup advantage indicators
- Post-game opponent stat analysis

---

## Troubleshooting

**Issue: Opponent stats are NULL**
```bash
# Check if backfill ran
sqlite3 api/data/nba_data.db "SELECT COUNT(*) FROM team_game_logs WHERE opp_pts IS NOT NULL;"

# Re-run backfill if needed
python3 -c "from api.utils.opponent_stats_calculator import backfill_all_opponent_stats; backfill_all_opponent_stats()"
```

**Issue: Season stats not aggregating**
```bash
# Check if season aggregation module exists
ls api/utils/season_opponent_stats_aggregator.py

# Create it using code in Part 3 above
```

**Issue: Possessions formula seems wrong**
```bash
# Verify formula: FGA + 0.44*FTA - OREB + TOV
python3 -c "from api.utils.opponent_stats_calculator import compute_possessions; print(compute_possessions(85, 24, 10, 14))"
# Should return ~99.6
```

---

## Next Steps

1. ✅ **DONE**: Schema migration
2. ✅ **DONE**: Opponent stats computation module
3. ✅ **DONE**: Backfill all games
4. **TODO**: Create season aggregation module (Part 3)
5. **TODO**: Update ETL sync (Part 4)
6. **TODO**: Integrate into predictions (Part 5)
7. **TODO**: Enhance AI Coach (Part 6)
8. **TODO**: Run validation tests (Part 7)

---

## Success Metrics

- ✅ 100% of games have opponent stats
- ✅ Possessions calculated for all teams
- ⏳ Season averages computed for all teams
- ⏳ Predictions use opponent matchup data
- ⏳ AI Coach explains using opponent stats
- ⏳ No errors in ETL sync

**Current Progress: 60% Complete** 🎯
