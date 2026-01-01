/**
 * GamesVsArchetypeModal Component
 *
 * Shows games where a team played AGAINST opponents with a specific archetype
 * Example: Click TOR's defensive archetype → shows ORL games vs teams with that defense
 */

import { useState } from 'react'
import BoxScoreModal from './BoxScoreModal'

function GamesVsArchetypeModal({
  isOpen,
  onClose,
  archetype,
  archetypeType, // 'offensive' or 'defensive'
  window, // 'season' or 'last10'
  targetTeamAbbr, // The team whose games we're showing
  selectedTeamAbbr, // The team whose archetype was clicked
  games,
  summary,
  isLoading
}) {
  const [selectedGame, setSelectedGame] = useState(null)

  if (!isOpen || !archetype) return null

  const isOffensive = archetypeType === 'offensive'
  const windowLabel = window === 'season' ? 'Season' : 'Last 10 Games'

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none overflow-y-auto">
        <div
          className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-4xl w-full pointer-events-auto transform transition-all my-8"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-purple-700 text-white p-6 rounded-t-xl">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm opacity-90 mb-1">
                  {targetTeamAbbr} vs Opponents' {isOffensive ? 'Offense' : 'Defense'} · {windowLabel}
                </div>
                <h2 className="text-2xl font-bold">
                  Games vs {archetype.name}
                </h2>
                <p className="text-sm opacity-90 mt-1">
                  {targetTeamAbbr}'s games against opponents whose {isOffensive ? 'offensive' : 'defensive'} style is "{archetype.name}"
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/20 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 max-h-[70vh] overflow-y-auto">
            {isLoading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">Loading games...</p>
              </div>
            ) : games && games.length > 0 ? (
              <>
                {/* Summary Stats */}
                <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4 mb-6">
                  <h3 className="text-sm font-bold text-purple-900 dark:text-purple-300 mb-3">
                    {targetTeamAbbr}'s Performance vs {archetype.name}
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <SummaryStat
                      label="Games"
                      value={summary.games_count || 0}
                    />
                    <SummaryStat
                      label="Avg PPG"
                      value={summary.ppg?.toFixed(1) || '0.0'}
                    />
                    <SummaryStat
                      label="Avg eFG%"
                      value={`${summary.efg?.toFixed(1) || '0.0'}%`}
                    />
                    <SummaryStat
                      label="Avg FT Pts"
                      value={summary.ft_points?.toFixed(1) || '0.0'}
                    />
                    <SummaryStat
                      label="Paint Pts"
                      value={summary.paint_points?.toFixed(1) || '0.0'}
                    />
                  </div>
                  <div className="mt-3 text-xs text-purple-700 dark:text-purple-300">
                    Record: {summary.wins || 0}-{(summary.games_count || 0) - (summary.wins || 0)} ({summary.win_pct?.toFixed(1) || '0.0'}%)
                  </div>
                </div>

                {/* Game List */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                    Game History ({games.length} games)
                  </h3>
                  <div className="space-y-2">
                    {games.map((game, idx) => (
                      <GameRow
                        key={idx}
                        game={game}
                        teamAbbr={targetTeamAbbr}
                        summary={summary}
                        onClick={() => setSelectedGame(game)}
                      />
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium">No games found</p>
                <p className="text-sm mt-1">
                  {targetTeamAbbr} hasn't played against opponents with this archetype yet
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Game Details Modal (nested) */}
      {selectedGame && (
        <BoxScoreModal
          isOpen={!!selectedGame}
          onClose={() => setSelectedGame(null)}
          game={selectedGame}
          teamAbbr={targetTeamAbbr}
          summary={summary}
        />
      )}
    </>
  )
}

function SummaryStat({ label, value }) {
  return (
    <div>
      <div className="text-xs text-purple-600 dark:text-purple-400 mb-1">{label}</div>
      <div className="text-lg font-bold text-gray-900 dark:text-white">{value}</div>
    </div>
  )
}

function GameRow({ game, teamAbbr, summary, onClick }) {
  const opponentTricode = game.opponent?.tricode || game.opp_abbr || 'UNK'
  const teamPts = game.team_pts || 0
  const oppPts = game.opp_pts || 0
  const isWin = teamPts > oppPts
  const gameDate = game.game_date || 'Unknown'

  // Calculate variances from summary averages
  const ptsVariance = teamPts - (summary?.ppg || 0)
  const efgVariance = (game.efg_pct || 0) - (summary?.efg || 0)
  const ftVariance = (game.ft_points || 0) - (summary?.ft_points || 0)
  const paintVariance = (game.paint_points || 0) - (summary?.paint_points || 0)

  // Helper to render stat with variance
  const renderStatWithVariance = (value, variance, suffix = '') => {
    const varianceColor = variance > 0
      ? 'text-green-600 dark:text-green-400'
      : variance < 0
      ? 'text-red-600 dark:text-red-400'
      : 'text-gray-500 dark:text-gray-400'

    const varianceSign = variance > 0 ? '+' : ''

    return (
      <span>
        {value}{suffix}{' '}
        <span className={varianceColor}>
          ({varianceSign}{variance.toFixed(1)})
        </span>
      </span>
    )
  }

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-left"
    >
      <div className="flex items-center gap-3 flex-1">
        <div className={`w-2 h-2 rounded-full ${isWin ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className="text-sm font-semibold text-gray-900 dark:text-white">
              {game.matchup || `${teamAbbr} vs ${opponentTricode}`}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              vs {opponentTricode}
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {new Date(gameDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Game Stats with Variance */}
        <div className="hidden md:flex items-center gap-3 text-xs">
          <div title="eFG% (variance from avg)">
            <span className="text-gray-600 dark:text-gray-400">eFG:</span>{' '}
            {renderStatWithVariance(game.efg_pct?.toFixed(1) || '0.0', efgVariance, '%')}
          </div>
          <div title="FT Points (variance from avg)">
            <span className="text-gray-600 dark:text-gray-400">FT:</span>{' '}
            {renderStatWithVariance(game.ft_points || 0, ftVariance)}
          </div>
          <div title="Paint Points (variance from avg)">
            <span className="text-gray-600 dark:text-gray-400">Paint:</span>{' '}
            {renderStatWithVariance(game.paint_points || 0, paintVariance)}
          </div>
          <div title="Pace">
            <span className="text-gray-600 dark:text-gray-400">Pace:</span>{' '}
            <span className="text-gray-600 dark:text-gray-400">
              {game.pace?.toFixed(1) || '0.0'}
            </span>
          </div>
        </div>

        {/* Score with PPG Variance */}
        <div className="text-right">
          <div className="flex items-center gap-2 justify-end">
            <div className={`text-sm font-bold ${isWin ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {teamPts}
            </div>
            <span className="text-xs">
              {renderStatWithVariance('', ptsVariance)}
            </span>
            <span className="text-sm font-bold text-gray-500">-</span>
            <div className="text-sm font-bold text-gray-600 dark:text-gray-400">
              {oppPts}
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Total: {teamPts + oppPts}
          </div>
        </div>
      </div>
    </button>
  )
}

export default GamesVsArchetypeModal
