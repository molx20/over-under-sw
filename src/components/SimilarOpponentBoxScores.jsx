import { useState, useEffect } from 'react'

/**
 * SimilarOpponentBoxScores Component
 *
 * Displays actual box scores from games where each team played opponents
 * similar to their current matchup opponent.
 *
 * Shows:
 * - Summary averages (pts, pace, 3PA, paint, etc.)
 * - Individual game tiles with detailed box scores
 * - Cluster context for opponent archetypes
 */
function SimilarOpponentBoxScores({ gameId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!gameId) return

    const fetchData = async () => {
      try {
        setLoading(true)
        const response = await fetch(`/api/games/${gameId}/similar-opponent-boxscores`)
        const result = await response.json()

        if (result.success) {
          setData(result)
        } else {
          setError(result.error || 'Failed to load data')
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [gameId])

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-12 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <span className="ml-3 text-gray-600 dark:text-gray-400">Loading similar opponent data...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
        <p className="text-red-600 dark:text-red-400">Error: {error}</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Home Team Section */}
      <TeamSection teamData={data.home_team} isHome={true} />

      {/* Away Team Section */}
      <TeamSection teamData={data.away_team} isHome={false} />
    </div>
  )
}

/**
 * TeamSection Component
 * Displays one team's performance vs similar opponent types
 */
function TeamSection({ teamData, isHome }) {
  const { team_name, team_abbr, vs_similar_to, cluster_label, cluster_description, similar_teams, sample } = teamData

  const hasGames = sample && sample.games_played > 0

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">
          {team_abbr} vs Teams Similar to {vs_similar_to}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {cluster_label && (
            <span>
              Matchup vs <span className="font-semibold">{cluster_label}</span> playstyle
            </span>
          )}
        </p>
      </div>

      {/* Cluster Description */}
      {cluster_description && (
        <div className="mb-4 p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
          <p className="text-sm text-primary-900 dark:text-primary-100">
            {cluster_description}
          </p>
        </div>
      )}

      {/* Similar Teams List */}
      {similar_teams && similar_teams.length > 0 && (
        <div className="mb-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            Similar teams: {similar_teams.map(t => t.team_abbr).join(', ')}
          </p>
        </div>
      )}

      {/* No Games Message */}
      {!hasGames && (
        <div className="p-4 bg-gray-50 dark:bg-gray-900/30 rounded-lg text-center">
          <p className="text-gray-600 dark:text-gray-400">
            No games played vs similar teams this season
          </p>
        </div>
      )}

      {/* Summary Stats */}
      {hasGames && sample.summary && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-gray-900 dark:text-white">
              vs Similar Opponents ({sample.games_played} games)
            </h4>
            <span className="text-sm font-semibold px-3 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
              Record: {sample.record}
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
            <StatItem label="Avg Scored" seasonValue={teamData.season_avg?.avg_pts_scored} similarValue={sample.summary.avg_pts_scored} />
            <StatItem label="Avg Allowed" seasonValue={teamData.season_avg?.avg_pts_allowed} similarValue={sample.summary.avg_pts_allowed} />
            <StatItem label="Avg Total" seasonValue={teamData.season_avg?.avg_total} similarValue={sample.summary.avg_total} />
            <StatItem label="Avg Pace" seasonValue={teamData.season_avg?.avg_pace} similarValue={sample.summary.avg_pace} />
            <StatItem label="Avg 3PA" seasonValue={teamData.season_avg?.avg_three_pa} similarValue={sample.summary.avg_three_pa} />
            <StatItem label="Avg 3PT%" seasonValue={teamData.season_avg?.avg_three_pct} similarValue={sample.summary.avg_three_pct} isPercentage={true} />
            <StatItem label="Avg Paint" seasonValue={teamData.season_avg?.avg_paint_pts} similarValue={sample.summary.avg_paint_pts} />
            <StatItem label="Avg TO" seasonValue={teamData.season_avg?.avg_turnovers} similarValue={sample.summary.avg_turnovers} />
            <StatItem label="Avg Assists" seasonValue={teamData.season_avg?.avg_assists} similarValue={sample.summary.avg_assists} />
            <StatItem label="Avg Reb" seasonValue={teamData.season_avg?.avg_reb} similarValue={sample.summary.avg_reb} />
            <StatItem label="Avg Fastbreak" seasonValue={teamData.season_avg?.avg_fastbreak} similarValue={sample.summary.avg_fastbreak} />
            <StatItem label="Avg 2nd Chance" seasonValue={teamData.season_avg?.avg_second_chance} similarValue={sample.summary.avg_second_chance} />
          </div>
        </div>
      )}

      {/* Individual Games */}
      {hasGames && sample.games && sample.games.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-white mb-3">
            Recent Games
          </h4>
          <div className="space-y-3">
            {sample.games.map((game, index) => (
              <GameTile key={game.game_id || index} game={game} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * StatItem Component
 * Displays stat comparison: Season | Similar Opp | Δ
 */
function StatItem({ label, seasonValue, similarValue, isPercentage = false }) {
  // Calculate delta
  const delta = similarValue !== null && seasonValue !== null
    ? (similarValue - seasonValue)
    : null

  // Determine if delta is positive or negative
  const isPositive = delta !== null && delta > 0
  const isNegative = delta !== null && delta < 0

  // Format values
  const formatValue = (val) => {
    if (val === null || val === undefined) return 'N/A'
    return isPercentage ? `${val}%` : val
  }

  const formatDelta = (d) => {
    if (d === null) return 'N/A'
    const sign = d > 0 ? '+' : ''
    return isPercentage ? `${sign}${d.toFixed(1)}` : `${sign}${d.toFixed(1)}`
  }

  return (
    <div>
      <p className="text-xs text-gray-500 dark:text-gray-500 mb-1">{label}</p>
      <div className="flex items-center space-x-2 text-sm">
        <span className="text-gray-600 dark:text-gray-400">Season</span>
        <span className="font-semibold text-gray-900 dark:text-white">{formatValue(seasonValue)}</span>
        <span className="text-gray-400">|</span>
        <span className="text-gray-600 dark:text-gray-400">vs Similar</span>
        <span className="font-semibold text-gray-900 dark:text-white">{formatValue(similarValue)}</span>
        {delta !== null && (
          <>
            <span className="text-gray-400">|</span>
            <div className="flex items-center space-x-1">
              {isPositive && (
                <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.293 7.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L6.707 7.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              )}
              {isNegative && (
                <svg className="w-3 h-3 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M14.707 12.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
              <span className={`font-semibold ${
                isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-600'
              }`}>
                {formatDelta(delta)}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

/**
 * GameTile Component
 * Individual game box score display
 */
function GameTile({ game }) {
  const isWin = game.result === 'W'

  return (
    <div className={`p-4 rounded-lg border-2 ${
      isWin
        ? 'border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20'
        : 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'
    }`}>
      {/* Game Header */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className={`text-xs font-bold px-2 py-1 rounded ${
            isWin ? 'bg-green-200 text-green-800 dark:bg-green-800 dark:text-green-200' : 'bg-red-200 text-red-800 dark:bg-red-800 dark:text-red-200'
          }`}>
            {game.result}
          </span>
          <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
            {game.date}
          </span>
        </div>
        <div className="text-sm font-semibold text-gray-900 dark:text-white">
          vs {game.opponent_abbr}
        </div>
      </div>

      {/* Score */}
      <div className="mb-2">
        <span className="text-lg font-bold text-gray-900 dark:text-white">
          {game.pts_scored}–{game.pts_allowed}
        </span>
        <span className="ml-3 text-sm text-gray-600 dark:text-gray-400">
          Total: {game.total}
        </span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {game.pace && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">Pace:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.pace}</span>
          </div>
        )}
        {game.three_pa && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">3PA:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">
              {game.three_pa} ({game.three_pct}%)
            </span>
          </div>
        )}
        {game.paint_pts !== null && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">Paint:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.paint_pts}</span>
          </div>
        )}
        {game.turnovers !== null && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">TO:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.turnovers}</span>
          </div>
        )}
        {game.assists !== null && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">Assists:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.assists}</span>
          </div>
        )}
        {game.reb !== null && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">Reb:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.reb}</span>
          </div>
        )}
        {game.fastbreak !== null && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">Fastbreak:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.fastbreak}</span>
          </div>
        )}
        {game.second_chance !== null && (
          <div>
            <span className="text-gray-500 dark:text-gray-500">2nd Chance:</span>
            <span className="ml-1 font-semibold text-gray-900 dark:text-white">{game.second_chance}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default SimilarOpponentBoxScores
