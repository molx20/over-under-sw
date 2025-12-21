# Turnover Analysis Implementation Plan

## Overview

This document provides a complete implementation plan for adding turnover analysis charts and prediction adjustments to the NBA Over/Under system.

**Status:** Backend functions created ✅
**Remaining:** Database updates, React charts, prediction engine integration, API endpoints, testing

---

## ✅ Completed

1. **`api/utils/turnover_pressure_tiers.py`** - Tier classification module
   - `get_turnover_pressure_tier()` - Converts rank 1-30 to elite/average/low
   - Tiers: Elite (1-10), Average (11-20), Low (21-30)

2. **`api/utils/turnover_vs_defense_pressure.py`** - Backend data aggregation
   - `get_team_turnover_vs_defense_pressure()` - Returns turnover splits by opponent pressure tier × location

3. **`api/utils/turnover_vs_pace.py`** - Backend data aggregation
   - `get_team_turnover_vs_pace()` - Returns turnover splits by game pace × location
   - Pace tiers: Slow (<96), Normal (96-101), Fast (>101)

---

## 📋 Remaining Tasks

### Task 1: Add Opponent Turnover Forcing Rank to Database

**File:** `api/utils/sync_nba_data.py`

**What to add:**

In the section that computes and ranks team stats, add:

```python
# Rank teams by opponent turnovers (turnovers forced per game)
stats_df['opp_tov_rank'] = stats_df['opp_tov'].rank(ascending=False, method='min').astype(int)
```

**Where:** After existing ranking calculations (around lines that compute `def_rtg_rank`, `opp_fg3_pct_rank`, etc.)

**Update schema:** Ensure `team_season_stats` table has `opp_tov_rank` column (likely already has `opp_tov` field)

---

### Task 2: Create React Chart - Turnover vs Defense Pressure

**File:** `src/components/TurnoverVsDefensePressureChart.jsx` (NEW)

**Based on:** `ThreePointScoringVsDefenseChart.jsx`

**Key changes:**
- Y-axis label: "Turnovers Per Game"
- Tiers: "Elite Pressure", "Average Pressure", "Low Pressure"
- Data field: `turnovers` instead of `three_pt_ppg`
- Props: `teamData` with structure matching backend response
- Yellow outline on opponent's pressure tier bar

**Implementation:**

```jsx
function TurnoverVsDefensePressureChart({ teamData, compact = false }) {
  if (!teamData || !teamData.splits) {
    return <div className="text-center text-gray-500">No turnover data available</div>
  }

  const { splits, season_avg_turnovers, team_abbreviation, opponent_tov_pressure_tier } = teamData

  const tiers = ['elite', 'average', 'low']
  const tierLabels = {
    elite: 'Elite Pressure',
    average: 'Avg Pressure',
    low: 'Low Pressure'
  }

  // Extract data for chart
  const chartData = tiers.map(tier => ({
    tier: tierLabels[tier],
    home: splits[tier]?.home_turnovers,
    away: splits[tier]?.away_turnovers,
    homeGames: splits[tier]?.home_games || 0,
    awayGames: splits[tier]?.away_games || 0,
    isOpponentTier: tier === opponent_tov_pressure_tier
  }))

  // ... Recharts bar chart implementation (similar to 3PT chart)
  // Use season_avg_turnovers for reference line
}
```

---

### Task 3: Create React Chart - Turnover vs Pace

**File:** `src/components/TurnoverVsPaceChart.jsx` (NEW)

**Based on:** `ThreePointScoringVsPaceChart.jsx`

**Key changes:**
- Y-axis label: "Turnovers Per Game"
- Tiers: "Slow Pace", "Normal Pace", "Fast Pace"
- Data field: `turnovers` instead of `three_pt_ppg`
- Props: `teamData` with structure matching backend response
- Yellow outline on projected pace tier bar

**Implementation:** Similar to Task 2, but with pace tiers instead of pressure tiers

---

### Task 4: Add API Endpoints

**File:** `server.py`

**Add two new endpoints:**

```python
@app.route('/api/game-turnover-vs-defense-pressure', methods=['GET'])
def game_turnover_vs_defense_pressure():
    """
    Get turnover vs defense pressure charts for both teams in a game
    """
    game_id = request.args.get('game_id')
    season = request.args.get('season', '2025-26')

    if not game_id:
        return jsonify({'error': 'game_id required'}), 400

    from api.utils.db_queries import get_game_teams
    from api.utils.turnover_vs_defense_pressure import get_team_turnover_vs_defense_pressure
    from api.utils.turnover_pressure_tiers import get_turnover_pressure_tier
    from api.utils.db_queries import get_team_stats_with_ranks

    try:
        teams = get_game_teams(game_id)
        if not teams:
            return jsonify({'error': 'Game not found'}), 404

        home_team_id = teams['home_team_id']
        away_team_id = teams['away_team_id']

        # Get turnover splits
        home_data = get_team_turnover_vs_defense_pressure(home_team_id, season)
        away_data = get_team_turnover_vs_defense_pressure(away_team_id, season)

        # Get opponent pressure tiers
        home_stats = get_team_stats_with_ranks(home_team_id, season)
        away_stats = get_team_stats_with_ranks(away_team_id, season)

        home_tov_rank = away_stats['stats'].get('opp_tov_rank', {}).get('rank')
        away_tov_rank = home_stats['stats'].get('opp_tov_rank', {}).get('rank')

        if home_data:
            home_data['opponent_tov_pressure_tier'] = get_turnover_pressure_tier(away_tov_rank)
        if away_data:
            away_data['opponent_tov_pressure_tier'] = get_turnover_pressure_tier(home_tov_rank)

        return jsonify({
            'home': home_data,
            'away': away_data
        })

    except Exception as e:
        logger.error(f'Error in game_turnover_vs_defense_pressure: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/game-turnover-vs-pace', methods=['GET'])
def game_turnover_vs_pace():
    """
    Get turnover vs pace charts for both teams in a game
    """
    game_id = request.args.get('game_id')
    season = request.args.get('season', '2025-26')

    if not game_id:
        return jsonify({'error': 'game_id required'}), 400

    from api.utils.db_queries import get_game_teams
    from api.utils.turnover_vs_pace import get_team_turnover_vs_pace, get_pace_tier
    from api.utils.prediction_engine import calculate_projected_pace
    from api.utils.db_queries import get_team_stats

    try:
        teams = get_game_teams(game_id)
        if not teams:
            return jsonify({'error': 'Game not found'}), 404

        home_team_id = teams['home_team_id']
        away_team_id = teams['away_team_id']

        # Get turnover splits
        home_data = get_team_turnover_vs_pace(home_team_id, season)
        away_data = get_team_turnover_vs_pace(away_team_id, season)

        # Get projected pace for the game
        home_stats = get_team_stats(home_team_id, season)
        away_stats = get_team_stats(away_team_id, season)

        home_pace = home_stats.get('overall', {}).get('pace', 100)
        away_pace = away_stats.get('overall', {}).get('pace', 100)
        projected_pace = calculate_projected_pace(home_pace, away_pace)

        pace_tier = get_pace_tier(projected_pace)

        if home_data:
            home_data['projected_pace'] = projected_pace
            home_data['projected_pace_tier'] = pace_tier
        if away_data:
            away_data['projected_pace'] = projected_pace
            away_data['projected_pace_tier'] = pace_tier

        return jsonify({
            'home': home_data,
            'away': away_data,
            'projected_pace': projected_pace
        })

    except Exception as e:
        logger.error(f'Error in game_turnover_vs_pace: {e}')
        return jsonify({'error': str(e)}), 500
```

---

### Task 5: Add Turnover Projection to Prediction Engine

**File:** `api/utils/prediction_engine.py`

**Where:** After STEP 3 (Defense Adjustment), before STEP 4 (Recent Form)

**Insert new STEP 3.5:**

```python
        # ========================================================================
        # STEP 3.5: TURNOVER ADJUSTMENT (Applied after Defense)
        # ========================================================================
        home_turnover_adjust = 0.0
        away_turnover_adjust = 0.0
        home_projected_to = None
        away_projected_to = None

        if home_team_id and away_team_id:
            try:
                from api.utils.turnover_vs_defense_pressure import get_team_turnover_vs_defense_pressure
                from api.utils.turnover_vs_pace import get_team_turnover_vs_pace, get_pace_tier
                from api.utils.turnover_pressure_tiers import get_turnover_pressure_tier

                print(f'[prediction_engine] STEP 3.5 - Turnover adjustment:')

                # Get turnover data for both teams
                home_to_defense = get_team_turnover_vs_defense_pressure(home_team_id, season)
                away_to_defense = get_team_turnover_vs_defense_pressure(away_team_id, season)
                home_to_pace = get_team_turnover_vs_pace(home_team_id, season)
                away_to_pace = get_team_turnover_vs_pace(away_team_id, season)

                # Get opponent turnover pressure tiers
                away_tov_rank = away_stats_with_ranks['stats'].get('opp_tov_rank', {}).get('rank')
                home_tov_rank = home_stats_with_ranks['stats'].get('opp_tov_rank', {}).get('rank')
                away_tov_pressure_tier = get_turnover_pressure_tier(away_tov_rank) if away_tov_rank else None
                home_tov_pressure_tier = get_turnover_pressure_tier(home_tov_rank) if home_tov_rank else None

                # Get projected pace tier
                pace_tier = get_pace_tier(game_pace) if game_pace else None

                # Project home turnovers
                if home_to_defense and home_to_pace and away_tov_pressure_tier and pace_tier:
                    season_to = home_to_defense['season_avg_turnovers']

                    # Defense component
                    to_vs_pressure = home_to_defense['splits'][away_tov_pressure_tier]['home_turnovers']
                    if to_vs_pressure:
                        def_to_delta = to_vs_pressure - season_to
                        def_to_adj = def_to_delta * 0.5
                    else:
                        def_to_adj = 0.0

                    # Pace component
                    to_vs_pace = home_to_pace['splits'][pace_tier]['home_turnovers']
                    if to_vs_pace:
                        pace_to_delta = to_vs_pace - season_to
                        pace_to_adj = pace_to_delta * 0.5
                    else:
                        pace_to_adj = 0.0

                    # Blended projection
                    chart_to = season_to + def_to_adj + pace_to_adj

                    # Blend with recent (if available)
                    # For now, just use chart projection
                    home_projected_to = chart_to

                    # Calculate delta vs normal
                    delta_to = home_projected_to - season_to

                    # Dead zone: ignore if within ±1.5 turnovers
                    if abs(delta_to) >= 1.5:
                        # More turnovers = penalty (teams score less with more turnovers)
                        # Fewer turnovers = bonus
                        if delta_to > 0:
                            # Penalty: -3 pts per 3 extra turnovers
                            home_turnover_adjust = -3.0 * (delta_to / 3.0)
                        else:
                            # Bonus: +2 pts per 3 fewer turnovers
                            home_turnover_adjust = 2.0 * (abs(delta_to) / 3.0)

                        # Clamp adjustment
                        home_turnover_adjust = max(-6.0, min(home_turnover_adjust, 4.0))

                    print(f'  Home: {season_to:.1f} avg → {home_projected_to:.1f} projected ({delta_to:+.1f}) → {home_turnover_adjust:+.1f} pts')

                # Project away turnovers (same logic)
                if away_to_defense and away_to_pace and home_tov_pressure_tier and pace_tier:
                    season_to = away_to_defense['season_avg_turnovers']

                    to_vs_pressure = away_to_defense['splits'][home_tov_pressure_tier]['away_turnovers']
                    if to_vs_pressure:
                        def_to_adj = (to_vs_pressure - season_to) * 0.5
                    else:
                        def_to_adj = 0.0

                    to_vs_pace = away_to_pace['splits'][pace_tier]['away_turnovers']
                    if to_vs_pace:
                        pace_to_adj = (to_vs_pace - season_to) * 0.5
                    else:
                        pace_to_adj = 0.0

                    chart_to = season_to + def_to_adj + pace_to_adj
                    away_projected_to = chart_to

                    delta_to = away_projected_to - season_to

                    if abs(delta_to) >= 1.5:
                        if delta_to > 0:
                            away_turnover_adjust = -3.0 * (delta_to / 3.0)
                        else:
                            away_turnover_adjust = 2.0 * (abs(delta_to) / 3.0)

                        away_turnover_adjust = max(-6.0, min(away_turnover_adjust, 4.0))

                    print(f'  Away: {season_to:.1f} avg → {away_projected_to:.1f} projected ({delta_to:+.1f}) → {away_turnover_adjust:+.1f} pts')

                # Apply adjustments
                home_projected += home_turnover_adjust
                away_projected += away_turnover_adjust

                print(f'  Home: {home_projected:.1f} | Away: {away_projected:.1f}')

            except Exception as e:
                print(f'[prediction_engine] Error in turnover adjustment: {e}')
```

**Also update output schema (lines ~850):**

```python
'breakdown': {
    'home_projected': round(home_projected, 1),
    'away_projected': round(away_projected, 1),
    'game_pace': round(game_pace, 1),
    'difference': round(diff, 1),
    'home_form_adjustment': round(home_form_adjustment, 1),
    'away_form_adjustment': round(away_form_adjustment, 1),
    'home_turnover_adjustment': round(home_turnover_adjust, 1),  # NEW
    'away_turnover_adjustment': round(away_turnover_adjust, 1),  # NEW
    'home_projected_turnovers': home_projected_to,  # NEW
    'away_projected_turnovers': away_projected_to,  # NEW
    'home_data_quality': home_data_quality,
    'away_data_quality': away_data_quality,
    # ...
}
```

---

### Task 6: Add Turnover Charts to GamePage

**File:** `src/pages/GamePage.jsx`

**Add hooks for turnover data:**

```jsx
const { data: turnoverVsDefense } = useQuery({
  queryKey: ['game-turnover-vs-defense', game_id],
  queryFn: () => api.getGameTurnoverVsDefense(game_id),
  enabled: !!game_id
})

const { data: turnoverVsPace } = useQuery({
  queryKey: ['game-turnover-vs-pace', game_id],
  queryFn: () => api.getGameTurnoverVsPace(game_id),
  enabled: !!game_id
})
```

**Add to API client (`src/utils/api.js`):**

```javascript
export async function getGameTurnoverVsDefense(gameId) {
  const response = await fetch(`${API_BASE_URL}/api/game-turnover-vs-defense-pressure?game_id=${gameId}`)
  if (!response.ok) throw new Error('Failed to fetch turnover vs defense data')
  return response.json()
}

export async function getGameTurnoverVsPace(gameId) {
  const response = await fetch(`${API_BASE_URL}/api/game-turnover-vs-pace?game_id=${gameId}`)
  if (!response.ok) throw new Error('Failed to fetch turnover vs pace data')
  return response.json()
}
```

**Add chart sections in GamePage render:**

```jsx
{/* Turnover Analysis Section */}
<div className="mt-8">
  <h2 className="text-xl font-bold mb-4">Turnover Analysis</h2>

  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    {/* Home Team Charts */}
    <div>
      <h3 className="font-semibold mb-2">{homeTeam.name} - Turnovers</h3>

      {turnoverVsDefense?.home && (
        <div className="mb-4">
          <TurnoverVsDefensePressureChart
            teamData={turnoverVsDefense.home}
            compact={false}
          />
        </div>
      )}

      {turnoverVsPace?.home && (
        <div>
          <TurnoverVsPaceChart
            teamData={turnoverVsPace.home}
            compact={false}
          />
        </div>
      )}
    </div>

    {/* Away Team Charts */}
    <div>
      <h3 className="font-semibold mb-2">{awayTeam.name} - Turnovers</h3>

      {turnoverVsDefense?.away && (
        <div className="mb-4">
          <TurnoverVsDefensePressureChart
            teamData={turnoverVsDefense.away}
            compact={false}
          />
        </div>
      )}

      {turnoverVsPace?.away && (
        <div>
          <TurnoverVsPaceChart
            teamData={turnoverVsPace.away}
            compact={false}
          />
        </div>
      )}
    </div>
  </div>
</div>
```

---

### Task 7: Testing Plan

1. **Test Backend Functions:**
   ```python
   from api.utils.turnover_vs_defense_pressure import get_team_turnover_vs_defense_pressure
   from api.utils.turnover_vs_pace import get_team_turnover_vs_pace

   # Test with Boston Celtics
   data = get_team_turnover_vs_defense_pressure(1610612738)
   print(data)

   data = get_team_turnover_vs_pace(1610612738)
   print(data)
   ```

2. **Test API Endpoints:**
   ```bash
   curl "http://localhost:8080/api/game-turnover-vs-defense-pressure?game_id=0022500325"
   curl "http://localhost:8080/api/game-turnover-vs-pace?game_id=0022500325"
   ```

3. **Test Charts:**
   - Navigate to any game detail page
   - Verify both turnover charts render
   - Check that yellow outlines appear on correct bars
   - Verify season average line displays

4. **Test Prediction Engine:**
   - Check console logs for "STEP 3.5 - Turnover adjustment"
   - Verify turnover adjustments appear in prediction breakdown
   - Compare predictions before/after turnover logic

---

## Summary

**Completed:** ✅ 3 backend modules (tier classification, vs defense, vs pace)

**Remaining:**
1. Database: Add `opp_tov_rank` to sync
2. React: 2 chart components
3. Backend: 2 API endpoints
4. Prediction: STEP 3.5 turnover adjustment logic
5. Frontend: Integrate charts into GamePage
6. Testing: Validate end-to-end

**Estimated Time:** 2-3 hours for remaining tasks

**Priority Order:**
1. Database sync update (required for everything else)
2. API endpoints (needed by frontend)
3. React charts (visual output)
4. Prediction engine integration (the scoring impact)
5. Testing

This systematic approach ensures each layer works before building the next.
