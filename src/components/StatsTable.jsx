import { useTeamStatsWithRanks } from '../utils/api'

function StatsTable({ homeStats, awayStats, homeTeam, awayTeam, homeTeamId, awayTeamId }) {
  // Fetch rankings for both teams
  const { data: homeRankings } = useTeamStatsWithRanks(homeTeamId, '2025-26')
  const { data: awayRankings } = useTeamStatsWithRanks(awayTeamId, '2025-26')

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

  // Helper to get rank from rankings data
  const getRank = (rankingsData, statKey) => {
    if (!rankingsData?.stats?.[statKey]?.rank) return null
    return rankingsData.stats[statKey].rank
  }

  const stats = [
    // Basic Stats
    {
      label: 'Record',
      homeValue: `${safeGet(homeStats, 'overall.wins', 0)}-${safeGet(homeStats, 'overall.losses', 0)}`,
      awayValue: `${safeGet(awayStats, 'overall.wins', 0)}-${safeGet(awayStats, 'overall.losses', 0)}`,
      homeRank: null, // No rank for record
      awayRank: null,
    },
    {
      label: 'PPG',
      homeValue: formatNum(safeGet(homeStats, 'overall.ppg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.ppg')),
      homeRank: getRank(homeRankings, 'ppg'),
      awayRank: getRank(awayRankings, 'ppg'),
    },
    {
      label: 'OPP PPG',
      homeValue: formatNum(safeGet(homeStats, 'overall.opp_ppg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.opp_ppg')),
      homeRank: getRank(homeRankings, 'opp_ppg'),
      awayRank: getRank(awayRankings, 'opp_ppg'),
    },
    {
      label: 'FG%',
      homeValue: formatPct(safeGet(homeStats, 'overall.fg_pct')),
      awayValue: formatPct(safeGet(awayStats, 'overall.fg_pct')),
      homeRank: getRank(homeRankings, 'fg_pct'),
      awayRank: getRank(awayRankings, 'fg_pct'),
    },
    {
      label: '3P%',
      homeValue: formatPct(safeGet(homeStats, 'overall.fg3_pct')),
      awayValue: formatPct(safeGet(awayStats, 'overall.fg3_pct')),
      homeRank: getRank(homeRankings, 'three_pct'),
      awayRank: getRank(awayRankings, 'three_pct'),
    },
    {
      label: 'FT%',
      homeValue: formatPct(safeGet(homeStats, 'overall.ft_pct')),
      awayValue: formatPct(safeGet(awayStats, 'overall.ft_pct')),
      homeRank: getRank(homeRankings, 'ft_pct'),
      awayRank: getRank(awayRankings, 'ft_pct'),
    },
    // Advanced Stats
    {
      label: 'OFF RTG',
      homeValue: formatNum(safeGet(homeStats, 'overall.ortg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.ortg')),
      homeRank: getRank(homeRankings, 'off_rtg'),
      awayRank: getRank(awayRankings, 'off_rtg'),
    },
    {
      label: 'DEF RTG',
      homeValue: formatNum(safeGet(homeStats, 'overall.drtg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.drtg')),
      homeRank: getRank(homeRankings, 'def_rtg'),
      awayRank: getRank(awayRankings, 'def_rtg'),
    },
    {
      label: 'NET RTG',
      homeValue: formatNum(safeGet(homeStats, 'overall.net_rtg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.net_rtg')),
      homeRank: getRank(homeRankings, 'net_rtg'),
      awayRank: getRank(awayRankings, 'net_rtg'),
    },
    {
      label: 'Pace',
      homeValue: formatNum(safeGet(homeStats, 'overall.pace')),
      awayValue: formatNum(safeGet(awayStats, 'overall.pace')),
      homeRank: getRank(homeRankings, 'pace'),
      awayRank: getRank(awayRankings, 'pace'),
    },
  ]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      <div className="px-4 sm:px-6 py-3 sm:py-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">Team Statistics Comparison</h3>
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
                  {stat.awayRank && (
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {formatRank(stat.awayRank)}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600 dark:text-gray-400 font-semibold">
                  {stat.label}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-gray-900 dark:text-white">
                  {stat.homeValue}
                  {stat.homeRank && (
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {formatRank(stat.homeRank)}
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
                {stat.awayRank && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatRank(stat.awayRank)}
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
                {stat.homeRank && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {formatRank(stat.homeRank)}
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
