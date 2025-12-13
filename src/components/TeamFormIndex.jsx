/**
 * TeamFormIndex Component
 *
 * Displays season vs Last 5 games comparison for both teams
 * Shows ORTG, DRTG, PPG, and 3P% with deltas and trend indicators
 */
function TeamFormIndex({ homeTeam, awayTeam, homeStats, awayStats, homeRecentGames, awayRecentGames }) {

  // Calculate Last 5 averages from recent games
  const calculateLast5Stats = (recentGames) => {
    if (!recentGames || recentGames.length === 0) {
      return { ortg: null, drtg: null, ppg: null, fg3_pct: null }
    }

    const games = recentGames.slice(0, 5)
    const count = games.length

    const totals = games.reduce((acc, game) => {
      acc.ortg += game.off_rating || 0
      acc.drtg += game.def_rating || 0
      acc.ppg += game.team_pts || 0
      acc.fg3_pct += game.fg3_pct || 0
      return acc
    }, { ortg: 0, drtg: 0, ppg: 0, fg3_pct: 0 })

    return {
      ortg: (totals.ortg / count).toFixed(1),
      drtg: (totals.drtg / count).toFixed(1),
      ppg: (totals.ppg / count).toFixed(1),
      fg3_pct: (totals.fg3_pct / count).toFixed(1)
    }
  }

  const homeLast5 = calculateLast5Stats(homeRecentGames)
  const awayLast5 = calculateLast5Stats(awayRecentGames)

  // Calculate deltas
  const calculateDelta = (seasonVal, last5Val) => {
    if (!seasonVal || !last5Val) return null
    return (parseFloat(last5Val) - parseFloat(seasonVal)).toFixed(1)
  }

  const homeDeltas = {
    ortg: calculateDelta(homeStats?.off_rating, homeLast5.ortg),
    drtg: calculateDelta(homeStats?.def_rating, homeLast5.drtg),
    ppg: calculateDelta(homeStats?.ppg, homeLast5.ppg),
    fg3_pct: calculateDelta(homeStats?.fg3_pct, homeLast5.fg3_pct)
  }

  const awayDeltas = {
    ortg: calculateDelta(awayStats?.off_rating, awayLast5.ortg),
    drtg: calculateDelta(awayStats?.def_rating, awayLast5.drtg),
    ppg: calculateDelta(awayStats?.ppg, awayLast5.ppg),
    fg3_pct: calculateDelta(awayStats?.fg3_pct, awayLast5.fg3_pct)
  }

  // Generate summary text
  const generateSummary = (teamAbbr, deltas) => {
    const ortgChange = deltas.ortg ? parseFloat(deltas.ortg) : 0
    const drtgChange = deltas.drtg ? parseFloat(deltas.drtg) : 0

    const ortgText = ortgChange > 0
      ? `Offense +${Math.abs(ortgChange).toFixed(1)} vs season`
      : ortgChange < 0
        ? `Offense ${ortgChange} vs season`
        : 'Offense unchanged'

    const drtgText = drtgChange < 0
      ? `Defense +${Math.abs(drtgChange).toFixed(1)} (better)`
      : drtgChange > 0
        ? `Defense +${drtgChange} (worse)`
        : 'Defense unchanged'

    return `${teamAbbr} ${ortgText}, ${drtgText}`
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
        Team Form Index
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        Season averages vs Last 5 games performance
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Away Team */}
        <TeamFormCard
          team={awayTeam}
          stats={awayStats}
          last5={awayLast5}
          deltas={awayDeltas}
          isHome={false}
        />

        {/* Home Team */}
        <TeamFormCard
          team={homeTeam}
          stats={homeStats}
          last5={homeLast5}
          deltas={homeDeltas}
          isHome={true}
        />
      </div>

      {/* Summary */}
      <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 space-y-2">
        <div className="text-sm text-gray-700 dark:text-gray-300">
          {generateSummary(awayTeam?.abbreviation, awayDeltas)}
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300">
          {generateSummary(homeTeam?.abbreviation, homeDeltas)}
        </div>
      </div>
    </div>
  )
}

function TeamFormCard({ team, stats, last5, deltas, isHome }) {
  const getDeltaColor = (delta, inverse = false) => {
    if (!delta || delta === 0) return 'text-gray-500'
    const positive = parseFloat(delta) > 0
    if (inverse) {
      return positive ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
    }
    return positive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
  }

  const getDeltaIcon = (delta, inverse = false) => {
    if (!delta || delta === 0) return '→'
    const positive = parseFloat(delta) > 0
    if (inverse) {
      return positive ? '↓' : '↑'
    }
    return positive ? '↑' : '↓'
  }

  const formatDelta = (delta) => {
    if (!delta) return '-'
    const val = parseFloat(delta)
    return val > 0 ? `+${delta}` : delta
  }

  return (
    <div className={`p-4 rounded-lg ${isHome ? 'bg-primary-50 dark:bg-primary-900/20' : 'bg-gray-50 dark:bg-gray-900/30'}`}>
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-bold text-gray-900 dark:text-white text-lg">
          {team?.abbreviation}
        </h4>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
          {isHome ? 'HOME' : 'AWAY'}
        </span>
      </div>

      <div className="space-y-3">
        {/* ORTG */}
        <StatRow
          label="ORTG"
          seasonValue={stats?.off_rating}
          last5Value={last5.ortg}
          delta={deltas.ortg}
          getDeltaColor={getDeltaColor}
          getDeltaIcon={getDeltaIcon}
          formatDelta={formatDelta}
        />

        {/* DRTG */}
        <StatRow
          label="DRTG"
          seasonValue={stats?.def_rating}
          last5Value={last5.drtg}
          delta={deltas.drtg}
          getDeltaColor={getDeltaColor}
          getDeltaIcon={getDeltaIcon}
          formatDelta={formatDelta}
          inverse={true}
        />

        {/* PPG */}
        <StatRow
          label="PPG"
          seasonValue={stats?.ppg}
          last5Value={last5.ppg}
          delta={deltas.ppg}
          getDeltaColor={getDeltaColor}
          getDeltaIcon={getDeltaIcon}
          formatDelta={formatDelta}
        />

        {/* 3P% */}
        <StatRow
          label="3P%"
          seasonValue={stats?.fg3_pct}
          last5Value={last5.fg3_pct}
          delta={deltas.fg3_pct}
          getDeltaColor={getDeltaColor}
          getDeltaIcon={getDeltaIcon}
          formatDelta={formatDelta}
          isPercentage={true}
        />
      </div>
    </div>
  )
}

function StatRow({ label, seasonValue, last5Value, delta, getDeltaColor, getDeltaIcon, formatDelta, inverse = false, isPercentage = false }) {
  const suffix = isPercentage ? '%' : ''

  return (
    <div className="flex items-center justify-between text-sm">
      <span className="font-medium text-gray-700 dark:text-gray-300 w-16">{label}</span>
      <div className="flex items-center space-x-3 flex-1 justify-end">
        <div className="text-right">
          <div className="text-gray-500 dark:text-gray-400 text-xs">Season</div>
          <div className="text-gray-900 dark:text-white font-semibold">
            {seasonValue ? `${parseFloat(seasonValue).toFixed(1)}${suffix}` : '-'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-gray-500 dark:text-gray-400 text-xs">Last 5</div>
          <div className="text-gray-900 dark:text-white font-semibold">
            {last5Value ? `${last5Value}${suffix}` : '-'}
          </div>
        </div>
        <div className={`text-right min-w-[50px] ${getDeltaColor(delta, inverse)} font-bold`}>
          <div className="text-xs opacity-60">Δ</div>
          <div className="flex items-center justify-end">
            <span className="mr-1">{getDeltaIcon(delta, inverse)}</span>
            <span>{formatDelta(delta)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TeamFormIndex
