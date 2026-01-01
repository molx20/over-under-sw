/**
 * ArchetypeRankingsPanel Component
 *
 * Displays ALL archetypes for a family with opponent archetype highlighting and ACTUAL STATS.
 * Shows offensive and defensive archetypes with real performance metrics (PPG, APG, etc.)
 */

import { useState } from 'react'

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
 * Extract stats from the splits data based on metric family
 */
function extractStats(statsData, family, context) {
  if (!statsData) {
    console.warn('[ArchetypeRankingsPanel] No stats data provided for family:', family)
    return null
  }

  const stats = {}

  // Log available fields for debugging
  console.log('[ArchetypeRankingsPanel] extractStats for', family, '- available fields:', Object.keys(statsData))

  if (family === 'scoring') {
    // Try multiple field names for PPG (different APIs may use different names)
    stats.ppg = statsData.overall_avg_points
             || statsData.season_avg_pts
             || statsData.avg_points
             || statsData.points
             || 0

    console.log('[ArchetypeRankingsPanel] Extracted PPG:', stats.ppg, 'from statsData')

    if (stats.ppg === 0) {
      console.error('[ArchetypeRankingsPanel] PPG is 0! statsData:', statsData)
    }
  } else if (family === 'threes') {
    stats.threesPG = statsData.overall_avg_fg3m
                  || statsData.season_avg_fg3m
                  || statsData.avg_fg3m
                  || 0
    stats.threePct = statsData.overall_avg_fg3_pct
                  || statsData.season_avg_fg3_pct
                  || statsData.avg_fg3_pct
                  || 0
  } else if (family === 'turnovers') {
    stats.tovPG = statsData.overall_avg_turnovers
               || statsData.season_avg_tov
               || statsData.avg_turnovers
               || 0
  } else if (family === 'assists') {
    stats.apg = statsData.overall_avg_assists
             || statsData.season_avg_ast
             || statsData.avg_assists
             || 0
  } else if (family === 'rebounds') {
    stats.orpg = statsData.overall_avg_offensive_rebounds
              || statsData.season_avg_oreb
              || statsData.avg_offensive_rebounds
              || 0
    stats.drpg = statsData.overall_avg_defensive_rebounds
              || statsData.season_avg_dreb
              || statsData.avg_defensive_rebounds
              || 0
    stats.rpg = statsData.overall_avg_rebounds
             || statsData.season_avg_reb
             || statsData.avg_rebounds
             || 0

    console.log('[ArchetypeRankingsPanel] Extracted rebounds:', { orpg: stats.orpg, drpg: stats.drpg, rpg: stats.rpg })
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

    // Determine which team's games to fetch (the OPPONENT of the clicked archetype)
    const targetTeam = clickedTeam === 'home' ? awayTeam : homeTeam
    const targetRole = clickedTeam === 'home' ? 'away' : 'home' // Opponent's role in THIS game

    console.log(`[ArchetypeRankingsPanel] Clicked ${clickedTeam} team's ${clickedSide} archetype`)
    console.log(`[ArchetypeRankingsPanel] Fetching ${targetTeam.abbreviation}'s ${targetRole} games vs archetype ${archetypeLabel}`)

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

      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001'
      const response = await fetch(`${baseUrl}/api/archetype_match_games?${params}`)
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

  // Extract actual stats
  const homeStatValues = extractStats(homeStats, family, context)
  const awayStatValues = extractStats(awayStats, family, context)

  return (
    <div className="space-y-8">
      {/* Offensive Section */}
      <ArchetypeGrid
        type="offensive"
        family={family}
        homeData={homeFamilyData?.offensive?.[window]}
        awayData={awayFamilyData?.offensive?.[window]}
        homeTeam={homeArchetypes?.team_abbr || 'Home'}
        awayTeam={awayArchetypes?.team_abbr || 'Away'}
        homeStats={homeStatValues}
        awayStats={awayStatValues}
        window={window}
        onArchetypeClick={fetchArchetypeMatchGames}
      />

      {/* Defensive Section */}
      <ArchetypeGrid
        type="defensive"
        family={family}
        homeData={homeFamilyData?.defensive?.[window]}
        awayData={awayFamilyData?.defensive?.[window]}
        homeTeam={homeArchetypes?.team_abbr || 'Home'}
        awayTeam={awayArchetypes?.team_abbr || 'Away'}
        homeStats={homeStatValues}
        awayStats={awayStatValues}
        window={window}
        onArchetypeClick={fetchArchetypeMatchGames}
      />

      {/* SAFE MODE ADDITION: Games vs This Archetype Panel (below existing archetypes) */}
      {selectedArchetype && (
        <div className="mt-8 border-t-2 border-gray-300 dark:border-gray-600 pt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Historical Games vs This Archetype
            </h3>
            <button
              onClick={() => {
                setSelectedArchetype(null)
                setArchetypeGames([])
              }}
              className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              ✕ Close
            </button>
          </div>

          {archetypeGamesLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
              <p className="text-sm text-gray-500">Loading games...</p>
            </div>
          ) : archetypeGames.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p>No matching games found.</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                Found {archetypeGames.length} game{archetypeGames.length !== 1 ? 's' : ''}
              </p>
              <div className="grid gap-2">
                {archetypeGames.map((game) => (
                  <div
                    key={game.game_id}
                    onClick={() => {
                      // Navigate to game detail using existing navigation
                      window.location.href = `/game/${game.game_id}`
                    }}
                    className="p-3 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {game.matchup}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            game.wl === 'W'
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                              : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                          }`}>
                            {game.wl}
                          </span>
                          <span className="text-xs text-gray-500">
                            {game.is_home ? 'Home' : 'Away'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-4 mt-1">
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {game.game_date}
                          </span>
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {game.team_pts} - {game.opp_pts}
                          </span>
                          <span className="text-xs text-gray-500">
                            vs {game.opponent?.tricode}
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-500">Click to view</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * ArchetypeGrid - Shows all 4 archetypes with opponent highlighting
 */
function ArchetypeGrid({ type, family, homeData, awayData, homeTeam, awayTeam, homeStats, awayStats, window, onArchetypeClick }) {
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
function ArchetypeCard({ archetypeId, name, isCurrent, isOpponent, stats, family, teamColor, onClick }) {
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

  // Get stat display based on family
  const getStatDisplay = (stats, family) => {
    if (!stats) return null

    if (family === 'scoring') {
      return `${stats.ppg.toFixed(1)} PPG`
    } else if (family === 'threes') {
      return `${stats.threesPG.toFixed(1)} 3PM | ${(stats.threePct * 100).toFixed(1)}%`
    } else if (family === 'turnovers') {
      return `${stats.tovPG.toFixed(1)} TOV/G`
    } else if (family === 'assists') {
      return `${stats.apg.toFixed(1)} APG`
    } else if (family === 'rebounds') {
      return `${stats.rpg.toFixed(1)} RPG (${stats.orpg.toFixed(1)} O / ${stats.drpg.toFixed(1)} D)`
    }

    return null
  }

  const statDisplay = getStatDisplay(stats, family)

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
