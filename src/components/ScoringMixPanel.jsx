import React, { useState } from 'react'
import ScoringMixBar from './ScoringMixBar'

/**
 * ScoringMixPanel - Main panel for analyzing scoring mix across 3 modes
 *
 * Props:
 *   - scoringMixData: Object with { home_team, away_team } scoring mix data
 *   - homeTeam: Object with home team info (id, name, etc.)
 *   - awayTeam: Object with away team info
 *   - isLoading: Boolean loading state
 */
function ScoringMixPanel({ scoringMixData, homeTeam, awayTeam, isLoading }) {
  const [mode, setMode] = useState('team') // 'team' | 'opp_allowed' | 'game_mix'

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">Loading scoring mix data...</div>
      </div>
    )
  }

  if (!scoringMixData || !scoringMixData.home_team || !scoringMixData.away_team) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 dark:text-gray-400">No scoring mix data available</div>
      </div>
    )
  }

  const { home_team, away_team } = scoringMixData

  // Get mode-specific descriptions
  const modeDescriptions = {
    team: 'How each team generates their own points (3PT, 2PT, FT)',
    opp_allowed: 'What scoring mix each team allows their opponents',
    game_mix: 'Combined scoring sources from both teams in their games'
  }

  // Get mode-specific data
  const getModeData = (teamData) => {
    if (mode === 'team') return teamData.team
    if (mode === 'opp_allowed') return teamData.opp_allowed
    return teamData.game_mix
  }

  const homeData = getModeData(home_team)
  const awayData = getModeData(away_team)

  // Calculate deltas (Last 5 - Season)
  const calculateDeltas = (data) => {
    if (!data || !data.last5 || !data.season) {
      return { delta_3pt: 0, delta_2pt: 0, delta_ft: 0 }
    }
    return {
      delta_3pt: data.last5.pct_3pt - data.season.pct_3pt,
      delta_2pt: data.last5.pct_2pt - data.season.pct_2pt,
      delta_ft: data.last5.pct_ft - data.season.pct_ft
    }
  }

  const homeDeltas = calculateDeltas(homeData)
  const awayDeltas = calculateDeltas(awayData)

  // Format delta with color
  const DeltaBadge = ({ value, label }) => {
    const isPositive = value > 0
    const isNeutral = Math.abs(value) < 1.0
    const colorClass = isNeutral
      ? 'text-gray-600 dark:text-gray-400'
      : isPositive
        ? 'text-green-600 dark:text-green-400'
        : 'text-red-600 dark:text-red-400'

    return (
      <div className="flex flex-col items-center">
        <div className="text-[10px] text-gray-500 dark:text-gray-500 mb-1">
          {label}
        </div>
        <div className={`text-xs font-semibold ${colorClass}`}>
          {value > 0 ? '+' : ''}{value.toFixed(1)}%
        </div>
      </div>
    )
  }

  // Team Section Component
  const TeamSection = ({ team, teamData, deltas, isHome }) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      {/* Team Header */}
      <div className="mb-4">
        <h3 className="text-sm font-bold text-gray-800 dark:text-gray-200">
          {team.team_abbreviation} - {team.full_name}
        </h3>
        <div className="text-xs text-gray-500 dark:text-gray-500">
          {isHome ? 'Home' : 'Away'}
        </div>
      </div>

      {/* Bars */}
      <div className="space-y-3 mb-4">
        <ScoringMixBar data={teamData.last5} label="Last 5" showValues={true} />
        <ScoringMixBar data={teamData.season} label="Season" showValues={true} />
      </div>

      {/* Delta Badges */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
        <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 text-center">
          Last 5 vs Season Δ
        </div>
        <div className="grid grid-cols-3 gap-2">
          <DeltaBadge value={deltas.delta_3pt} label="3PT%" />
          <DeltaBadge value={deltas.delta_2pt} label="2PT%" />
          <DeltaBadge value={deltas.delta_ft} label="FT%" />
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <div className="flex flex-col items-center gap-3">
        <div className="flex gap-2 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
          <button
            onClick={() => setMode('team')}
            className={`px-4 py-2 text-xs sm:text-sm font-medium rounded transition-colors ${
              mode === 'team'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            Team Scoring
          </button>
          <button
            onClick={() => setMode('opp_allowed')}
            className={`px-4 py-2 text-xs sm:text-sm font-medium rounded transition-colors ${
              mode === 'opp_allowed'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            Defense Allowed
          </button>
          <button
            onClick={() => setMode('game_mix')}
            className={`px-4 py-2 text-xs sm:text-sm font-medium rounded transition-colors ${
              mode === 'game_mix'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            Game Mix
          </button>
        </div>

        {/* Mode Description */}
        <p className="text-xs text-gray-600 dark:text-gray-400 text-center max-w-2xl">
          {modeDescriptions[mode]}
        </p>
      </div>

      {/* Team Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TeamSection
          team={away_team}
          teamData={awayData}
          deltas={awayDeltas}
          isHome={false}
        />
        <TeamSection
          team={home_team}
          teamData={homeData}
          deltas={homeDeltas}
          isHome={true}
        />
      </div>

      {/* Legend */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
        <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 text-center">
          Scoring Mix Legend
        </div>
        <div className="flex justify-center gap-6 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-green-500 dark:bg-green-600 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">3-Point FG</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-blue-500 dark:bg-blue-600 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">2-Point FG</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-orange-500 dark:bg-orange-600 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">Free Throws</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ScoringMixPanel
