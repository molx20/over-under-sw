function Last5TrendsCard({ teamAbbr, trends, side }) {
  // Handle missing or empty trends data
  if (!trends || !trends.games || trends.games.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">
            {teamAbbr} - Last 5 Games
          </h3>
          <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs font-medium rounded">
            No data
          </span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No recent game data available
        </p>
      </div>
    )
  }

  const { games, averages, season_comparison, opponent_breakdown, trend_tags, data_quality } = trends

  // Helper function to format delta with color
  const formatDelta = (delta, invertColors = false) => {
    if (!delta || delta === 0) {
      return <span className="text-gray-500 dark:text-gray-400">(+0.0)</span>
    }

    // For defensive stats, negative is good (invertColors = true)
    const isPositive = invertColors ? delta < 0 : delta > 0
    const colorClass = isPositive
      ? 'text-green-600 dark:text-green-400'
      : 'text-red-600 dark:text-red-400'

    return (
      <span className={colorClass}>
        ({delta > 0 ? '+' : ''}{delta.toFixed(1)})
      </span>
    )
  }

  // Quality badge styling
  const qualityBadgeClass = data_quality === 'excellent'
    ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
    : data_quality === 'good'
    ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
    : 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400'

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">
          {teamAbbr} - Last 5 Games
        </h3>
        <span className={`px-2 py-1 text-xs font-medium rounded ${qualityBadgeClass}`}>
          {games.length} {games.length === 1 ? 'game' : 'games'}
        </span>
      </div>

      {/* Averages vs Season */}
      <div className="space-y-2 sm:space-y-3 mb-4">
        <div className="flex justify-between items-center text-sm sm:text-base">
          <span className="text-gray-600 dark:text-gray-400">Pace:</span>
          <div className="font-semibold text-gray-900 dark:text-white">
            {averages.pace.toFixed(1)} {formatDelta(season_comparison.pace_delta)}
          </div>
        </div>
        <div className="flex justify-between items-center text-sm sm:text-base">
          <span className="text-gray-600 dark:text-gray-400">OFF RTG:</span>
          <div className="font-semibold text-gray-900 dark:text-white">
            {averages.off_rtg.toFixed(1)} {formatDelta(season_comparison.off_rtg_delta)}
          </div>
        </div>
        <div className="flex justify-between items-center text-sm sm:text-base">
          <span className="text-gray-600 dark:text-gray-400">DEF RTG:</span>
          <div className="font-semibold text-gray-900 dark:text-white">
            {averages.def_rtg.toFixed(1)} {formatDelta(season_comparison.def_rtg_delta, true)}
          </div>
        </div>
        <div className="flex justify-between items-center text-sm sm:text-base">
          <span className="text-gray-600 dark:text-gray-400">PPG:</span>
          <div className="font-semibold text-gray-900 dark:text-white">
            {averages.ppg.toFixed(1)} {formatDelta(season_comparison.ppg_delta)}
          </div>
        </div>
      </div>

      {/* Past Opponents */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mb-4">
        <h4 className="text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Past Opponents
        </h4>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {games.map((game, idx) => {
            const opponentTricode = game.opponent?.tricode || 'UNK'
            const strength = game.opponent?.strength || 'unknown'

            // Color badge by opponent strength
            const strengthColor = strength === 'top'
              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-700'
              : strength === 'mid'
              ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-700'
              : strength === 'bottom'
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600'

            return (
              <span
                key={idx}
                className={`px-2 py-0.5 rounded text-xs font-medium ${strengthColor}`}
                title={`Rank: OFF #${game.opponent?.off_rtg_rank || 'N/A'}, DEF #${game.opponent?.def_rtg_rank || 'N/A'}`}
              >
                {opponentTricode}
              </span>
            )
          })}
        </div>
        {opponent_breakdown.avg_opp_off_rank && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Avg opponent: OFF #{opponent_breakdown.avg_opp_off_rank.toFixed(1)}, DEF #{opponent_breakdown.avg_opp_def_rank?.toFixed(1) || 'N/A'}
          </p>
        )}
      </div>

      {/* Trend Tags */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
        <h4 className="text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Trends
        </h4>
        <div className="flex flex-wrap gap-2">
          {trend_tags.map((tag, idx) => (
            <span
              key={idx}
              className="px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs sm:text-sm rounded-full font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Last5TrendsCard
