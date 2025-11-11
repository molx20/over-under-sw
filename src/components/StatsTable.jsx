function StatsTable({ homeStats, awayStats, homeTeam, awayTeam }) {
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

  const stats = [
    // Basic Stats
    {
      label: 'Record',
      homeValue: `${safeGet(homeStats, 'overall.wins', 0)}-${safeGet(homeStats, 'overall.losses', 0)}`,
      awayValue: `${safeGet(awayStats, 'overall.wins', 0)}-${safeGet(awayStats, 'overall.losses', 0)}`
    },
    {
      label: 'PPG',
      homeValue: formatNum(safeGet(homeStats, 'overall.ppg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.ppg'))
    },
    {
      label: 'OPP PPG',
      homeValue: formatNum(safeGet(homeStats, 'overall.opp_ppg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.opp_ppg'))
    },
    {
      label: 'FG%',
      homeValue: formatPct(safeGet(homeStats, 'overall.fg_pct')),
      awayValue: formatPct(safeGet(awayStats, 'overall.fg_pct'))
    },
    {
      label: '3P%',
      homeValue: formatPct(safeGet(homeStats, 'overall.fg3_pct')),
      awayValue: formatPct(safeGet(awayStats, 'overall.fg3_pct'))
    },
    {
      label: 'FT%',
      homeValue: formatPct(safeGet(homeStats, 'overall.ft_pct')),
      awayValue: formatPct(safeGet(awayStats, 'overall.ft_pct'))
    },
    // Advanced Stats
    {
      label: 'OFF RTG',
      homeValue: formatNum(safeGet(homeStats, 'overall.ortg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.ortg'))
    },
    {
      label: 'DEF RTG',
      homeValue: formatNum(safeGet(homeStats, 'overall.drtg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.drtg'))
    },
    {
      label: 'NET RTG',
      homeValue: formatNum(safeGet(homeStats, 'overall.net_rtg')),
      awayValue: formatNum(safeGet(awayStats, 'overall.net_rtg'))
    },
    {
      label: 'Pace',
      homeValue: formatNum(safeGet(homeStats, 'overall.pace')),
      awayValue: formatNum(safeGet(awayStats, 'overall.pace'))
    },
  ]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Team Statistics Comparison</h3>
      </div>
      <div className="overflow-x-auto">
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
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-600 dark:text-gray-400 font-semibold">
                  {stat.label}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-right text-gray-900 dark:text-white">
                  {stat.homeValue}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default StatsTable
