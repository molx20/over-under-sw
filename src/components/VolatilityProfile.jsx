import { useState } from 'react'

/**
 * VolatilityProfile Component
 *
 * Displays game total volatility analysis
 * Shows how much each team's game totals vary from their season average
 */
function VolatilityProfile({ homeTeam, awayTeam, homeRecentGames, awayRecentGames, homeStats, awayStats }) {
  const [showGlossary, setShowGlossary] = useState(false)

  // Calculate volatility from last 10 games
  const calculateVolatility = (recentGames, seasonAvg) => {
    if (!recentGames || recentGames.length < 5) {
      return { variance: 0, volatilityIndex: 0 }
    }

    const games = recentGames.slice(0, 10)
    const gameTotals = games.map(g => (g.team_pts || 0) + (g.opp_pts || 0))

    // Calculate average of these game totals
    const avgTotal = gameTotals.reduce((sum, total) => sum + total, 0) / gameTotals.length

    // Calculate variance (average absolute deviation from average)
    const deviations = gameTotals.map(total => Math.abs(total - avgTotal))
    const variance = deviations.reduce((sum, dev) => sum + dev, 0) / deviations.length

    // Calculate volatility index (0-10 scale)
    // Variance > 15 = very volatile (10), < 5 = very stable (0)
    const volatilityIndex = Math.min(10, Math.max(0, (variance / 15) * 10))

    return {
      variance: variance.toFixed(1),
      volatilityIndex: volatilityIndex.toFixed(1)
    }
  }

  const homeVolatility = calculateVolatility(homeRecentGames, homeStats?.ppg)
  const awayVolatility = calculateVolatility(awayRecentGames, awayStats?.ppg)

  // Combined volatility index
  const combinedVolatility = (
    (parseFloat(homeVolatility.volatilityIndex) + parseFloat(awayVolatility.volatilityIndex)) / 2
  ).toFixed(1)

  const getVolatilityTag = (index) => {
    const val = parseFloat(index)
    if (val < 3) return { text: 'Very Stable', color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' }
    if (val < 5) return { text: 'Stable', color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' }
    if (val < 7) return { text: 'Moderately Swingy', color: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300' }
    if (val < 9) return { text: 'Volatile', color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300' }
    return { text: 'Highly Volatile', color: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' }
  }

  const tag = getVolatilityTag(combinedVolatility)

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white">
          Volatility Profile
        </h3>
        <button
          onClick={() => setShowGlossary(!showGlossary)}
          className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>What is this?</span>
        </button>
      </div>

      {showGlossary && (
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Understanding Volatility
          </h4>
          <div className="text-sm text-blue-900 dark:text-blue-100 space-y-2">
            <p>
              <strong>Volatility</strong> measures how consistent or unpredictable game totals are for each team.
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li><strong>Low Volatility (0-4):</strong> Games are very predictable. Totals stay close to average.</li>
              <li><strong>Medium Volatility (5-7):</strong> Some variance. Games can swing ±10 points from average.</li>
              <li><strong>High Volatility (8-10):</strong> Very unpredictable. Totals can vary wildly game-to-game.</li>
            </ul>
            <p className="pt-2">
              <strong>Why it matters:</strong> High volatility means this matchup could easily go Over or Under — it's harder to predict. Low volatility means the game total will likely stay close to expectations.
            </p>
          </div>
        </div>
      )}

      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        How much game totals vary from average (based on last 10 games)
      </p>

      {/* Combined Volatility Index */}
      <div className="mb-6 text-center">
        <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">
          Matchup Volatility Index
        </div>
        <div className="flex items-center justify-center space-x-3">
          <div className="text-5xl font-bold text-primary-600 dark:text-primary-400">
            {combinedVolatility}
          </div>
          <div className="text-3xl text-gray-400 dark:text-gray-600">/</div>
          <div className="text-3xl text-gray-500 dark:text-gray-500">10</div>
        </div>
        <div className="mt-3">
          <span className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${tag.color}`}>
            {tag.text}
          </span>
        </div>
      </div>

      {/* Visual Bar */}
      <div className="mb-6">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 transition-all duration-300"
            style={{ width: `${(parseFloat(combinedVolatility) / 10) * 100}%` }}
          ></div>
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span>Stable</span>
          <span>Volatile</span>
        </div>
      </div>

      {/* Team Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Away Team */}
        <div className="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-gray-900 dark:text-white">
              {awayTeam?.abbreviation}
            </h4>
            <span className="text-xs text-gray-500 dark:text-gray-400">AWAY</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Volatility Index</span>
              <span className="font-bold text-gray-900 dark:text-white">
                {awayVolatility.volatilityIndex} / 10
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Avg Variance</span>
              <span className="font-bold text-gray-900 dark:text-white">
                ±{awayVolatility.variance} pts
              </span>
            </div>
          </div>
        </div>

        {/* Home Team */}
        <div className="bg-primary-50 dark:bg-primary-900/20 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-gray-900 dark:text-white">
              {homeTeam?.abbreviation}
            </h4>
            <span className="text-xs text-gray-500 dark:text-gray-400">HOME</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Volatility Index</span>
              <span className="font-bold text-gray-900 dark:text-white">
                {homeVolatility.volatilityIndex} / 10
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Avg Variance</span>
              <span className="font-bold text-gray-900 dark:text-white">
                ±{homeVolatility.variance} pts
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-700 dark:text-gray-300 text-center">
          This matchup is <span className="font-semibold">{tag.text.toLowerCase()}</span> —
          game totals can vary by {Math.max(parseFloat(homeVolatility.variance), parseFloat(awayVolatility.variance)).toFixed(1)} points from average
        </p>
      </div>
    </div>
  )
}

export default VolatilityProfile
