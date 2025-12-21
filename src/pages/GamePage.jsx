import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import StatsTable from '../components/StatsTable'
import MatchupDNA from '../components/MatchupDNA'
import PredictionPanel from '../components/PredictionPanel'
import Last5GamesPanel from '../components/Last5GamesPanel'
import AdvancedSplitsPanel from '../components/AdvancedSplitsPanel'
import MatchupSimilarityCard from '../components/MatchupSimilarityCard'
import SimilarOpponentBoxScores from '../components/SimilarOpponentBoxScores'
import IdentityGlossary from '../components/IdentityGlossary'
import PostGameReviewModal from '../components/PostGameReviewModal'
import { useGameDetail, useGameScoringSplits, useGameThreePointScoringSplits, useGameThreePointScoringVsPace, useGameTurnoverVsDefensePressure, useGameTurnoverVsPace, useGameAssistsVsDefense, useGameAssistsVsPace } from '../utils/api'

function GamePage() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const [bettingLine, setBettingLine] = useState('')
  const [customBettingLine, setCustomBettingLine] = useState(null)
  const [showGlossary, setShowGlossary] = useState(false)
  const [showReviewModal, setShowReviewModal] = useState(false)

  // Tab state for main content sections
  const [activeTab, setActiveTab] = useState('prediction') // 'prediction' | 'dna' | 'last5' | 'splits'

  // Stats table collapse state (mobile only)
  const [statsCollapsed, setStatsCollapsed] = useState(false)

  // Use React Query for automatic caching and loading states
  const {
    data: gameData,
    isLoading,
    isFetching,
    isError,
    error,
    refetch
  } = useGameDetail(gameId, customBettingLine)

  // Fetch scoring splits for both teams
  const {
    data: scoringSplitsData,
    isLoading: splitsLoading,
  } = useGameScoringSplits(gameId, '2025-26')

  // Fetch 3PT scoring splits for both teams
  const {
    data: threePtSplitsData,
    isLoading: threePtSplitsLoading,
  } = useGameThreePointScoringSplits(gameId, '2025-26')

  // Fetch 3PT scoring vs pace for both teams
  const {
    data: threePtVsPaceData,
    isLoading: threePtVsPaceLoading,
  } = useGameThreePointScoringVsPace(gameId, '2025-26')

  // Fetch turnover vs defense pressure for both teams
  const {
    data: turnoverVsDefenseData,
    isLoading: turnoverVsDefenseLoading,
  } = useGameTurnoverVsDefensePressure(gameId, '2025-26')

  // Fetch turnover vs pace for both teams
  const {
    data: turnoverVsPaceData,
    isLoading: turnoverVsPaceLoading,
  } = useGameTurnoverVsPace(gameId, '2025-26')

  // Fetch assists vs defense for both teams
  const {
    data: assistsVsDefenseData,
    isLoading: assistsVsDefenseLoading,
  } = useGameAssistsVsDefense(gameId, '2025-26')

  // Fetch assists vs pace for both teams
  const {
    data: assistsVsPaceData,
    isLoading: assistsVsPaceLoading,
  } = useGameAssistsVsPace(gameId, '2025-26')

  // DIAGNOSTIC: Log assists hook results
  console.log('[GamePage] gameId:', gameId)
  console.log('[GamePage] assistsVsDefenseData from hook:', assistsVsDefenseData)
  console.log('[GamePage] assistsVsDefenseLoading from hook:', assistsVsDefenseLoading)
  console.log('[GamePage] assistsVsPaceData from hook:', assistsVsPaceData)
  console.log('[GamePage] assistsVsPaceLoading from hook:', assistsVsPaceLoading)

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
          <div className="mt-6 space-y-2">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">Analyzing matchup…</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Reading team stats, trends, and playstyle profiles.</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">This usually takes 10–20 seconds.</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-4">If it takes longer, reload — cached data may load instantly.</p>
          </div>
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

  const { prediction, home_stats, away_stats, home_recent_games, away_recent_games, home_team, away_team, matchup_summary, scoring_environment } = gameData

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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6 mb-6">
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">Enter Betting Line</h3>
        <div className="flex flex-col sm:flex-row sm:items-end space-y-3 sm:space-y-0 sm:space-x-4">
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
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white text-base"
            />
          </div>
          <button
            onClick={handleCalculatePrediction}
            disabled={isFetching}
            className="w-full sm:w-auto px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {isFetching && (
              <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            )}
            <span>{isFetching ? 'Calculating...' : 'Calculate Prediction'}</span>
          </button>
        </div>
      </div>

      {/* Game Matchup Header with Scoring Environment */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg shadow-lg p-4 sm:p-6 mb-6 text-white">
        <div className="text-center">
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold mb-1 sm:mb-2">{away_team?.abbreviation || 'Away'} @ {home_team?.abbreviation || 'Home'}</h1>
          <p className="text-sm sm:text-base opacity-90 mb-4">{away_team?.name || 'Away Team'} at {home_team?.name || 'Home Team'}</p>

          {/* Scoring Environment Label */}
          {scoring_environment && (
            <div className="inline-block bg-white/20 backdrop-blur-sm rounded-lg px-6 py-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-white/80 mb-1">
                Scoring Environment
              </div>
              <div className={`text-2xl font-bold ${
                scoring_environment === 'HIGH' ? 'text-green-300' :
                scoring_environment === 'LOW' ? 'text-red-300' :
                'text-gray-300'
              }`}>
                {scoring_environment}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Matchup Summary Section (shows after betting line entered) */}
      {prediction && prediction.betting_line && matchup_summary && (
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg shadow-lg p-4 sm:p-6 md:p-8 mb-6 sm:mb-8 text-white">
          <div className="text-center">

            {/* Matchup Summary Section */}
            <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-lg p-4 sm:p-6">
              <div className="flex items-center justify-center mb-3">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-base sm:text-lg font-semibold">Matchup Summary</h3>
              </div>

              {matchup_summary && matchup_summary.matchup_dna_summary ? (
                <p className="text-sm sm:text-base leading-relaxed text-white/90 text-left max-w-4xl mx-auto">
                  {matchup_summary.matchup_dna_summary.text}
                </p>
              ) : isFetching ? (
                <div className="flex flex-col items-center space-y-2">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                  <p className="text-sm text-white/80">Building matchup summary…</p>
                </div>
              ) : (
                <p className="text-sm text-white/70 italic">
                  Matchup summary not available for this game yet.
                </p>
              )}
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="mt-6 sm:mt-8 pt-6 border-t border-white/20">
            <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
              <button
                onClick={() => setActiveTab('prediction')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'prediction'
                    ? 'bg-white text-primary-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Prediction
              </button>
              <button
                onClick={() => setActiveTab('dna')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'dna'
                    ? 'bg-white text-primary-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Matchup DNA
              </button>
              <button
                onClick={() => setActiveTab('last5')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'last5'
                    ? 'bg-white text-primary-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Last 5 Games
              </button>
              <button
                onClick={() => setActiveTab('splits')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'splits'
                    ? 'bg-white text-primary-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Advanced Splits
              </button>
              {prediction.similarity && (
                <button
                  onClick={() => setActiveTab('similarity')}
                  className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                    activeTab === 'similarity'
                      ? 'bg-white text-primary-700 shadow-lg'
                      : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  Similarity
                </button>
              )}
              <button
                onClick={() => setActiveTab('similar-opponents')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'similar-opponents'
                    ? 'bg-white text-primary-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Similar Opponents
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Show predicted total without betting line comparison */}
      {prediction && !prediction.betting_line && (
        <div className="bg-gradient-to-r from-gray-600 to-gray-700 rounded-lg shadow-lg p-4 sm:p-6 md:p-8 mb-6 sm:mb-8 text-white">
          <div className="text-center">
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold mb-1 sm:mb-2">{away_team?.abbreviation || 'Away'} @ {home_team?.abbreviation || 'Home'}</h1>
            <p className="text-sm sm:text-base md:text-lg opacity-90">{away_team?.name || 'Away Team'} at {home_team?.name || 'Home Team'}</p>
            <div className="flex justify-center items-center mt-4 sm:mt-6">
              <div>
                <div className="text-xs sm:text-sm opacity-80 mb-1">Predicted Total</div>
                <div className="text-4xl sm:text-5xl font-bold">{prediction.predicted_total}</div>
              </div>
            </div>
            <div className="mt-4 sm:mt-6 space-y-2">
              <p className="text-xs sm:text-sm opacity-80">Enter a betting line above to get a recommendation</p>
              <button
                onClick={() => setShowReviewModal(true)}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 mx-auto"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Upload Final Score
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="mt-6 sm:mt-8 pt-6 border-t border-white/20">
            <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
              <button
                onClick={() => setActiveTab('prediction')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'prediction'
                    ? 'bg-white text-gray-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Prediction
              </button>
              <button
                onClick={() => setActiveTab('dna')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'dna'
                    ? 'bg-white text-gray-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Matchup DNA
              </button>
              <button
                onClick={() => setActiveTab('last5')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'last5'
                    ? 'bg-white text-gray-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Last 5 Games
              </button>
              <button
                onClick={() => setActiveTab('splits')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'splits'
                    ? 'bg-white text-gray-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Advanced Splits
              </button>
              {prediction.similarity && (
                <button
                  onClick={() => setActiveTab('similarity')}
                  className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                    activeTab === 'similarity'
                      ? 'bg-white text-gray-700 shadow-lg'
                      : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  Similarity
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stats Comparison - Collapsible on mobile */}
      <div className="mb-8">
        {/* Mobile toggle button */}
        <button
          onClick={() => setStatsCollapsed(!statsCollapsed)}
          className="md:hidden w-full flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 mb-3 text-gray-900 dark:text-white font-semibold"
        >
          <span>Team Statistics Comparison</span>
          <svg
            className={`w-5 h-5 transition-transform ${statsCollapsed ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Stats table - hidden on mobile when collapsed, always visible on desktop */}
        <div className={`${statsCollapsed ? 'hidden md:block' : 'block'}`}>
          <StatsTable
            homeStats={home_stats}
            awayStats={away_stats}
            homeTeam={home_team?.abbreviation || 'Home'}
            awayTeam={away_team?.abbreviation || 'Away'}
            homeTeamId={home_team?.id}
            awayTeamId={away_team?.id}
          />
        </div>
      </div>

      {/* Tab Content Panels */}
      {prediction && (
        <>
          {/* Prediction Tab */}
          {activeTab === 'prediction' && (
            <div className="mb-6 sm:mb-8">
              <PredictionPanel
                prediction={prediction}
                homeTeam={home_team}
                awayTeam={away_team}
                homeStats={home_stats}
                awayStats={away_stats}
              />
            </div>
          )}

          {/* Matchup DNA Tab */}
          {activeTab === 'dna' && (
            <div className="mb-6 sm:mb-8">
              <MatchupDNA
                matchupSummary={matchup_summary}
                homeTeam={home_team}
                awayTeam={away_team}
              />
            </div>
          )}

          {/* Last 5 Games Tab */}
          {activeTab === 'last5' && (
            <div className="mb-6 sm:mb-8">
              <Last5GamesPanel
                prediction={prediction}
                homeTeam={home_team}
                awayTeam={away_team}
              />
            </div>
          )}

          {/* Advanced Splits Tab */}
          {activeTab === 'splits' && (
            <div className="mb-6 sm:mb-8">
              <AdvancedSplitsPanel
                scoringSplitsData={scoringSplitsData}
                threePtSplitsData={threePtSplitsData}
                threePtVsPaceData={threePtVsPaceData}
                turnoverVsDefenseData={turnoverVsDefenseData}
                turnoverVsPaceData={turnoverVsPaceData}
                assistsVsDefenseData={assistsVsDefenseData}
                assistsVsPaceData={assistsVsPaceData}
                splitsLoading={splitsLoading}
                threePtSplitsLoading={threePtSplitsLoading}
                threePtVsPaceLoading={threePtVsPaceLoading}
                turnoverVsDefenseLoading={turnoverVsDefenseLoading}
                turnoverVsPaceLoading={turnoverVsPaceLoading}
                assistsVsDefenseLoading={assistsVsDefenseLoading}
                assistsVsPaceLoading={assistsVsPaceLoading}
                onShowGlossary={() => setShowGlossary(true)}
              />
            </div>
          )}

          {/* Similarity Tab */}
          {activeTab === 'similarity' && prediction.similarity && (
            <div className="mb-6 sm:mb-8">
              <MatchupSimilarityCard
                prediction={prediction}
                homeTeam={home_team?.abbreviation || 'Home'}
                awayTeam={away_team?.abbreviation || 'Away'}
              />
            </div>
          )}

          {/* Similar Opponents Tab */}
          {activeTab === 'similar-opponents' && (
            <div className="mb-6 sm:mb-8">
              <SimilarOpponentBoxScores gameId={gameId} />
            </div>
          )}
        </>
      )}


      {/* Identity Glossary Modal */}
      <IdentityGlossary
        isOpen={showGlossary}
        onClose={() => setShowGlossary(false)}
      />

      <PostGameReviewModal
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        gameData={gameData ? {
          game_id: gameId,
          home_team: home_team?.name || 'Home Team',
          away_team: away_team?.name || 'Away Team',
          game_date: new Date().toISOString().split('T')[0], // Use today's date as fallback
          prediction: {
            ...prediction,
            // Override with custom betting line if user entered one
            betting_line: customBettingLine || prediction?.betting_line
          }
        } : null}
      />
    </div>
  )
}

export default GamePage
