import Last5TrendsCard from './Last5TrendsCard'

/**
 * Last5GamesPanel Component
 *
 * Displays Last 5 Game Trends for both teams side-by-side
 */
function Last5GamesPanel({ prediction, homeTeam, awayTeam }) {
  if (!prediction?.home_last5_trends && !prediction?.away_last5_trends) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>No last 5 games data available</p>
      </div>
    )
  }

  return (
    <div>
      {/* Trend Adjustment Summary */}
      {prediction?.trend_adjustment && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              <span className="font-semibold">Trend Adjustment:</span>{' '}
              {prediction.trend_adjustment.explanation}
            </p>
            <span className="text-lg font-bold text-blue-700 dark:text-blue-300">
              {prediction.trend_adjustment.total_adjustment > 0 ? '+' : ''}
              {prediction.trend_adjustment.total_adjustment} pts
            </span>
          </div>
        </div>
      )}

      {/* Side-by-side cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {prediction?.away_last5_trends && (
          <Last5TrendsCard
            teamAbbr={awayTeam?.abbreviation}
            trends={prediction.away_last5_trends}
            side="away"
            prediction={prediction}
            seasonPPG={prediction.factors?.away_ppg}
          />
        )}
        {prediction?.home_last5_trends && (
          <Last5TrendsCard
            teamAbbr={homeTeam?.abbreviation}
            trends={prediction.home_last5_trends}
            side="home"
            prediction={prediction}
            seasonPPG={prediction.factors?.home_ppg}
          />
        )}
      </div>
    </div>
  )
}

export default Last5GamesPanel
