import GlassTooltip from './GlassTooltip'
import './GlassTooltip.css'
import { formatDelta, shouldInvertColors } from '../utils/formatHelpers.jsx'
import { getOffenseHeat, getRestStatus } from '../utils/predictionHelpers'

function Last5TrendsCard({ teamAbbr, trends, side, prediction, seasonPPG }) {
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

  // Quality badge styling
  const qualityBadgeClass = data_quality === 'excellent'
    ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
    : data_quality === 'good'
    ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
    : 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400'

  // Calculate heat check
  const heatStatus = getOffenseHeat(
    averages?.ppg || 0,
    seasonPPG || 0
  )

  // Get rest status from prediction
  const restStatus = getRestStatus(
    side === 'home' ? prediction?.back_to_back_debug?.home : prediction?.back_to_back_debug?.away
  )

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

      {/* NEW: Heat Check & Rest Status Row */}
      <div className="grid grid-cols-2 gap-3 mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        {/* Offense Heat Check */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 rounded-lg p-3">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">
            OFFENSE HEAT
          </div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{heatStatus.icon}</span>
            <span className={`text-sm font-bold ${
              heatStatus.color === 'red' ? 'text-red-600 dark:text-red-400' :
              heatStatus.color === 'blue' ? 'text-blue-600 dark:text-blue-400' :
              'text-gray-600 dark:text-gray-400'
            }`}>
              {heatStatus.label}
            </span>
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            {heatStatus.description}
          </div>
        </div>

        {/* Rest Status */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 rounded-lg p-3">
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 font-semibold">
            REST STATUS
          </div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
              restStatus.color === 'red' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' :
              restStatus.color === 'yellow' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300' :
              'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
            }`}>
              {restStatus.label}
            </span>
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            {restStatus.days} days rest
            {restStatus.warning && ' ⚠️'}
          </div>
        </div>
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
            {averages.def_rtg.toFixed(1)} {formatDelta(season_comparison.def_rtg_delta, shouldInvertColors('def_rtg'))}
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
            const oppPts = game.opp_pts || 0
            const teamPts = game.team_pts || 0
            const result = game.matchup || ''

            // Color badge by opponent strength
            const strengthColor = strength === 'top'
              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-700'
              : strength === 'mid'
              ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-700'
              : strength === 'bottom'
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600'

            return (
              <GlassTooltip
                key={idx}
                content={`${result}\n${opponentTricode} scored ${oppPts} pts (${teamAbbr}: ${teamPts})\nRank: OFF #${game.opponent?.off_rtg_rank || 'N/A'}, DEF #${game.opponent?.def_rtg_rank || 'N/A'}`}
              >
                <span className={`px-2 py-0.5 rounded text-xs font-medium cursor-help ${strengthColor}`}>
                  {opponentTricode}
                </span>
              </GlassTooltip>
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
