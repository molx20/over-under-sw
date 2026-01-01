/**
 * ArchetypeDrilldownModal Component
 *
 * Shows detailed stats and game history for a specific archetype
 * - Offensive: PPG bar chart by defense tier + game list
 * - Defensive: Opponent suppression stats + game list
 */

import { useState } from 'react'
import BoxScoreModal from './BoxScoreModal'

function ArchetypeDrilldownModal({
  isOpen,
  onClose,
  archetype,
  archetypeType, // 'offensive' or 'defensive'
  window, // 'season' or 'last10'
  teamAbbr,
  games, // Array of games played with this archetype
  stats, // Aggregated stats from API
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
          <div className="bg-gradient-to-r from-primary-600 to-primary-700 text-white p-6 rounded-t-xl">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm opacity-90 mb-1">
                  {teamAbbr} · {windowLabel} · {isOffensive ? 'Offensive' : 'Defensive'} Archetype
                </div>
                <h2 className="text-2xl font-bold">
                  {archetype.name}
                </h2>
                <p className="text-sm opacity-90 mt-1">
                  {archetype.description}
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
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">Loading games...</p>
              </div>
            ) : games && games.length > 0 ? (
              <>
                {/* Stats Summary */}
                {isOffensive ? (
                  <OffensiveStats stats={stats} games={games} />
                ) : (
                  <DefensiveStats stats={stats} games={games} />
                )}

                {/* Game List */}
                <div className="mt-6">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                    Game History ({games.length} games)
                  </h3>
                  <div className="space-y-2">
                    {games.map((game, idx) => (
                      <GameRow
                        key={idx}
                        game={game}
                        teamAbbr={teamAbbr}
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
                <p className="text-sm mt-1">No games played with this archetype yet</p>
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
          teamAbbr={teamAbbr}
          summary={{
            ppg: stats.avg_team_pts,
            efg: stats.avg_efg,
            ft_points: stats.avg_ft_points,
            paint_points: stats.avg_paint_points,
            ast: stats.avg_ast,
            tov: stats.avg_tov
          }}
        />
      )}
    </>
  )
}

function OffensiveStats({ stats, games }) {
  return (
    <div className="space-y-6">
      {/* Aggregated Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Avg PPG"
          value={stats.avg_team_pts?.toFixed(1) || '0.0'}
          subtitle={`${games.length} games`}
        />
        <StatCard
          label="Avg Total"
          value={stats.avg_total?.toFixed(1) || '0.0'}
          subtitle="Team + Opp"
        />
        <StatCard
          label="Avg eFG%"
          value={stats.avg_efg?.toFixed(1) || '0.0'}
          subtitle="%"
        />
        <StatCard
          label="Win Rate"
          value={stats.win_pct?.toFixed(1) || '0.0'}
          subtitle="%"
        />
      </div>

      {/* Bar Chart Placeholder - Will be enhanced with actual chart library */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          PPG by Opponent Defense Tier
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          📊 Bar chart: Season PPG vs Elite/Mid/Bottom tier defenses
          <br />
          (Chart visualization coming in next iteration)
        </div>
      </div>
    </div>
  )
}

function DefensiveStats({ stats, games }) {
  return (
    <div className="space-y-6">
      {/* Defensive Performance */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Avg Opp PPG"
          value={stats.avg_opp_pts?.toFixed(1) || '0.0'}
          subtitle={`${games.length} games`}
        />
        <StatCard
          label="Avg Total"
          value={stats.avg_total?.toFixed(1) || '0.0'}
          subtitle="Team + Opp"
        />
        <StatCard
          label="Avg Pace"
          value={stats.avg_pace?.toFixed(1) || '0.0'}
          subtitle="possessions"
        />
        <StatCard
          label="Win Rate"
          value={stats.win_pct?.toFixed(1) || '0.0'}
          subtitle="%"
        />
      </div>

      {/* Opponent Stats Placeholder */}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Opponent Suppression Metrics
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          📊 Detailed opponent metrics (eFG%, 3PA, Paint PTS, FT Rate) coming soon
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, subtitle }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
      {subtitle && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</div>
      )}
    </div>
  )
}

function GameRow({ game, teamAbbr, onClick }) {
  const opponentTricode = game.opponent?.tricode || game.opp_abbr || 'UNK'
  const teamPts = game.team_pts || 0
  const oppPts = game.opp_pts || 0
  const isWin = teamPts > oppPts
  const gameDate = game.game_date || 'Unknown'

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-left"
    >
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${isWin ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <div>
          <div className="text-sm font-semibold text-gray-900 dark:text-white">
            {game.matchup || `${teamAbbr} vs ${opponentTricode}`}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {gameDate}
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className={`text-sm font-bold ${isWin ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {teamPts} - {oppPts}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Total: {teamPts + oppPts}
        </div>
      </div>
    </button>
  )
}

// Calculate aggregated stats from games array
function calculateAggregatedStats(games, isOffensive) {
  if (!games || games.length === 0) return {}

  const stats = {
    avgPPG: 0,
    avgTotal: 0,
    avgEFG: 0,
    avgFTPoints: 0,
    avgOppEFG: 0,
    avgOpp3PA: 0,
    avgOpp3PPct: 0,
    avgOppPaintPts: 0,
    avgOppFTRate: 0,
    avgForcedTOs: 0,
    avgPace: 0,
    avgOppPPG: 0
  }

  games.forEach(game => {
    stats.avgPPG += game.team_pts || 0
    stats.avgTotal += (game.team_pts || 0) + (game.opp_pts || 0)
    stats.avgOppPPG += game.opp_pts || 0
    stats.avgPace += game.pace || 0

    // Offensive stats
    if (isOffensive) {
      // Calculate eFG% if we have the data
      // eFG% = (FGM + 0.5 * 3PM) / FGA
      // For now, use placeholder
      stats.avgEFG += 0 // TODO: Calculate from game data
      stats.avgFTPoints += 0 // TODO: Calculate from game data
    }

    // Defensive stats
    if (!isOffensive) {
      stats.avgOppEFG += 0 // TODO: Calculate opponent eFG%
      stats.avgOpp3PA += 0 // TODO: Get opponent 3PA
      stats.avgOpp3PPct += 0 // TODO: Get opponent 3P%
      stats.avgOppPaintPts += 0 // TODO: Get opponent paint points
      stats.avgOppFTRate += 0 // TODO: Calculate opponent FT rate
      stats.avgForcedTOs += game.opp_tov || game.turnovers || 0
    }
  })

  // Average everything
  const count = games.length
  Object.keys(stats).forEach(key => {
    stats[key] = stats[key] / count
  })

  return stats
}

export default ArchetypeDrilldownModal
