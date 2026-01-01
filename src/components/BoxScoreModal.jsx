/**
 * BoxScoreModal Component
 *
 * Modal popup that displays detailed game box score when clicking on opponent chips
 */
function BoxScoreModal({ isOpen, onClose, game, teamAbbr, summary = null }) {
  if (!isOpen || !game) return null

  const opponentTricode = game.opponent?.tricode || game.opp_abbr || 'UNK'
  const oppPts = game.opp_pts || 0
  const teamPts = game.team_pts || 0
  const totalPts = teamPts + oppPts
  const result = game.matchup || ''
  const offRank = game.opponent?.off_rtg_rank || 'N/A'
  const defRank = game.opponent?.def_rtg_rank || 'N/A'
  const strength = game.opponent?.strength || 'unknown'
  const gameDate = game.game_date || 'Unknown Date'

  // Box score stats (ensure all values are safe)
  const pace = Number(game.pace) || 0
  const threePt = game.three_pt || null
  const turnovers = Number(game.tov) || 0
  const assists = Number(game.ast) || 0
  const rebounds = Number(game.reb) || 0

  // Calculate additional stats for variance
  const efgPct = game.efg_pct || 0
  const ftPoints = game.ft_points || game.ftm || 0
  const paintPoints = game.paint_points || 0

  // Calculate variances from summary averages (if available)
  const ptsVariance = summary ? teamPts - (summary.ppg || 0) : null
  const efgVariance = summary ? efgPct - (summary.efg || 0) : null
  const ftVariance = summary ? ftPoints - (summary.ft_points || 0) : null
  const paintVariance = summary ? paintPoints - (summary.paint_points || 0) : null
  const astVariance = summary ? assists - (summary.ast || 0) : null
  const tovVariance = summary ? turnovers - (summary.tov || 0) : null

  // Helper to render stat with variance
  const renderStatWithVariance = (value, variance, suffix = '') => {
    if (variance === null || variance === undefined) {
      return <>{value}{suffix}</>
    }

    const varianceColor = variance > 0
      ? 'text-green-600 dark:text-green-400'
      : variance < 0
      ? 'text-red-600 dark:text-red-400'
      : 'text-gray-500 dark:text-gray-400'

    const varianceSign = variance > 0 ? '+' : ''

    return (
      <>
        {value}{suffix}{' '}
        <span className={varianceColor}>
          ({varianceSign}{variance.toFixed(1)})
        </span>
      </>
    )
  }

  // Determine result color
  const isWin = teamPts > oppPts
  const resultColor = isWin
    ? 'text-green-600 dark:text-green-400'
    : 'text-red-600 dark:text-red-400'

  // Strength badge color
  const strengthColor = strength === 'top'
    ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
    : strength === 'mid'
    ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
    : strength === 'bottom'
    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-md w-full pointer-events-auto transform transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              Game Details
            </h3>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Date and Matchup */}
            <div className="text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {gameDate}
              </div>
              <div className={`text-sm font-semibold mb-2 ${resultColor}`}>
                {result}
              </div>
              <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                {teamAbbr} {teamPts} - {oppPts} {opponentTricode}
              </div>
              {ptsVariance !== null && (
                <div className="text-sm font-medium mb-1">
                  {renderStatWithVariance('', ptsVariance, ' pts vs avg')}
                </div>
              )}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Total: {totalPts}
              </div>
            </div>

            {/* Key Stats Grid */}
            <div className="grid grid-cols-2 gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">eFG%</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {renderStatWithVariance(efgPct.toFixed(1), efgVariance, '%')}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">FT Points</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {renderStatWithVariance(ftPoints, ftVariance)}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Paint Points</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {renderStatWithVariance(paintPoints, paintVariance)}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Pace</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">{pace.toFixed(1)}</div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">3PT Points</div>
                {threePt ? (
                  <>
                    <div className="text-lg font-bold text-gray-900 dark:text-white">{threePt.points || 0} PTS</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      ({threePt.made || 0}/{threePt.attempted || 0} · {
                        threePt.percentage != null
                          ? (Number.isInteger(threePt.percentage) ? threePt.percentage : threePt.percentage.toFixed(1))
                          : '0.0'
                      }%)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="text-lg font-bold text-gray-900 dark:text-white">—</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">No 3PT data</div>
                  </>
                )}
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Assists</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {renderStatWithVariance(assists, astVariance)}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">TO</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {renderStatWithVariance(turnovers, tovVariance)}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Reb</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">{rebounds}</div>
              </div>
            </div>

            {/* Opponent Info */}
            <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Opponent Strength</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${strengthColor}`}>
                  {strength.charAt(0).toUpperCase() + strength.slice(1)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">OFF Rank</span>
                <span className="font-semibold text-gray-900 dark:text-white">#{offRank}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">DEF Rank</span>
                <span className="font-semibold text-gray-900 dark:text-white">#{defRank}</span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

export default BoxScoreModal
