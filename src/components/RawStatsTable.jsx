/**
 * RawStatsTable Component
 *
 * Displays raw matchup stats in a clean table format
 * Shows season and Last 5 stats for key metrics
 */
function RawStatsTable({ homeTeam, awayTeam, homeStats, awayStats, homeRecentGames, awayRecentGames }) {

  // Calculate Last 5 averages
  const calculateLast5Stats = (recentGames) => {
    if (!recentGames || recentGames.length === 0) {
      return { ortg: '-', drtg: '-', pace: '-', opp_fg3_pct: '-', opp_paint: '-' }
    }

    const games = recentGames.slice(0, 5)
    const count = games.length

    const totals = games.reduce((acc, game) => {
      acc.ortg += game.off_rating || 0
      acc.drtg += game.def_rating || 0
      acc.pace += game.pace || 0
      acc.opp_fg3_pct += game.opp_fg3_pct || 0
      acc.opp_paint += game.opp_points_in_paint || 0
      return acc
    }, { ortg: 0, drtg: 0, pace: 0, opp_fg3_pct: 0, opp_paint: 0 })

    return {
      ortg: (totals.ortg / count).toFixed(1),
      drtg: (totals.drtg / count).toFixed(1),
      pace: (totals.pace / count).toFixed(1),
      opp_fg3_pct: (totals.opp_fg3_pct / count).toFixed(1),
      opp_paint: (totals.opp_paint / count).toFixed(1)
    }
  }

  const homeLast5 = calculateLast5Stats(homeRecentGames)
  const awayLast5 = calculateLast5Stats(awayRecentGames)

  const rows = [
    {
      label: 'Season ORTG',
      awayValue: awayStats?.off_rating?.toFixed(1) || '-',
      homeValue: homeStats?.off_rating?.toFixed(1) || '-'
    },
    {
      label: 'Last 5 ORTG',
      awayValue: awayLast5.ortg,
      homeValue: homeLast5.ortg
    },
    {
      label: 'Season DRTG',
      awayValue: awayStats?.def_rating?.toFixed(1) || '-',
      homeValue: homeStats?.def_rating?.toFixed(1) || '-'
    },
    {
      label: 'Last 5 DRTG',
      awayValue: awayLast5.drtg,
      homeValue: homeLast5.drtg
    },
    {
      label: 'Season Pace',
      awayValue: awayStats?.pace?.toFixed(1) || '-',
      homeValue: homeStats?.pace?.toFixed(1) || '-'
    },
    {
      label: 'Last 5 Pace',
      awayValue: awayLast5.pace,
      homeValue: homeLast5.pace
    },
    {
      label: 'Opp 3P% Allowed',
      awayValue: awayStats?.opp_fg3_pct ? `${awayStats.opp_fg3_pct.toFixed(1)}%` : '-',
      homeValue: homeStats?.opp_fg3_pct ? `${homeStats.opp_fg3_pct.toFixed(1)}%` : '-'
    },
    {
      label: 'Opp Paint Pts Allowed',
      awayValue: awayStats?.opp_paint_pts_per_game?.toFixed(1) || '-',
      homeValue: homeStats?.opp_paint_pts_per_game?.toFixed(1) || '-'
    }
  ]

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
        Raw Matchup Stats
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        Direct comparison of key metrics
      </p>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-gray-300 dark:border-gray-600">
              <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Metric
              </th>
              <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                {awayTeam?.abbreviation}
                <div className="text-xs font-normal text-gray-500">AWAY</div>
              </th>
              <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                {homeTeam?.abbreviation}
                <div className="text-xs font-normal text-gray-500">HOME</div>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr
                key={index}
                className={`border-b border-gray-200 dark:border-gray-700 ${
                  index % 2 === 0 ? 'bg-gray-50 dark:bg-gray-900/30' : ''
                }`}
              >
                <td className="py-3 px-4 text-sm font-medium text-gray-900 dark:text-white">
                  {row.label}
                </td>
                <td className="py-3 px-4 text-center text-sm font-semibold text-gray-700 dark:text-gray-300">
                  {row.awayValue}
                </td>
                <td className="py-3 px-4 text-center text-sm font-semibold text-gray-700 dark:text-gray-300">
                  {row.homeValue}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default RawStatsTable
