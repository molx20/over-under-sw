import { useState, useMemo, useEffect } from 'react'
import GameCard from '../components/GameCard'
import { useGames } from '../utils/api'

function Home() {
  const [sortBy, setSortBy] = useState('time')
  const [selectedDate, setSelectedDate] = useState(null)

  const {
    data,
    isLoading,
    isError,
    error,
    refetch
  } = useGames(selectedDate)

  useEffect(() => {
    const interval = setInterval(() => refetch(), 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [refetch])

  const games = data?.games || []
  const lastUpdated = data?.last_updated ? new Date(data.last_updated) : null
  const apiSelectedDate = data?.date || null
  const dateReason = data?.date_selection_reason || null
  const todayMT = data?.today_mt || null

  const getSortedGames = useMemo(() => {
    return games.sort((a, b) => {
      switch (sortBy) {
        case 'time':
          const timeA = a.game_time || a.game_date || ''
          const timeB = b.game_time || b.game_date || ''
          return timeB.localeCompare(timeA) // Reverse to show earliest games first
        case 'alphabetical':
          const teamA = a.away_team?.abbreviation || a.away_team_name || ''
          const teamB = b.away_team?.abbreviation || b.away_team_name || ''
          return teamA.localeCompare(teamB)
        default:
          return 0
      }
    })
  }, [games, sortBy])

  // Loading state
  if (isLoading && games.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mobile-container py-12">
          <div className="flex flex-col items-center justify-center space-y-6">
            <div className="w-16 h-16 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
            <div className="text-center space-y-2">
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Loading games...
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs mx-auto">
                Analyzing matchups and pulling latest data
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mobile-container py-8">
          <div className="bg-red-50 dark:bg-red-900/20 rounded-2xl p-6 border-2 border-red-200 dark:border-red-800">
            <div className="text-center space-y-4">
              <div className="text-5xl">⚠️</div>
              <h3 className="text-lg font-bold text-red-900 dark:text-red-100">
                Couldn't load games
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300">
                {error?.message}
              </p>
              <button
                onClick={() => refetch()}
                className="btn-mobile bg-red-600 text-white hover:bg-red-700 active:bg-red-800"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const sortedGames = getSortedGames

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sticky Header */}
      <div className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="mobile-container py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                {apiSelectedDate && apiSelectedDate !== todayMT ? apiSelectedDate : "Today"}
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {sortedGames.length} {sortedGames.length === 1 ? 'game' : 'games'}
                {lastUpdated && ` • Updated ${lastUpdated.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`}
              </p>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="flex items-center justify-center w-11 h-11 rounded-full bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 transition-colors"
              aria-label="Refresh games"
            >
              <svg
                className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div className="mobile-container py-6">
        {/* Date/Sort Controls - Stacked Vertically */}
        <div className="space-y-3 mb-6">
          {/* Date Picker */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Select Date
            </label>
            <div className="flex gap-2">
              <input
                type="date"
                value={selectedDate || ''}
                onChange={(e) => setSelectedDate(e.target.value || null)}
                className="flex-1 min-h-[44px] px-4 py-2.5 text-base border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
              />
              {selectedDate && (
                <button
                  onClick={() => setSelectedDate(null)}
                  className="min-h-[44px] px-4 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-gray-600 active:bg-gray-400 font-medium transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Sort Dropdown */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full min-h-[44px] px-4 py-2.5 text-base border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
            >
              <option value="time">Game Time</option>
              <option value="alphabetical">Alphabetical</option>
            </select>
          </div>
        </div>

        {/* Warning Message */}
        {apiSelectedDate && apiSelectedDate !== todayMT && (
          <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-400 rounded-lg">
            <div className="flex items-start space-x-3">
              <span className="text-xl">ℹ️</span>
              <div>
                <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                  No games today
                </p>
                <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                  Showing latest available games (MT: {todayMT})
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Games List - Single Column */}
        {sortedGames.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🏀</div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              No games found
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 max-w-xs mx-auto">
              {dateReason === 'fallback_today_mt (empty_db)'
                ? 'Database is empty. Run sync to fetch game data.'
                : `No NBA games scheduled for ${apiSelectedDate || 'this date'}`
              }
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedGames.map((game) => (
              <GameCard key={game.game_id} game={game} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Home
