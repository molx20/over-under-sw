# Similar Teams by Archetype - Implementation Plan

## Goal
Add "Similar Teams" display to Style Archetypes UI showing teams in the same archetype bucket (peer groups).

## Data Structure Analysis

### Current Archetype Data (per team):
```javascript
{
  season_offensive: { id, name, description, scoring_profile },
  season_defensive: { id, name, description, allows, suppresses },
  last10_offensive: { id, name, description, scoring_profile },
  last10_defensive: { id, name, description, allows, suppresses },
  style_shifts: { offensive, defensive, offensive_details, defensive_details }
}
```

### API Endpoint:
- `/api/team-archetypes?season=2025-26` - returns ALL teams
- `/api/team-archetypes?team_id=X&season=2025-26` - returns single team

## Implementation Steps

### 1. Create Archetype Index Builder
**File:** `src/utils/archetypeHelpers.js`

```javascript
/**
 * Build index of teams by archetype
 * Returns: { offensive: { archetypeId: [teamAbbrevs] }, defensive: { archetypeId: [teamAbbrevs] } }
 */
export function buildArchetypeTeamsIndex(allTeamsArchetypes) {
  const offensiveIndex = {}
  const defensiveIndex = {}

  Object.entries(allTeamsArchetypes).forEach(([teamId, data]) => {
    const teamAbbr = data.team_abbr

    // Season offensive
    const seasonOff = data.season_offensive.id
    if (!offensiveIndex[seasonOff]) offensiveIndex[seasonOff] = []
    offensiveIndex[seasonOff].push(teamAbbr)

    // Last 10 offensive (if different)
    const last10Off = data.last10_offensive.id
    if (last10Off !== seasonOff) {
      if (!offensiveIndex[last10Off]) offensiveIndex[last10Off] = []
      if (!offensiveIndex[last10Off].includes(teamAbbr)) {
        offensiveIndex[last10Off].push(teamAbbr)
      }
    }

    // Season defensive
    const seasonDef = data.season_defensive.id
    if (!defensiveIndex[seasonDef]) defensiveIndex[seasonDef] = []
    defensiveIndex[seasonDef].push(teamAbbr)

    // Last 10 defensive (if different)
    const last10Def = data.last10_defensive.id
    if (last10Def !== seasonDef) {
      if (!defensiveIndex[last10Def]) defensiveIndex[last10Def] = []
      if (!defensiveIndex[last10Def].includes(teamAbbr)) {
        defensiveIndex[last10Def].push(teamAbbr)
      }
    }
  })

  return { offensive: offensiveIndex, defensive: defensiveIndex }
}

/**
 * Get similar teams for an archetype
 * @param {string} archetypeType - 'offensive' or 'defensive'
 * @param {string} archetypeId - archetype ID
 * @param {string} excludeTeam - team abbreviation to exclude
 * @param {object} index - archetype teams index
 */
export function getSimilarTeams(archetypeType, archetypeId, excludeTeam, index) {
  const archIndex = archetypeType === 'offensive' ? index.offensive : index.defensive
  const teams = archIndex[archetypeId] || []

  return teams
    .filter(team => team !== excludeTeam)
    .sort() // Alphabetical for stable ordering
}
```

### 2. Create SimilarTeamsChips Component
**File:** `src/components/SimilarTeamsChips.jsx`

Features:
- Shows up to 6 team chips
- "View all (n)" button to expand/collapse
- Responsive layout
- Dark mode support

```javascript
import { useState } from 'react'

function SimilarTeamsChips({ teams, compact = false }) {
  const [showAll, setShowAll] = useState(false)

  if (!teams || teams.length === 0) return null

  const displayTeams = showAll ? teams : teams.slice(0, 6)
  const hasMore = teams.length > 6

  return (
    <div className={`mt-2 ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="flex items-center gap-1 mb-1">
        <span className="text-gray-500 dark:text-gray-400 font-medium">Similar teams:</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {displayTeams.map(team => (
          <span
            key={team}
            className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs font-medium"
          >
            {team}
          </span>
        ))}
        {hasMore && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="inline-flex items-center px-2 py-0.5 rounded bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-medium hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
          >
            {showAll ? 'Show less' : `View all (${teams.length})`}
          </button>
        )}
      </div>
    </div>
  )
}

export default SimilarTeamsChips
```

### 3. Update TeamArchetypes Component
**File:** `src/components/TeamArchetypes.jsx`

Changes:
1. Accept `allTeamsArchetypes` prop
2. Pass similar teams to ArchetypeBadge
3. Only show Last 10 similar teams if archetype shifted

```javascript
import { useMemo } from 'react'
import { buildArchetypeTeamsIndex, getSimilarTeams } from '../utils/archetypeHelpers'
import SimilarTeamsChips from './SimilarTeamsChips'

function TeamArchetypes({
  archetypes,
  teamName,
  allTeamsArchetypes, // NEW
  showComparison = true,
  compact = false
}) {
  // Build archetype index
  const archetypeIndex = useMemo(() => {
    if (!allTeamsArchetypes) return null
    return buildArchetypeTeamsIndex(allTeamsArchetypes)
  }, [allTeamsArchetypes])

  // Get similar teams helper
  const getSimilar = (type, archetypeId) => {
    if (!archetypeIndex) return []
    return getSimilarTeams(type, archetypeId, teamName, archetypeIndex)
  }

  // ... rest of component

  // In ArchetypeBadge calls, add similarTeams prop:
  <ArchetypeBadge
    archetype={season_offensive}
    label="Season"
    compact={compact}
    similarTeams={getSimilar('offensive', season_offensive.id)}
  />
}
```

### 4. Update ArchetypeBadge Component
Add `similarTeams` prop and render SimilarTeamsChips:

```javascript
function ArchetypeBadge({
  archetype,
  label,
  className = '',
  compact = false,
  similarTeams = [] // NEW
}) {
  return (
    <div className={className}>
      {/* Existing badge UI */}

      {/* Similar teams chips */}
      <SimilarTeamsChips teams={similarTeams} compact={compact} />
    </div>
  )
}
```

### 5. Update AdvancedSplitsPanel to Fetch All Teams
**File:** `src/components/AdvancedSplitsPanel.jsx`

```javascript
import { useTeamArchetypes } from '../utils/api'

function AdvancedSplitsPanel({ ... }) {
  // Fetch ALL teams' archetypes
  const { data: allTeamsArchetypes } = useTeamArchetypes(null, '2025-26')

  // Pass to TeamArchetypes
  <TeamArchetypes
    archetypes={homeArchetypes}
    teamName={scoringSplitsData?.home_team?.team_abbreviation}
    allTeamsArchetypes={allTeamsArchetypes}
    showComparison={true}
  />
}
```

## UI Behavior

### Season Archetypes (Always shown):
```
Offensive Style
  Season: Balanced High-Assist
    Ball-movement focused offense with balanced scoring sources...
    Similar teams: ATL, BOS, CHI, DEN, GSW, MIA [View all (12)]

Defensive Style
  Season: Perimeter Lockdown
    Elite perimeter defense that forces opponents inside...
    Similar teams: BOS, DAL, MIA, MIL, PHI, TOR [View all (9)]
```

### Last 10 Archetypes (Only if shifted):
```
  Last 10: Foul-Pressure Paint Attack
    Drives to the rim, draws fouls...
    Similar teams: ATL, CLE, LAL, MEM, PHX, SAC
    ⚠️ STYLE SHIFT: Balanced High-Assist → Foul-Pressure Paint Attack
```

## Testing Checklist

- [ ] Similar teams list excludes the team itself
- [ ] Alphabetical sorting is stable
- [ ] "View all" expands correctly
- [ ] Last 10 similar teams only show when archetype differs
- [ ] Dark mode styling works
- [ ] Responsive layout (mobile/desktop)
- [ ] Empty states handled gracefully

## Files Changed

### New Files:
1. `src/utils/archetypeHelpers.js` - Index builder and similar teams helper
2. `src/components/SimilarTeamsChips.jsx` - Similar teams chip list UI

### Modified Files:
1. `src/components/TeamArchetypes.jsx` - Add similar teams integration
2. `src/components/AdvancedSplitsPanel.jsx` - Fetch all teams' archetypes
3. `src/pages/GamePage.jsx` - Pass allTeamsArchetypes to AdvancedSplitsPanel

## Backend Changes
None required - `/api/team-archetypes` already supports fetching all teams.

## Performance Considerations
- `useTeamArchetypes(null)` called once per page load
- Cached for 1 hour via React Query
- Index building is memoized
- Minimal re-renders due to useMemo

## Accessibility
- Chip buttons have proper hover states
- Expand/collapse is keyboard accessible
- Semantic HTML structure
