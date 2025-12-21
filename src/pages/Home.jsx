import { useState, useMemo, useEffect } from 'react'
import GameCard from '../components/GameCard'
import { useGames } from '../utils/api'

function Home() {
  const [sortBy, setSortBy] = useState('time') // time, alphabetical

  // Use React Query for automatic caching and refetching
  const {
    data,
    isLoading,
    isError,
    error,
    refetch
  } = useGames()

  // Auto-refresh every 30 minutes using React Query's refetchInterval
  useEffect(() => {
    const interval = setInterval(() => refetch(), 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [refetch])

  // Extract games and metadata from query data
  const games = data?.games || []
  const lastUpdated = data?.last_updated ? new Date(data.last_updated) : null
  const selectedDate = data?.date || null
  const dateReason = data?.date_selection_reason || null
  const todayMT = data?.today_mt || null

  // Memoize sorted games to avoid recalculation on every render
  const getSortedGames = useMemo(() => {
    return games.sort((a, b) => {
      if (!a.prediction || !b.prediction) return 0

      switch (sortBy) {
        case 'time':
          return a.game_time.localeCompare(b.game_time)
        case 'alphabetical':
          return a.away_team.abbreviation.localeCompare(b.away_team.abbreviation)
        default:
          return 0
      }
    })
  }, [games, sortBy]) // Recalculate only when these dependencies change

  if (isLoading && games.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <div className="mt-6 space-y-2">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">Analyzing matchup…</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Pulling team stats, trends, and playstyle data.</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">This usually takes 10–30 seconds.</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-4">If it takes too long, try again — cached data may load instantly.</p>
          </div>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <h3 className="text-red-800 dark:text-red-400 font-semibold mb-2">Error Loading Games</h3>
          <p className="text-red-600 dark:text-red-300">{error?.message}</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const sortedGames = getSortedGames

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header with Controls */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              {selectedDate && selectedDate !== todayMT ? `Games for ${selectedDate}` : "Today's Games"}
            </h2>
            {lastUpdated && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
            {selectedDate && selectedDate !== todayMT && (
              <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
                ℹ️ No games today (MT: {todayMT}), showing latest available slate
              </p>
            )}
          </div>
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>

        {/* Filters and Sort */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="time">Game Time</option>
              <option value="alphabetical">Alphabetical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Games Grid */}
      {sortedGames.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🏀</div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No Games Found</h3>
          <p className="text-gray-600 dark:text-gray-400">
            {dateReason === 'fallback_today_mt (empty_db)'
              ? 'The games database is empty. Please run the sync job to fetch game data.'
              : `There are no NBA games scheduled for ${selectedDate || 'this date'}`
            }
          </p>
          {dateReason === 'fallback_today_mt (empty_db)' && (
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-4">
              Sync runs automatically at 3:00 AM MT, or you can trigger it manually from the admin panel.
            </p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedGames.map((game) => (
            <GameCard key={game.game_id} game={game} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Home
