/**
 * ArchetypeRankingsPanel Component
 *
 * Displays ALL archetypes for a family with opponent archetype highlighting.
 * Shows offensive and defensive archetypes in a grid layout with percentile rankings.
 */

import { useState } from 'react'
import GlassTooltip from './GlassTooltip'

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
      glass_crasher_elite: { name: 'Glass Crasher Elite', color: 'purple' },
      selective_crasher: { name: 'Selective Crasher', color: 'blue' },
      transition_focused: { name: 'Transition Focused', color: 'green' },
      passive_offense_boards: { name: 'Passive Offense Boards', color: 'gray' }
    },
    defensive: {
      defensive_glass_dominant: { name: 'Defensive Glass Dominant', color: 'indigo' },
      boxing_out_discipline: { name: 'Boxing Out Discipline', color: 'teal' },
      vulnerable_boards: { name: 'Vulnerable Boards', color: 'orange' },
      average_rebounding: { name: 'Average Rebounding', color: 'gray' }
    }
  },
  threes: {
    offensive: {
      volume_three_bomber: { name: 'Volume Three Bomber', color: 'purple' },
      efficient_three_selective: { name: 'Efficient Three Selective', color: 'blue' },
      high_volume_low_efficiency: { name: 'High Volume Low-Efficiency', color: 'orange' },
      midrange_paint_focused: { name: 'Midrange/Paint Focused', color: 'gray' }
    },
    defensive: {
      three_point_lockdown: { name: 'Three-Point Lockdown', color: 'indigo' },
      contest_rate_elite: { name: 'Contest Rate Elite', color: 'teal' },
      three_point_vulnerable: { name: 'Three-Point Vulnerable', color: 'red' },
      average_perimeter_defense: { name: 'Average Perimeter Defense', color: 'gray' }
    }
  },
  turnovers: {
    offensive: {
      ball_security_elite: { name: 'Ball Security Elite', color: 'purple' },
      careful_controlled: { name: 'Careful Controlled', color: 'blue' },
      turnover_prone: { name: 'Turnover Prone', color: 'orange' },
      average_ball_security: { name: 'Average Ball Security', color: 'gray' }
    },
    defensive: {
      ball_hawking_pressure: { name: 'Ball Hawking Pressure', color: 'indigo' },
      steal_rate_elite: { name: 'Steal Rate Elite', color: 'teal' },
      passive_low_pressure: { name: 'Passive Low-Pressure', color: 'green' },
      average_pressure: { name: 'Average Pressure', color: 'gray' }
    }
  }
}

/**
 * Main component that renders offensive and defensive archetype grids
 */
function ArchetypeRankingsPanel({
  family,          // 'scoring' | 'assists' | 'rebounds' | 'threes' | 'turnovers'
  homeArchetypes,  // Full archetype object for home team
  awayArchetypes,  // Full archetype object for away team
  window,          // 'season' | 'last10'
  homeTeamStats,   // Home team stats (PPG, etc.)
  awayTeamStats    // Away team stats (PPG, etc.)
}) {
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
        window={window}
      />

      {/* Defensive Section */}
      <ArchetypeGrid
        type="defensive"
        family={family}
        homeData={homeFamilyData?.defensive?.[window]}
        awayData={awayFamilyData?.defensive?.[window]}
        homeTeam={homeArchetypes?.team_abbr || 'Home'}
        awayTeam={awayArchetypes?.team_abbr || 'Away'}
        window={window}
      />
    </div>
  )
}

/**
 * ArchetypeGrid - Shows all 4 archetypes with opponent highlighting
 */
function ArchetypeGrid({ type, family, homeData, awayData, homeTeam, awayTeam, window }) {
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
                  percentile={isCurrentArchetype ? awayData.percentile : null}
                  teamColor="orange"
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
                  percentile={isCurrentArchetype ? homeData.percentile : null}
                  teamColor="blue"
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
 * ArchetypeCard - Individual archetype card with highlighting
 */
function ArchetypeCard({ archetypeId, name, isCurrent, isOpponent, percentile, teamColor }) {
  const getCardClasses = () => {
    let classes = 'p-3 rounded-lg border-2 transition-all '

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
      // Opponent's archetype - yellow warning border
      classes += 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500 dark:border-yellow-400 shadow-md'
    } else {
      // Inactive archetype - gray
      classes += 'bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600 opacity-60'
    }

    return classes
  }

  const getStrengthBadge = (pct) => {
    if (!pct) return null
    if (pct >= 80) return { label: 'Elite', color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' }
    if (pct >= 60) return { label: 'Above Avg', color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' }
    if (pct >= 40) return { label: 'Average', color: 'bg-gray-100 dark:bg-gray-700/30 text-gray-700 dark:text-gray-300' }
    if (pct >= 20) return { label: 'Below Avg', color: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300' }
    return { label: 'Poor', color: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' }
  }

  const strength = getStrengthBadge(percentile)

  return (
    <div className={getCardClasses()}>
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

          {isCurrent && percentile && (
            <div className="mt-2 flex items-center gap-3">
              {/* Percentile Bar */}
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    teamColor === 'blue' ? 'bg-blue-500 dark:bg-blue-600' : 'bg-orange-500 dark:bg-orange-600'
                  }`}
                  style={{ width: `${Math.max(percentile, 5)}%` }}
                />
              </div>
              {/* Percentile Text */}
              <span className="text-xs font-bold text-gray-700 dark:text-gray-300 w-12 text-right">
                {percentile.toFixed(0)}%ile
              </span>
              {/* Strength Badge */}
              {strength && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${strength.color}`}>
                  {strength.label}
                </span>
              )}
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
