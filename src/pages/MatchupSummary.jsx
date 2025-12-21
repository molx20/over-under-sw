import { useParams, useNavigate } from 'react-router-dom'
import { useGameDetail } from '../utils/api'

function MatchupSummary() {
  const { gameId } = useParams()
  const navigate = useNavigate()

  // Fetch game data
  const {
    data: gameData,
    isLoading,
    isError,
    error,
    refetch
  } = useGameDetail(gameId, null)

  // Show loading state
  if (isLoading && !gameData) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <div className="mt-6 space-y-2">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">Loading Matchup Summary...</p>
          </div>
        </div>
      </div>
    )
  }

  // Show error state
  if (isError || !gameData) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={() => navigate(`/game/${gameId}`)}
          className="mb-4 text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to War Room</span>
        </button>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <h3 className="text-red-800 dark:text-red-400 font-semibold mb-2">Error Loading Summary</h3>
          <p className="text-red-600 dark:text-red-300 mb-4">{error?.message || 'Failed to load matchup summary'}</p>
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

  const { home_team, away_team, matchup_summary } = gameData

  // Check if matchup summary exists
  if (!matchup_summary || !matchup_summary.matchup_dna_summary) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <button
          onClick={() => navigate(`/game/${gameId}`)}
          className="mb-4 text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to War Room</span>
        </button>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <h3 className="text-yellow-800 dark:text-yellow-400 font-semibold mb-2">Summary Not Available</h3>
          <p className="text-yellow-600 dark:text-yellow-300">
            The AI-generated matchup summary is not available for this game yet.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <button
        onClick={() => navigate(`/game/${gameId}`)}
        className="mb-6 text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span>Back to War Room</span>
      </button>

      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg shadow-lg p-6 sm:p-8 mb-8 text-white">
        <div className="text-center">
          <div className="mb-4">
            <span className="inline-block px-4 py-2 bg-white/20 backdrop-blur-sm rounded-full text-sm font-semibold">
              AI MATCHUP ANALYSIS
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mb-2">
            {away_team?.abbreviation || 'AWAY'} @ {home_team?.abbreviation || 'HOME'}
          </h1>
          <p className="text-lg opacity-90">
            {away_team?.name || 'Away Team'} at {home_team?.name || 'Home Team'}
          </p>
        </div>
      </div>

      {/* Matchup Summary Content */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 sm:p-8 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-3 mb-6">
          <svg className="w-6 h-6 text-primary-600 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Full Matchup Summary
          </h2>
        </div>

        <div className="prose prose-gray dark:prose-invert max-w-none">
          <div className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
            {matchup_summary.matchup_dna_summary.content || matchup_summary.matchup_dna_summary.text || "Writeup unavailable (missing data)."}
          </div>
        </div>

        {/* Metadata if available */}
        {matchup_summary.matchup_dna_summary.generated_at && (
          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Generated on {new Date(matchup_summary.matchup_dna_summary.generated_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>

      {/* Back Button (Bottom) */}
      <div className="mt-8 text-center">
        <button
          onClick={() => navigate(`/game/${gameId}`)}
          className="inline-flex items-center justify-center px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-semibold transition-colors"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Return to War Room
        </button>
      </div>
    </div>
  )
}

export default MatchupSummary
