import { useState } from 'react'
import { useTeamStatsComparison } from '../utils/api'
import { formatDelta, shouldInvertColors, isPercentageStat } from '../utils/formatHelpers.jsx'

function StatsTable({ homeStats, awayStats, homeTeam, awayTeam, homeTeamId, awayTeamId }) {
  // Scope toggle state: 'season' or 'last5'
  const [selectedScope, setSelectedScope] = useState('season')

  // Fetch comparison data for both teams
  const { data: homeComparison } = useTeamStatsComparison(homeTeamId, '2025-26', 5)
  const { data: awayComparison } = useTeamStatsComparison(awayTeamId, '2025-26', 5)

  // Determine if Last 5 toggle should be enabled (both teams need games)
  const hasEnoughGames = (
    homeComparison?.last_n_stats?.games_count > 0 &&
    awayComparison?.last_n_stats?.games_count > 0
  )

  // Safe accessor with fallback
  const safeGet = (obj, path, defaultValue = 0) => {
    try {
      return path.split('.').reduce((acc, part) => acc?.[part], obj) ?? defaultValue
    } catch {
      return defaultValue
    }
  }

  const formatPct = (value) => {
    const num = parseFloat(value) || 0
    return num.toFixed(1) + '%'
  }

  const formatNum = (value) => {
    const num = parseFloat(value) || 0
    return num.toFixed(1)
  }

  // Format rank with ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
  const formatRank = (rank) => {
    if (!rank) return null
    const num = parseInt(rank)
    const suffix = ['th', 'st', 'nd', 'rd']
    const v = num % 100
    return num + (suffix[(v - 20) % 10] || suffix[v] || suffix[0])
  }

  // Helper to format a stat value
  const formatStatValue = (value, statLabel) => {
    const isPct = ['FG%', '3P%', 'FT%'].includes(statLabel)
    if (typeof value === 'number') {
      return isPct ? value.toFixed(1) + '%' : value.toFixed(1)
    }
    return value
  }

  // Map stat labels to data keys
  const statKeyMap = {
    'PPG': 'ppg',
    'OPP PPG': 'opp_ppg',
    'FG%': 'fg_pct',
    '3P%': 'three_pct',
    'FT%': 'ft_pct',
    'OFF RTG': 'off_rtg',
    'DEF RTG': 'def_rtg',
    'NET RTG': 'net_rtg',
    'Pace': 'pace'
  }

  // Get value from existing stats prop based on stat label
  const getSeasonValueFromProps = (stats, statLabel) => {
    const valueMap = {
      'PPG': formatNum(safeGet(stats, 'overall.ppg')),
      'OPP PPG': formatNum(safeGet(stats, 'overall.opp_ppg')),
      'FG%': formatPct(safeGet(stats, 'overall.fg_pct')),
      '3P%': formatPct(safeGet(stats, 'overall.fg3_pct')),
      'FT%': formatPct(safeGet(stats, 'overall.ft_pct')),
      'OFF RTG': formatNum(safeGet(stats, 'overall.ortg')),
      'DEF RTG': formatNum(safeGet(stats, 'overall.drtg')),
      'NET RTG': formatNum(safeGet(stats, 'overall.net_rtg')),
      'Pace': formatNum(safeGet(stats, 'overall.pace'))
    }
    return valueMap[statLabel] || '0.0'
  }

  // Get stat display (value, rank, delta) based on selected scope
  const getStatDisplay = (comparison, stats, statLabel) => {
    const dataKey = statKeyMap[statLabel]

    if (selectedScope === 'season') {
      // Season mode: return value from stats prop + rank from comparison
      const value = getSeasonValueFromProps(stats, statLabel)
      const rank = comparison?.season_stats?.[dataKey]?.rank
      return { value, rank, delta: null }
    } else {
      // Last-5 mode: return value + delta from comparison
      const lastNStat = comparison?.last_n_stats?.stats?.[dataKey]
      if (!lastNStat) {
        // Fallback if no last-N data
        const value = getSeasonValueFromProps(stats, statLabel)
        return { value, rank: null, delta: null }
      }
      return {
        value: formatStatValue(lastNStat.value, statLabel),
        rank: null,
        delta: lastNStat.delta
      }
    }
  }

  const stats = [
    // Record row (special case - no rank/delta)
    {
      label: 'Record',
      homeValue: `${safeGet(homeStats, 'overall.wins', 0)}-${safeGet(homeStats, 'overall.losses', 0)}`,
      awayValue: `${safeGet(awayStats, 'overall.wins', 0)}-${safeGet(awayStats, 'overall.losses', 0)}`,
      homeRank: null,
      awayRank: null,
      homeDelta: null,
      awayDelta: null,
      dataKey: null,
    },
    // Dynamically compute other stats based on scope
    ...['PPG', 'OPP PPG', 'FG%', '3P%', 'FT%', 'OFF RTG', 'DEF RTG', 'NET RTG', 'Pace'].map(statLabel => {
      const homeDisplay = getStatDisplay(homeComparison, homeStats, statLabel)
      const awayDisplay = getStatDisplay(awayComparison, awayStats, statLabel)

      return {
        label: statLabel,
        homeValue: homeDisplay.value,
        awayValue: awayDisplay.value,
        homeRank: homeDisplay.rank,
        awayRank: awayDisplay.rank,
        homeDelta: homeDisplay.delta,
        awayDelta: awayDisplay.delta,
        dataKey: statKeyMap[statLabel]
      }
    })
  ]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      <div className="px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
            Team Statistics Comparison
          </h3>

          {/* Scope Toggle */}
          <div className="flex items-center space-x-1 bg-gray-200 dark:bg-gray-600 rounded-lg p-1">
            <button
              onClick={() => setSelectedScope('season')}
              className={`px-3 py-1 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                selectedScope === 'season'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Season
            </button>
            <button
              onClick={() => setSelectedScope('last5')}
              disabled={!hasEnoughGames}
              className={`px-3 py-1 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                selectedScope === 'last5'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow'
                  : hasEnoughGames
                    ? 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    : 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
              }`}
            >
              Last 5
            </button>
          </div>
        </div>

        {/* Data quality warning for Last-5 mode */}
        {selectedScope === 'last5' && (
          homeComparison?.last_n_stats?.data_quality === 'poor' ||
          awayComparison?.last_n_stats?.data_quality === 'poor'
        ) && (
          <div className="mt-2 text-xs text-yellow-600 dark:text-yellow-400">
            Warning: Limited game data available (fewer than 3 games)
          </div>
        )}
      </div>

      {/* Desktop Table View - Hidden on mobile */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-100 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                {awayTeam}
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                Stat
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                {homeTeam}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {stats.map((stat, index) => (
              <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                  {stat.awayValue}
                  {selectedScope === 'season' && stat.awayRank && (
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {formatRank(stat.awayRank)}
                    </span>
                  )}
                  {selectedScope === 'last5' && stat.awayDelta !== null && stat.awayDelta !== undefined && (
                    <span className="ml-2 text-xs">
                      {formatDelta(
                        stat.awayDelta,
                        shouldInvertColors(stat.dataKey),
                        isPercentageStat(stat.dataKey)
                      )}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600 dark:text-gray-400 font-semibold">
                  {stat.label}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-gray-900 dark:text-white">
                  {stat.homeValue}
                  {selectedScope === 'season' && stat.homeRank && (
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {formatRank(stat.homeRank)}
                    </span>
                  )}
                  {selectedScope === 'last5' && stat.homeDelta !== null && stat.homeDelta !== undefined && (
                    <span className="ml-2 text-xs">
                      {formatDelta(
                        stat.homeDelta,
                        shouldInvertColors(stat.dataKey),
                        isPercentageStat(stat.dataKey)
                      )}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View - Shown on mobile only */}
      <div className="md:hidden divide-y divide-gray-200 dark:divide-gray-700">
        {stats.map((stat, index) => (
          <div key={index} className="p-4">
            <div className="text-center mb-3">
              <span className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                {stat.label}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <div className="flex-1 text-left">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{awayTeam}</div>
                <div className="text-base font-bold text-gray-900 dark:text-white">
                  {stat.awayValue}
                </div>
                {selectedScope === 'season' && stat.awayRank && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatRank(stat.awayRank)}
                  </div>
                )}
                {selectedScope === 'last5' && stat.awayDelta !== null && stat.awayDelta !== undefined && (
                  <div className="text-xs mt-1">
                    {formatDelta(
                      stat.awayDelta,
                      shouldInvertColors(stat.dataKey),
                      isPercentageStat(stat.dataKey)
                    )}
                  </div>
                )}
              </div>
              <div className="px-4 text-gray-400 dark:text-gray-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
              </div>
              <div className="flex-1 text-right">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{homeTeam}</div>
                <div className="text-base font-bold text-gray-900 dark:text-white">
                  {stat.homeValue}
                </div>
                {selectedScope === 'season' && stat.homeRank && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatRank(stat.homeRank)}
                  </div>
                )}
                {selectedScope === 'last5' && stat.homeDelta !== null && stat.homeDelta !== undefined && (
                  <div className="text-xs mt-1">
                    {formatDelta(
                      stat.homeDelta,
                      shouldInvertColors(stat.dataKey),
                      isPercentageStat(stat.dataKey)
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default StatsTable
