import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import StatsTable from '../components/StatsTable'
import { useGameDetail } from '../utils/api'

function GamePage() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const [bettingLine, setBettingLine] = useState('')
  const [customBettingLine, setCustomBettingLine] = useState(null)

  // Use React Query for automatic caching and loading states
  const {
    data: gameData,
    isLoading,
    isFetching,
    isError,
    error,
    refetch
  } = useGameDetail(gameId, customBettingLine)

  const handleCalculatePrediction = () => {
    const line = parseFloat(bettingLine)
    if (isNaN(line) || line <= 0) {
      alert('Please enter a valid betting line')
      return
    }
    // Trigger new query with betting line
    // React Query will cache this separately
    setCustomBettingLine(line)
  }

  // Show loading state only on initial load (no cached data)
  if (isLoading && !gameData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Generating prediction...</p>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">Fetching NBA stats and generating prediction</p>
          <p className="mt-1 text-xs text-gray-400 dark:text-gray-600">This usually takes 15-60 seconds. If it times out, try clicking again - it may work from cache.</p>
        </div>
      </div>
    )
  }

  // Show error state with retry option
  if (isError || !gameData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={() => navigate('/')}
          className="mb-4 text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Games</span>
        </button>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <h3 className="text-red-800 dark:text-red-400 font-semibold mb-2">Error Loading Game</h3>
          <p className="text-red-600 dark:text-red-300 mb-4">{error?.message || 'Game not found'}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  const { prediction, home_stats, away_stats, home_recent_games, away_recent_games, home_team, away_team } = gameData

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span>Back to Games</span>
      </button>

      {/* Stale data indicator - shows when fetching in background */}
      {isFetching && gameData && (
        <div className="mb-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 flex items-center space-x-2">
          <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="text-sm text-blue-700 dark:text-blue-300">Updating prediction...</span>
        </div>
      )}

      {/* Betting Line Input */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Enter Betting Line</h3>
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <label htmlFor="betting-line" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Your Sportsbook's Over/Under Line
            </label>
            <input
              id="betting-line"
              type="number"
              step="0.5"
              placeholder="e.g. 220.5"
              value={bettingLine}
              onChange={(e) => setBettingLine(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            />
          </div>
          <button
            onClick={handleCalculatePrediction}
            disabled={isFetching}
            className="mt-7 px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isFetching && (
              <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            )}
            <span>{isFetching ? 'Calculating...' : 'Calculate Prediction'}</span>
          </button>
        </div>
      </div>

      {/* Prediction Summary */}
      {prediction && prediction.betting_line && (
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg shadow-lg p-8 mb-8 text-white">
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-2">{away_team?.abbreviation || 'Away'} @ {home_team?.abbreviation || 'Home'}</h1>
            <p className="text-lg opacity-90">{away_team?.name || 'Away Team'} at {home_team?.name || 'Home Team'}</p>
            <div className="flex justify-center items-center space-x-8 mt-6">
              <div>
                <div className="text-sm opacity-80 mb-1">Betting Line</div>
                <div className="text-4xl font-bold">{prediction.betting_line}</div>
              </div>
              <div className="text-4xl opacity-50">→</div>
              <div>
                <div className="text-sm opacity-80 mb-1">Predicted Total</div>
                <div className="text-4xl font-bold">{prediction.predicted_total}</div>
              </div>
            </div>
            <div className="mt-6 flex justify-center items-center space-x-6">
              <div className={`px-8 py-3 rounded-full text-2xl font-bold ${
                prediction.recommendation === 'OVER' ? 'bg-green-500' :
                prediction.recommendation === 'UNDER' ? 'bg-red-500' : 'bg-yellow-500'
              }`}>
                {prediction.recommendation}
              </div>
              <div>
                <div className="text-sm opacity-80">Confidence</div>
                <div className="text-3xl font-bold">{prediction.confidence}%</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Show predicted total without betting line comparison */}
      {prediction && !prediction.betting_line && (
        <div className="bg-gradient-to-r from-gray-600 to-gray-700 rounded-lg shadow-lg p-8 mb-8 text-white">
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-2">{away_team?.abbreviation || 'Away'} @ {home_team?.abbreviation || 'Home'}</h1>
            <p className="text-lg opacity-90">{away_team?.name || 'Away Team'} at {home_team?.name || 'Home Team'}</p>
            <div className="flex justify-center items-center mt-6">
              <div>
                <div className="text-sm opacity-80 mb-1">Predicted Total</div>
                <div className="text-5xl font-bold">{prediction.predicted_total}</div>
              </div>
            </div>
            <div className="mt-6">
              <p className="text-sm opacity-80">Enter a betting line above to get a recommendation</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Comparison */}
      <div className="mb-8">
        <StatsTable
          homeStats={home_stats}
          awayStats={away_stats}
          homeTeam={home_team?.abbreviation || 'Home'}
          awayTeam={away_team?.abbreviation || 'Away'}
          homeTeamId={home_team?.id}
          awayTeamId={away_team?.id}
        />
      </div>

      {/* Prediction Breakdown */}
      {prediction && prediction.breakdown && prediction.factors && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Prediction Breakdown</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Home Projected</span>
                <span className="font-semibold text-gray-900 dark:text-white">{prediction.breakdown?.home_projected || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Away Projected</span>
                <span className="font-semibold text-gray-900 dark:text-white">{prediction.breakdown?.away_projected || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Game Pace</span>
                <span className="font-semibold text-gray-900 dark:text-white">{prediction.breakdown?.game_pace || 'N/A'}</span>
              </div>
              {prediction.betting_line && prediction.breakdown?.difference !== undefined && (
                <div className="flex justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
                  <span className="text-gray-600 dark:text-gray-400">Total Difference</span>
                  <span className={`font-bold ${prediction.breakdown.difference > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                    {prediction.breakdown.difference > 0 ? '+' : ''}{prediction.breakdown.difference}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Key Factors</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Home Team Pace</span>
                <span className="font-semibold text-gray-900 dark:text-white">{prediction.factors?.home_pace ? prediction.factors.home_pace.toFixed(1) : 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Away Team Pace</span>
                <span className="font-semibold text-gray-900 dark:text-white">{prediction.factors?.away_pace ? prediction.factors.away_pace.toFixed(1) : 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Projected Game Pace</span>
                <span className="font-semibold text-gray-900 dark:text-white">{prediction.factors?.game_pace || 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Games */}
      {(home_recent_games?.length > 0 || away_recent_games?.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {away_recent_games?.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Away Team Recent Games</h3>
              <div className="space-y-2">
                {away_recent_games.map((game, index) => (
                  <div key={index} className="flex justify-between text-sm py-2 border-b border-gray-200 dark:border-gray-700 last:border-0">
                    <span className="text-gray-600 dark:text-gray-400">{game.matchup}</span>
                    <span className="font-semibold text-gray-900 dark:text-white">Total: {game.total}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {home_recent_games?.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Home Team Recent Games</h3>
              <div className="space-y-2">
                {home_recent_games.map((game, index) => (
                  <div key={index} className="flex justify-between text-sm py-2 border-b border-gray-200 dark:border-gray-700 last:border-0">
                    <span className="text-gray-600 dark:text-gray-400">{game.matchup}</span>
                    <span className="font-semibold text-gray-900 dark:text-white">Total: {game.total}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default GamePage
