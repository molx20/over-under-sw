import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TeamFormIndex from '../components/TeamFormIndex'
import MatchupIndicators from '../components/MatchupIndicators'
import EmptyPossessionsGauge from '../components/EmptyPossessionsGauge'
import VolatilityProfile from '../components/VolatilityProfile'
import Last5GamesPanel from '../components/Last5GamesPanel'
import AdvancedSplitsPanel from '../components/AdvancedSplitsPanel'
import SimilarOpponentBoxScores from '../components/SimilarOpponentBoxScores'
import ScoringMixPanel from '../components/ScoringMixPanel'
import MarkdownRenderer from '../components/MarkdownRenderer'
import { useGameDetail, useGameScoringSplits, useGameThreePointScoringSplits, useGameThreePointScoringVsPace, useGameTurnoverVsDefensePressure, useGameTurnoverVsPace, useGameAssistsVsDefense, useGameAssistsVsPace, useGameScoringMix, useFullMatchupSummaryWriteup } from '../utils/api'

function WarRoom() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('last5') // 'last5' | 'splits' | 'similar-opponents' | 'scoring-mix'
  const [showFullSummary, setShowFullSummary] = useState(false)

  // Fetch game data
  const {
    data: gameData,
    isLoading,
    isFetching,
    isError,
    error,
    refetch
  } = useGameDetail(gameId, null)

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

  // Fetch scoring mix for both teams
  const {
    data: scoringMixData,
    isLoading: scoringMixLoading,
  } = useGameScoringMix(gameId, '2025-26')

  // Fetch full matchup summary writeup
  const {
    data: matchupWriteup,
    isLoading: writeupLoading,
  } = useFullMatchupSummaryWriteup(gameId)

  // Show loading state
  if (isLoading && !gameData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mobile-container py-8">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <div className="mt-6 space-y-2">
              <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">Loading War Room...</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Analyzing matchup data and team statistics.</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">This usually takes 10–20 seconds.</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Show error state
  if (isError || !gameData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mobile-container py-8">
          <button
            onClick={() => navigate('/')}
            className="mb-4 min-h-[44px] text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
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
              className="px-4 py-2 min-h-[44px] bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const { prediction, home_stats, away_stats, home_recent_games, away_recent_games, home_team, away_team, matchup_summary, scoring_environment, empty_possessions } = gameData

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mobile-container py-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 min-h-[44px] text-primary-600 dark:text-primary-400 hover:underline flex items-center space-x-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span>Back to Games</span>
      </button>

      {/* War Room Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl shadow-lg p-6 mb-6 text-white">
        <div className="text-center">
          {/* Tag */}
          <div className="mb-4">
            <span className="inline-block px-4 py-2 bg-white/20 backdrop-blur-sm rounded-full text-sm font-semibold">
              MATCHUP WAR ROOM
            </span>
          </div>

          {/* Game Title */}
          <h1 className="text-3xl sm:text-4xl font-bold mb-2">
            {away_team?.abbreviation || 'AWAY'} @ {home_team?.abbreviation || 'HOME'}
          </h1>

          {/* Subtext */}
          <p className="text-lg opacity-90 mb-6">
            {away_team?.name || 'Away Team'} at {home_team?.name || 'Home Team'}
          </p>

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

      {/* War Room Content */}
      <div className="space-y-8">
        {/* Team Form Index */}
        <TeamFormIndex
          homeTeam={home_team}
          awayTeam={away_team}
          homeStats={home_stats}
          awayStats={away_stats}
          homeRecentGames={home_recent_games}
          awayRecentGames={away_recent_games}
        />

        {/* Matchup Indicators */}
        <MatchupIndicators
          homeTeam={home_team}
          awayTeam={away_team}
          homeStats={home_stats}
          awayStats={away_stats}
        />

        {/* Empty Possessions Analysis */}
        <EmptyPossessionsGauge
          homeTeam={home_team}
          awayTeam={away_team}
          emptyPossessionsData={empty_possessions}
        />

        {/* Volatility Profile */}
        <VolatilityProfile
          homeTeam={home_team}
          awayTeam={away_team}
          homeRecentGames={home_recent_games}
          awayRecentGames={away_recent_games}
          homeStats={home_stats}
          awayStats={away_stats}
        />


        {/* Full Matchup Summary Button */}
        <div className="flex justify-center">
          <button
            onClick={() => setShowFullSummary(true)}
            className="px-6 py-3 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold rounded-lg shadow-lg transition-all transform hover:scale-105 flex items-center space-x-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>View Full Matchup Summary</span>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap justify-center gap-2 sm:gap-3 mb-6">
            <button
              onClick={() => setActiveTab('last5')}
              className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                activeTab === 'last5'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              Last 5 Games
            </button>
            <button
              onClick={() => setActiveTab('splits')}
              className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                activeTab === 'splits'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              Advanced Splits
            </button>
            <button
              onClick={() => setActiveTab('similar-opponents')}
              className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                activeTab === 'similar-opponents'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              Similar Opponents
            </button>
            <button
              onClick={() => setActiveTab('scoring-mix')}
              className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                activeTab === 'scoring-mix'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              Scoring Mix
            </button>
          </div>

          {/* Tab Content (DATA ONLY MODE) */}
          <div className="mt-6">
            {activeTab === 'last5' && prediction && (
              <Last5GamesPanel
                prediction={prediction}
                homeTeam={home_team}
                awayTeam={away_team}
              />
            )}

            {activeTab === 'splits' && (
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
                onShowGlossary={() => {}}
              />
            )}

            {activeTab === 'similar-opponents' && (
              <SimilarOpponentBoxScores gameId={gameId} />
            )}

            {activeTab === 'scoring-mix' && (
              <ScoringMixPanel
                scoringMixData={scoringMixData}
                homeTeam={home_team}
                awayTeam={away_team}
                isLoading={scoringMixLoading}
              />
            )}
          </div>
        </div>

      </div>

      {/* Full Matchup Summary Modal */}
      {showFullSummary && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-start justify-center p-2 sm:p-4"
             onClick={() => setShowFullSummary(false)}>
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-4xl w-full my-4 sm:my-8"
               onClick={(e) => e.stopPropagation()}>
            {/* Sticky Header - Compact on mobile */}
            <div className="sticky top-0 z-10 bg-gradient-to-r from-primary-600 to-primary-700 px-4 sm:px-6 py-3 sm:py-4 rounded-t-lg">
              <div className="flex items-center justify-between">
                <h2 className="text-lg sm:text-2xl font-bold text-white flex items-center">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6 mr-2 sm:mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="hidden sm:inline">Full Matchup Summary</span>
                  <span className="sm:hidden">Matchup Summary</span>
                </h2>
                <button
                  onClick={() => setShowFullSummary(false)}
                  className="text-white hover:text-gray-200 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Close modal"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Scrollable Content - AI Write-up Only */}
            <div className="px-4 sm:px-6 py-4 sm:py-8 max-h-[75vh] sm:max-h-[80vh] overflow-y-auto">

              {/* AI-Generated Matchup Summary Write-up */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 rounded-lg p-4 sm:p-6 border border-blue-200 dark:border-gray-700">
                <div className="flex items-center mb-3 sm:mb-4">
                  <svg className="w-5 h-5 mr-2 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">AI Matchup Breakdown</h3>
                </div>
                {writeupLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span className="ml-3 text-sm sm:text-base text-gray-600 dark:text-gray-400">Generating analysis...</span>
                  </div>
                ) : (
                  <MarkdownRenderer content={matchupWriteup} />
                )}
              </div>

            </div>

            {/* Sticky Footer - Full-width button on mobile */}
            <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-900 px-4 sm:px-6 py-3 sm:py-4 rounded-b-lg border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowFullSummary(false)}
                className="w-full sm:w-auto sm:ml-auto sm:block px-6 py-2.5 min-h-[48px] bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}

export default WarRoom
