/**
 * Archetype Helper Functions
 *
 * Utilities for building archetype team indexes and finding similar teams
 */

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
    const seasonOff = data.season_offensive?.id
    if (seasonOff) {
      if (!offensiveIndex[seasonOff]) offensiveIndex[seasonOff] = []
      offensiveIndex[seasonOff].push(teamAbbr)
    }

    // Last 10 offensive (if different)
    const last10Off = data.last10_offensive?.id
    if (last10Off && last10Off !== seasonOff) {
      if (!offensiveIndex[last10Off]) offensiveIndex[last10Off] = []
      if (!offensiveIndex[last10Off].includes(teamAbbr)) {
        offensiveIndex[last10Off].push(teamAbbr)
      }
    }

    // Season defensive
    const seasonDef = data.season_defensive?.id
    if (seasonDef) {
      if (!defensiveIndex[seasonDef]) defensiveIndex[seasonDef] = []
      defensiveIndex[seasonDef].push(teamAbbr)
    }

    // Last 10 defensive (if different)
    const last10Def = data.last10_defensive?.id
    if (last10Def && last10Def !== seasonDef) {
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
