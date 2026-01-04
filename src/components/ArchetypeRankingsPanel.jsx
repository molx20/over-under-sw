/**
 * ArchetypeRankingsPanel Component
 *
 * Displays ALL archetypes for a family with opponent archetype highlighting and ACTUAL STATS.
 * Shows offensive and defensive archetypes with real performance metrics (PPG, APG, etc.)
 */

import { useState } from 'react'
import GamesVsArchetypeModal from './GamesVsArchetypeModal'
import SimilarTeamsChips from './SimilarTeamsChips'

// Archetype definitions for each family
const ARCHETYPE_DEFINITIONS = {
  scoring: {
    offensive: {
      foul_pressure_paint_attack: { name: 'Foul Pressure Paint Attack', color: 'purple' },
      perimeter_spacing_offense: { name: 'Perimeter Spacing Offense', color: 'green' },
      balanced_high_assist: { name: 'Balanced High-Assist', color: 'blue' },
      second_chance_rebounders: { name: 'Second Chance Rebounders', color: 'orange' },
      iso_low_assist: { name: 'ISO Low-Assist', color: 'red' }
    },
    defensive: {
      foul_baiting_suppressor: { name: 'Foul-Baiting Suppressor', color: 'indigo' },
      perimeter_lockdown: { name: 'Perimeter Lockdown', color: 'teal' },
      paint_protection_elite: { name: 'Paint Protection Elite', color: 'cyan' },
      turnover_forcing_pressure: { name: 'Turnover Forcing Pressure', color: 'pink' },
      balanced_disciplined: { name: 'Balanced Disciplined', color: 'gray' }
    }
  },
  assists: {
    offensive: {
      ball_movement_maestro: { name: 'Ball Movement Maestro', color: 'purple' },
      high_volume_playmaking: { name: 'High Volume Playmaking', color: 'blue' },
      iso_driven_low_assist: { name: 'ISO Driven Low-Assist', color: 'red' },
      balanced_sharing: { name: 'Balanced Sharing', color: 'gray' }
    },
    defensive: {
      assist_denial_elite: { name: 'Assist Denial Elite', color: 'indigo' },
      rotation_scrambler: { name: 'Rotation Scrambler', color: 'teal' },
      ball_movement_vulnerable: { name: 'Ball Movement Vulnerable', color: 'orange' },
      average_assist_defense: { name: 'Average Assist Defense', color: 'gray' }
    }
  },
  rebounds: {
    offensive: {
      crash_the_glass_elite: { name: 'Crash the Glass Elite', color: 'purple' },
      selective_crasher: { name: 'Selective Crasher', color: 'blue' },
      transition_focused: { name: 'Transition Focused', color: 'green' },
      balanced_rebounding: { name: 'Balanced Rebounding', color: 'gray' }
    },
    defensive: {
      glass_protector_elite: { name: 'Glass Protector Elite', color: 'indigo' },
      solid_boxing_out: { name: 'Solid Boxing Out', color: 'teal' },
      vulnerable_to_crashes: { name: 'Vulnerable to Crashes', color: 'orange' },
      average_rebounding: { name: 'Average Rebounding', color: 'gray' }
    }
  },
  threes: {
    offensive: {
      volume_three_bomber: { name: 'Volume Three Bomber', color: 'purple' },
      efficient_selective_shooter: { name: 'Efficient Selective Shooter', color: 'blue' },
      three_avoidant: { name: 'Three Avoidant', color: 'orange' },
      balanced_shooting: { name: 'Balanced Shooting', color: 'gray' }
    },
    defensive: {
      three_point_shutdown: { name: 'Three-Point Shutdown', color: 'indigo' },
      perimeter_contest_strong: { name: 'Perimeter Contest Strong', color: 'teal' },
      three_point_vulnerable: { name: 'Three-Point Vulnerable', color: 'red' },
      average_perimeter_defense: { name: 'Average Perimeter Defense', color: 'gray' }
    }
  },
  turnovers: {
    offensive: {
      ball_security_elite: { name: 'Ball Security Elite', color: 'purple' },
      solid_ball_handler: { name: 'Solid Ball Handler', color: 'blue' },
      turnover_prone_aggressive: { name: 'Turnover Prone Aggressive', color: 'orange' },
      average_ball_security: { name: 'Average Ball Security', color: 'gray' }
    },
    defensive: {
      turnover_forcing_havoc: { name: 'Turnover Forcing Havoc', color: 'indigo' },
      pressure_defense: { name: 'Pressure Defense', color: 'teal' },
      passive_turnover_defense: { name: 'Passive Turnover Defense', color: 'green' },
      average_pressure: { name: 'Average Pressure', color: 'gray' }
    }
  }
}

/**
 * Helper function to find teams with matching archetypes
 */
function findSimilarTeams(allTeamsArchetypes, archetypeId, family, type, window, excludeTeamIds = []) {
  if (!allTeamsArchetypes) return []

  const similarTeams = []
  const windowKey = window === 'season' ? 'season' : 'last10'

  Object.entries(allTeamsArchetypes).forEach(([teamId, teamData]) => {
    // Skip excluded teams (e.g., the current team and their opponent)
    if (excludeTeamIds.includes(parseInt(teamId))) return

    let teamArchetypeId = null

    // Handle scoring family (legacy structure)
    if (family === 'scoring') {
      teamArchetypeId = teamData[`${windowKey}_${type}`]?.id
    } else {
      // Handle new families (nested structure)
      teamArchetypeId = teamData[family]?.[type]?.[window]?.id
    }

    // If this team has the same archetype, add them to the list
    if (teamArchetypeId === archetypeId) {
      similarTeams.push(teamData.team_abbr || 'Unknown')
    }
  })

  return similarTeams
}

/**
 * Extract stats from the splits data based on metric family
 * @param {boolean} isHomeTeam - Whether this team is playing at home (use _home stats) or away (use _away stats)
 */
function extractStats(statsData, family, context, window = 'season', isHomeTeam = true) {
  if (!statsData) {
    console.warn('[ArchetypeRankingsPanel] No stats data provided for family:', family)
    return null
  }

  const stats = {}

  // Log available fields for debugging
  console.log('[ArchetypeRankingsPanel] extractStats for', family, '- available fields:', Object.keys(statsData))

  if (family === 'scoring') {
    const locationSuffix = isHomeTeam ? '_home' : '_away'

    // OFFENSIVE: PPG scored by team (with home/away splits)
    if (window === 'last10') {
      stats.ppg = statsData[`last10_avg_ppg${locationSuffix}`]
               || statsData.last10_avg_ppg
               || statsData.overall_avg_points
               || statsData.season_avg_pts
               || 0
    } else {
      stats.ppg = statsData[`season_avg_ppg${locationSuffix}`]
               || statsData.overall_avg_points
               || statsData.season_avg_pts
               || statsData.avg_points
               || statsData.points
               || 0
    }

    // DEFENSIVE: PPG allowed (opponent points, with home/away splits)
    if (window === 'last10') {
      stats.ppg_def = statsData[`last10_avg_opp_ppg${locationSuffix}`]
                   || statsData.last10_avg_opp_ppg
                   || statsData.overall_avg_opp_points
                   || 0
    } else {
      stats.ppg_def = statsData[`season_avg_opp_ppg${locationSuffix}`]
                   || statsData.overall_avg_opp_points
                   || statsData.season_avg_opp_ppg
                   || statsData.season_avg_opp_pts
                   || 0
    }

    console.log('[ArchetypeRankingsPanel] Extracted PPG:', {
      isHomeTeam,
      offensive_ppg: stats.ppg,
      defensive_ppg: stats.ppg_def,
      window
    })

    if (stats.ppg === 0) {
      console.error('[ArchetypeRankingsPanel] PPG is 0! statsData:', statsData)
    }
  } else if (family === 'threes') {
    const locationSuffix = isHomeTeam ? '_home' : '_away'

    // OFFENSIVE: 3PT Makes with home/away splits
    if (window === 'last10') {
      stats.threesPG = statsData[`last10_avg_fg3m${locationSuffix}`]
                    || statsData.last10_avg_fg3m
                    || statsData.overall_avg_fg3m
                    || 0
    } else {
      stats.threesPG = statsData[`season_avg_fg3m${locationSuffix}`]
                    || statsData.overall_avg_fg3m
                    || statsData.season_avg_fg3m
                    || statsData.avg_fg3m
                    || 0
    }

    // OFFENSIVE: 3PT Percentage with home/away splits
    if (window === 'last10') {
      stats.threePct = statsData[`last10_avg_fg3_pct${locationSuffix}`]
                    || statsData.last10_avg_fg3_pct
                    || statsData.overall_avg_fg3_pct
                    || 0
    } else {
      stats.threePct = statsData[`season_avg_fg3_pct${locationSuffix}`]
                    || statsData.overall_avg_fg3_pct
                    || statsData.season_avg_fg3_pct
                    || statsData.avg_fg3_pct
                    || 0
    }

    // DEFENSIVE: Opponent 3PT Makes (3PM allowed)
    if (window === 'last10') {
      stats.threesPG_def = statsData[`last10_avg_opp_fg3m${locationSuffix}`]
                        || statsData.last10_avg_opp_fg3m
                        || statsData.overall_avg_opp_fg3m
                        || 0
    } else {
      stats.threesPG_def = statsData[`season_avg_opp_fg3m${locationSuffix}`]
                        || statsData.overall_avg_opp_fg3m
                        || statsData.season_avg_opp_fg3m
                        || 0
    }

    // DEFENSIVE: Opponent 3PT Percentage (3P% allowed)
    if (window === 'last10') {
      stats.threePct_def = statsData[`last10_avg_opp_fg3_pct${locationSuffix}`]
                        || statsData.last10_avg_opp_fg3_pct
                        || statsData.overall_avg_opp_fg3_pct
                        || 0
    } else {
      stats.threePct_def = statsData[`season_avg_opp_fg3_pct${locationSuffix}`]
                        || statsData.overall_avg_opp_fg3_pct
                        || statsData.season_avg_opp_fg3_pct
                        || 0
    }

    console.log('[ArchetypeRankingsPanel] Extracted 3PT defensive stats:', {
      isHomeTeam,
      locationSuffix,
      window,
      threesPG_def: stats.threesPG_def,
      threePct_def: stats.threePct_def,
      raw_season_avg_opp_fg3m: statsData.season_avg_opp_fg3m,
      raw_season_avg_opp_fg3m_home: statsData.season_avg_opp_fg3m_home,
      raw_season_avg_opp_fg3m_away: statsData.season_avg_opp_fg3m_away
    })
  } else if (family === 'turnovers') {
    const locationSuffix = isHomeTeam ? '_home' : '_away'

    // OFFENSIVE: Turnovers committed by the team (split by home/away)
    if (window === 'last10') {
      stats.tovPG = statsData[`last10_avg_turnovers${locationSuffix}`]
                 || statsData.last10_avg_turnovers
                 || statsData.last10_avg_tov
                 || 0
    } else {
      stats.tovPG = statsData[`season_avg_turnovers${locationSuffix}`]
                 || statsData.overall_avg_turnovers
                 || statsData.season_avg_turnovers
                 || statsData.season_avg_tov
                 || statsData.avg_turnovers
                 || 0
    }

    // DEFENSIVE: Turnovers forced (opponent turnovers, split by home/away)
    if (window === 'last10') {
      stats.tovPG_def = statsData[`last10_avg_opp_turnovers${locationSuffix}`]
                     || statsData.last10_avg_opp_turnovers
                     || statsData.last10_avg_opp_tov
                     || 0
    } else {
      stats.tovPG_def = statsData[`season_avg_opp_turnovers${locationSuffix}`]
                     || statsData.overall_avg_opp_turnovers
                     || statsData.season_avg_opp_turnovers
                     || statsData.season_avg_opp_tov
                     || 0
    }

    console.log('[ArchetypeRankingsPanel] Extracted turnovers:', {
      isHomeTeam,
      offensive_tovPG: stats.tovPG,
      defensive_tovPG: stats.tovPG_def,
      window
    })
  } else if (family === 'assists') {
    const locationSuffix = isHomeTeam ? '_home' : '_away'

    // OFFENSIVE: Assists with home/away splits
    if (window === 'last10') {
      stats.apg = statsData[`last10_avg_ast${locationSuffix}`]
               || statsData.last10_avg_ast
               || statsData.overall_avg_assists
               || 0
    } else {
      stats.apg = statsData[`season_avg_ast${locationSuffix}`]
               || statsData.overall_avg_assists
               || statsData.season_avg_ast
               || statsData.avg_assists
               || 0
    }

    // DEFENSIVE: Opponent Assists (assists allowed)
    if (window === 'last10') {
      stats.apg_def = statsData[`last10_avg_opp_ast${locationSuffix}`]
                   || statsData.last10_avg_opp_ast
                   || statsData.overall_avg_opp_assists
                   || 0
    } else {
      stats.apg_def = statsData[`season_avg_opp_ast${locationSuffix}`]
                   || statsData.overall_avg_opp_assists
                   || statsData.season_avg_opp_ast
                   || 0
    }

    console.log('[ArchetypeRankingsPanel] Extracted assists defensive stats:', {
      isHomeTeam,
      locationSuffix,
      window,
      apg_def: stats.apg_def,
      raw_season_avg_opp_ast: statsData.season_avg_opp_ast,
      raw_season_avg_opp_ast_home: statsData.season_avg_opp_ast_home,
      raw_season_avg_opp_ast_away: statsData.season_avg_opp_ast_away
    })
  } else if (family === 'rebounds') {
    const locationSuffix = isHomeTeam ? '_home' : '_away'

    // OFFENSIVE: Team Offensive Rebounds with home/away splits
    if (window === 'last10') {
      stats.orpg = statsData[`last10_avg_oreb${locationSuffix}`]
                || statsData.last10_avg_oreb
                || statsData.overall_avg_offensive_rebounds
                || 0
    } else {
      stats.orpg = statsData[`season_avg_oreb${locationSuffix}`]
                || statsData.overall_avg_offensive_rebounds
                || statsData.season_avg_oreb
                || statsData.avg_offensive_rebounds
                || 0
    }

    // OFFENSIVE: Team Defensive Rebounds with home/away splits
    if (window === 'last10') {
      stats.drpg = statsData[`last10_avg_dreb${locationSuffix}`]
                || statsData.last10_avg_dreb
                || statsData.overall_avg_defensive_rebounds
                || 0
    } else {
      stats.drpg = statsData[`season_avg_dreb${locationSuffix}`]
                || statsData.overall_avg_defensive_rebounds
                || statsData.season_avg_dreb
                || statsData.avg_defensive_rebounds
                || 0
    }

    // Total Rebounds (for reference, though not typically shown separately)
    stats.rpg = statsData.overall_avg_rebounds
             || statsData.season_avg_reb
             || statsData.avg_rebounds
             || 0

    // DEFENSIVE: Opponent Offensive Rebounds (offensive rebounds allowed)
    if (window === 'last10') {
      stats.orpg_def = statsData[`last10_avg_opp_oreb${locationSuffix}`]
                    || statsData.last10_avg_opp_oreb
                    || statsData.overall_avg_opp_offensive_rebounds
                    || 0
    } else {
      stats.orpg_def = statsData[`season_avg_opp_oreb${locationSuffix}`]
                    || statsData.overall_avg_opp_offensive_rebounds
                    || statsData.season_avg_opp_oreb
                    || 0
    }

    // DEFENSIVE: Opponent Defensive Rebounds (defensive rebounds allowed)
    if (window === 'last10') {
      stats.drpg_def = statsData[`last10_avg_opp_dreb${locationSuffix}`]
                    || statsData.last10_avg_opp_dreb
                    || statsData.overall_avg_opp_defensive_rebounds
                    || 0
    } else {
      stats.drpg_def = statsData[`season_avg_opp_dreb${locationSuffix}`]
                    || statsData.overall_avg_opp_defensive_rebounds
                    || statsData.season_avg_opp_dreb
                    || 0
    }

    console.log('[ArchetypeRankingsPanel] Extracted rebounds:', { orpg: stats.orpg, drpg: stats.drpg, rpg: stats.rpg, orpg_def: stats.orpg_def, drpg_def: stats.drpg_def })
  }

  return stats
}

/**
 * Main component that renders offensive and defensive archetype grids
 */
function ArchetypeRankingsPanel({
  family,
  homeArchetypes,
  awayArchetypes,
  allTeamsArchetypes,
  window,
  homeStats,
  awayStats,
  context,
  homeTeam,
  awayTeam,
  gameId
}) {
  // SAFE MODE ADDITION: State for archetype match games (click-to-view feature)
  const [selectedArchetype, setSelectedArchetype] = useState(null) // { team: 'home'|'away', side: 'offensive'|'defensive', label: str }
  const [archetypeGames, setArchetypeGames] = useState([])
  const [archetypeGamesLoading, setArchetypeGamesLoading] = useState(false)

  // SAFE MODE ADDITION: Fetch games where team played against opponents with specific archetype
  const fetchArchetypeMatchGames = async (clickedTeam, clickedSide, archetypeLabel) => {
    if (!homeTeam || !awayTeam) {
      console.warn('[ArchetypeRankingsPanel] Missing team data, cannot fetch games')
      return
    }

    // Determine which team's games to fetch (the CLICKED team, not the opponent)
    const targetTeam = clickedTeam === 'home' ? homeTeam : awayTeam
    const targetRole = clickedTeam === 'home' ? 'home' : 'away' // Clicked team's role in THIS game

    console.log(`[ArchetypeRankingsPanel] Clicked ${clickedTeam} team's ${clickedSide} archetype`)
    console.log(`[ArchetypeRankingsPanel] Fetching ${targetTeam.abbreviation}'s ${targetRole} games vs opponents with ${archetypeLabel}`)

    setSelectedArchetype({ team: clickedTeam, side: clickedSide, label: archetypeLabel })
    setArchetypeGamesLoading(true)

    try {
      const params = new URLSearchParams({
        team_id: targetTeam.id,
        category: family === 'scoring' ? 'scoring' : family,
        side: clickedSide,
        label: archetypeLabel,
        window: window,
        role: targetRole,
        season: '2025-26'
      })

      const response = await fetch(`/api/archetype_match_games?${params}`)
      const data = await response.json()

      if (data.success) {
        console.log(`[ArchetypeRankingsPanel] Found ${data.games_count} matching games`)
        setArchetypeGames(data.games || [])
      } else {
        console.error('[ArchetypeRankingsPanel] API error:', data.error)
        setArchetypeGames([])
      }
    } catch (error) {
      console.error('[ArchetypeRankingsPanel] Fetch error:', error)
      setArchetypeGames([])
    } finally {
      setArchetypeGamesLoading(false)
    }
  }

  // Handle missing data
  if (!homeArchetypes || !awayArchetypes || !family) {
    return (
      <div className="p-8 text-center text-gray-500 dark:text-gray-400">
        <p>Archetype data not available. Rebuild Docker container with scipy dependency.</p>
      </div>
    )
  }

  // Extract family-specific data
  let homeFamilyData, awayFamilyData

  // For scoring family, use the legacy structure
  if (family === 'scoring') {
    const windowKey = window === 'season' ? 'season' : 'last10'
    homeFamilyData = {
      offensive: {
        [window]: {
          ...homeArchetypes[`${windowKey}_offensive`],
          percentile: homeArchetypes[`${windowKey}_offensive_percentile`] || 50
        }
      },
      defensive: {
        [window]: {
          ...homeArchetypes[`${windowKey}_defensive`],
          percentile: homeArchetypes[`${windowKey}_defensive_percentile`] || 50
        }
      }
    }
    awayFamilyData = {
      offensive: {
        [window]: {
          ...awayArchetypes[`${windowKey}_offensive`],
          percentile: awayArchetypes[`${windowKey}_offensive_percentile`] || 50
        }
      },
      defensive: {
        [window]: {
          ...awayArchetypes[`${windowKey}_defensive`],
          percentile: awayArchetypes[`${windowKey}_defensive_percentile`] || 50
        }
      }
    }
  } else {
    // For new families, use the nested structure
    homeFamilyData = homeArchetypes[family]
    awayFamilyData = awayArchetypes[family]
  }

  // Validate family data exists
  if (!homeFamilyData || !awayFamilyData) {
    return (
      <div className="p-8 text-center text-gray-500 dark:text-gray-400">
        <p>No {family} archetype data available. Rebuild Docker container with scipy.</p>
      </div>
    )
  }

  // Extract actual stats (pass window to get correct season/last10 values)
  // Pass isHomeTeam parameter to get home/away location-specific stats
  const homeStatValues = extractStats(homeStats, family, context, window, true)
  const awayStatValues = extractStats(awayStats, family, context, window, false)

  return (
    <div className="space-y-8">
      {/* Offensive Section */}
      <ArchetypeGrid
        type="offensive"
        family={family}
        homeData={homeFamilyData?.offensive?.[window]}
        awayData={awayFamilyData?.offensive?.[window]}
        homeTeam={homeTeam?.name || homeTeam?.abbreviation || 'Home'}
        awayTeam={awayTeam?.name || awayTeam?.abbreviation || 'Away'}
        homeStats={homeStatValues}
        awayStats={awayStatValues}
        window={window}
        onArchetypeClick={fetchArchetypeMatchGames}
        allTeamsArchetypes={allTeamsArchetypes}
        homeTeamId={homeTeam?.team_id}
        awayTeamId={awayTeam?.team_id}
      />

      {/* Defensive Section */}
      <ArchetypeGrid
        type="defensive"
        family={family}
        homeData={homeFamilyData?.defensive?.[window]}
        awayData={awayFamilyData?.defensive?.[window]}
        homeTeam={homeTeam?.name || homeTeam?.abbreviation || 'Home'}
        awayTeam={awayTeam?.name || awayTeam?.abbreviation || 'Away'}
        homeStats={homeStatValues}
        awayStats={awayStatValues}
        window={window}
        onArchetypeClick={fetchArchetypeMatchGames}
        allTeamsArchetypes={allTeamsArchetypes}
        homeTeamId={homeTeam?.team_id}
        awayTeamId={awayTeam?.team_id}
      />

      {/* SAFE MODE ADDITION: Games vs This Archetype Modal (popup instead of inline) */}
      <GamesVsArchetypeModal
        isOpen={!!selectedArchetype}
        onClose={() => {
          setSelectedArchetype(null)
          setArchetypeGames([])
        }}
        archetype={
          selectedArchetype
            ? {
                name: ARCHETYPE_DEFINITIONS[family]?.[selectedArchetype.side]?.[selectedArchetype.label]?.name || selectedArchetype.label,
                id: selectedArchetype.label
              }
            : null
        }
        archetypeType={selectedArchetype?.side}
        window={window}
        targetTeamAbbr={
          selectedArchetype
            ? (selectedArchetype.team === 'home' ? awayTeam?.abbreviation : homeTeam?.abbreviation)
            : null
        }
        selectedTeamAbbr={
          selectedArchetype
            ? (selectedArchetype.team === 'home' ? homeTeam?.abbreviation : awayTeam?.abbreviation)
            : null
        }
        games={archetypeGames}
        summary={{
          games_count: archetypeGames.length,
          ppg: archetypeGames.length > 0 ? archetypeGames.reduce((sum, g) => sum + (g.team_pts || 0), 0) / archetypeGames.length : 0,
          efg: archetypeGames.length > 0 ? archetypeGames.reduce((sum, g) => sum + (g.efg_pct || 0), 0) / archetypeGames.length : 0,
          ft_points: archetypeGames.length > 0 ? archetypeGames.reduce((sum, g) => sum + (g.ft_points || 0), 0) / archetypeGames.length : 0,
          paint_points: archetypeGames.length > 0 ? archetypeGames.reduce((sum, g) => sum + (g.paint_points || 0), 0) / archetypeGames.length : 0,
          wins: archetypeGames.filter(g => g.wl === 'W').length,
          win_pct: archetypeGames.length > 0 ? (archetypeGames.filter(g => g.wl === 'W').length / archetypeGames.length) * 100 : 0
        }}
        isLoading={archetypeGamesLoading}
      />
    </div>
  )
}

/**
 * ArchetypeGrid - Shows all 4 archetypes with opponent highlighting
 */
function ArchetypeGrid({ type, family, homeData, awayData, homeTeam, awayTeam, homeStats, awayStats, window, onArchetypeClick, allTeamsArchetypes, homeTeamId, awayTeamId }) {
  if (!homeData || !awayData) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
        <p>No {type} archetype data available</p>
      </div>
    )
  }

  const isOffensive = type === 'offensive'
  const titleColor = isOffensive
    ? 'text-blue-600 dark:text-blue-400'
    : 'text-red-600 dark:text-red-400'

  // Get archetype definitions for this family/type
  const archetypeDefs = ARCHETYPE_DEFINITIONS[family]?.[type] || {}
  const archetypeList = Object.keys(archetypeDefs)

  // Get current archetypes
  const homeArchetypeId = homeData?.id
  const awayArchetypeId = awayData?.id

  // Calculate similar teams for each archetype (exclude current home and away teams)
  const excludeTeamIds = [homeTeamId, awayTeamId].filter(Boolean)

  return (
    <div className="relative">
      {/* Section Header */}
      <div className="mb-4">
        <h3 className={`text-lg font-semibold ${titleColor}`}>
          {isOffensive ? 'Offensive' : 'Defensive'} {getFamilyDisplayName(family)} Archetypes
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Yellow border indicates opponent's archetype
        </p>
      </div>

      {/* Two-column grid: Home vs Away */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Away Team Column */}
        <div>
          <h4 className="text-sm font-semibold text-orange-700 dark:text-orange-300 mb-3">
            {awayTeam}
          </h4>
          <div className="space-y-2">
            {archetypeList.map(archetypeId => {
              const isCurrentArchetype = archetypeId === awayArchetypeId
              const isOpponentArchetype = archetypeId === homeArchetypeId
              const archetypeDef = archetypeDefs[archetypeId]

              // Find similar teams for this archetype
              const similarTeams = isCurrentArchetype
                ? findSimilarTeams(allTeamsArchetypes, archetypeId, family, type, window, excludeTeamIds)
                : []

              return (
                <ArchetypeCard
                  key={archetypeId}
                  archetypeId={archetypeId}
                  name={archetypeDef.name}
                  isCurrent={isCurrentArchetype}
                  isOpponent={isOpponentArchetype}
                  stats={isCurrentArchetype ? awayStats : null}
                  family={family}
                  teamColor="orange"
                  onClick={isOpponentArchetype ? () => onArchetypeClick?.('away', type, archetypeId) : null}
                  type={type}
                  similarTeams={similarTeams}
                />
              )
            })}
          </div>
        </div>

        {/* Home Team Column */}
        <div>
          <h4 className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-3">
            {homeTeam}
          </h4>
          <div className="space-y-2">
            {archetypeList.map(archetypeId => {
              const isCurrentArchetype = archetypeId === homeArchetypeId
              const isOpponentArchetype = archetypeId === awayArchetypeId
              const archetypeDef = archetypeDefs[archetypeId]

              // Find similar teams for this archetype
              const similarTeams = isCurrentArchetype
                ? findSimilarTeams(allTeamsArchetypes, archetypeId, family, type, window, excludeTeamIds)
                : []

              return (
                <ArchetypeCard
                  key={archetypeId}
                  archetypeId={archetypeId}
                  name={archetypeDef.name}
                  isCurrent={isCurrentArchetype}
                  isOpponent={isOpponentArchetype}
                  stats={isCurrentArchetype ? homeStats : null}
                  family={family}
                  teamColor="blue"
                  onClick={isOpponentArchetype ? () => onArchetypeClick?.('home', type, archetypeId) : null}
                  type={type}
                  similarTeams={similarTeams}
                />
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * ArchetypeCard - Individual archetype card with highlighting and ACTUAL STATS
 */
function ArchetypeCard({ archetypeId, name, isCurrent, isOpponent, stats, family, teamColor, onClick, type, similarTeams = [] }) {
  const getCardClasses = () => {
    let classes = 'p-3 rounded-lg border-2 transition-all '

    // SAFE MODE ADDITION: Add cursor-pointer and hover effect for clickable opponent archetypes
    if (onClick) {
      classes += 'cursor-pointer hover:shadow-lg '
    }

    if (isCurrent && isOpponent) {
      // Both teams have this archetype - purple highlight
      classes += 'bg-purple-50 dark:bg-purple-900/20 border-purple-500 dark:border-purple-400 shadow-lg'
    } else if (isCurrent) {
      // Current team's archetype - bold border with team color
      if (teamColor === 'blue') {
        classes += 'bg-blue-50 dark:bg-blue-900/20 border-blue-600 dark:border-blue-400 shadow-md'
      } else {
        classes += 'bg-orange-50 dark:bg-orange-900/20 border-orange-600 dark:border-orange-400 shadow-md'
      }
    } else if (isOpponent) {
      // Opponent's archetype - yellow warning border (CLICKABLE if onClick provided)
      classes += 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500 dark:border-yellow-400 shadow-md'
    } else {
      // Inactive archetype - gray
      classes += 'bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 opacity-60'
    }

    return classes
  }

  // Get stat display based on family and type (offensive vs defensive)
  const getStatDisplay = (stats, family, type) => {
    if (!stats) return null

    if (family === 'scoring') {
      // OFFENSIVE: Points scored | DEFENSIVE: Points allowed
      const ppgValue = type === 'defensive' ? stats.ppg_def : stats.ppg
      return `${ppgValue.toFixed(1)} PPG`
    } else if (family === 'threes') {
      // OFFENSIVE: 3PM made | DEFENSIVE: 3PM allowed
      const threesPGValue = type === 'defensive' ? stats.threesPG_def : stats.threesPG
      const threePctValue = type === 'defensive' ? stats.threePct_def : stats.threePct
      return `${threesPGValue.toFixed(1)} 3PM | ${threePctValue.toFixed(1)}%`
    } else if (family === 'turnovers') {
      // OFFENSIVE: Turnovers committed | DEFENSIVE: Turnovers forced
      const tovValue = type === 'defensive' ? stats.tovPG_def : stats.tovPG
      return `${tovValue.toFixed(1)} TOV/G`
    } else if (family === 'assists') {
      // OFFENSIVE: Assists made | DEFENSIVE: Assists allowed
      const apgValue = type === 'defensive' ? stats.apg_def : stats.apg
      return `${apgValue.toFixed(1)} APG`
    } else if (family === 'rebounds') {
      // OFFENSIVE: Rebounds grabbed | DEFENSIVE: Rebounds allowed
      const orpgValue = type === 'defensive' ? stats.orpg_def : stats.orpg
      const drpgValue = type === 'defensive' ? stats.drpg_def : stats.drpg
      const rpgValue = orpgValue + drpgValue
      return `${rpgValue.toFixed(1)} RPG (${orpgValue.toFixed(1)} O / ${drpgValue.toFixed(1)} D)`
    }

    return null
  }

  const statDisplay = getStatDisplay(stats, family, type)

  return (
    <div className={getCardClasses()} onClick={onClick}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${isCurrent || isOpponent ? 'text-gray-900 dark:text-gray-100' : 'text-gray-600 dark:text-gray-400'}`}>
              {name}
            </span>
            {isOpponent && !isCurrent && (
              <span className="text-xs px-2 py-0.5 bg-yellow-200 dark:bg-yellow-700 text-yellow-900 dark:text-yellow-100 rounded-full font-medium">
                OPP
              </span>
            )}
            {isCurrent && isOpponent && (
              <span className="text-xs px-2 py-0.5 bg-purple-200 dark:bg-purple-700 text-purple-900 dark:text-purple-100 rounded-full font-medium">
                BOTH
              </span>
            )}
          </div>

          {isCurrent && statDisplay && (
            <div className="mt-2">
              <span className={`text-lg font-bold ${teamColor === 'blue' ? 'text-blue-700 dark:text-blue-300' : 'text-orange-700 dark:text-orange-300'}`}>
                {statDisplay}
              </span>
            </div>
          )}

          {isCurrent && similarTeams.length > 0 && (
            <SimilarTeamsChips teams={similarTeams} compact={true} />
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Helper function to get display name for archetype family
 */
function getFamilyDisplayName(family) {
  const displayNames = {
    scoring: 'Scoring',
    assists: 'Assists',
    rebounds: 'Rebounding',
    threes: 'Three-Point',
    turnovers: 'Turnover'
  }
  return displayNames[family] || family
}

export default ArchetypeRankingsPanel
