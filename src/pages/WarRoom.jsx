import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import TeamFormIndex from '../components/TeamFormIndex'
import MatchupIndicators from '../components/MatchupIndicators'
import RawStatsTable from '../components/RawStatsTable'
import VolatilityProfile from '../components/VolatilityProfile'
import MatchupDNA from '../components/MatchupDNA'
import Last5GamesPanel from '../components/Last5GamesPanel'
import AdvancedSplitsPanel from '../components/AdvancedSplitsPanel'
import MatchupSimilarityCard from '../components/MatchupSimilarityCard'
import SimilarOpponentBoxScores from '../components/SimilarOpponentBoxScores'
import { useGameDetail, useGameScoringSplits, useGameThreePointScoringSplits, useGameThreePointScoringVsPace, useGameTurnoverVsDefensePressure, useGameTurnoverVsPace } from '../utils/api'

function WarRoom() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dna') // 'dna' | 'last5' | 'splits' | 'similarity' | 'similar-opponents'

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

  // Show loading state
  if (isLoading && !gameData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <div className="mt-6 space-y-2">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">Loading War Room...</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Analyzing matchup data and team statistics.</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">This usually takes 10–20 seconds.</p>
          </div>
        </div>
      </div>
    )
  }

  // Show error state
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

      {/* War Room Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-lg shadow-lg p-6 sm:p-8 mb-8 text-white">
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

        {/* Raw Stats Table */}
        <RawStatsTable
          homeTeam={home_team}
          awayTeam={away_team}
          homeStats={home_stats}
          awayStats={away_stats}
          homeRecentGames={home_recent_games}
          awayRecentGames={away_recent_games}
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


        {/* Tab Navigation */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap justify-center gap-2 sm:gap-3 mb-6">
            <button
              onClick={() => setActiveTab('dna')}
              className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                activeTab === 'dna'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              Matchup DNA
            </button>
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
            {prediction?.similarity && (
              <button
                onClick={() => setActiveTab('similarity')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'similarity'
                    ? 'bg-primary-600 text-white shadow-lg'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Similarity
              </button>
            )}
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
          </div>

          {/* Tab Content */}
          <div className="mt-6">
            {activeTab === 'dna' && (
              <MatchupDNA
                matchupSummary={matchup_summary}
                homeTeam={home_team}
                awayTeam={away_team}
              />
            )}

            {activeTab === 'last5' && (
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
                splitsLoading={splitsLoading}
                threePtSplitsLoading={threePtSplitsLoading}
                threePtVsPaceLoading={threePtVsPaceLoading}
                turnoverVsDefenseLoading={turnoverVsDefenseLoading}
                turnoverVsPaceLoading={turnoverVsPaceLoading}
                onShowGlossary={() => {}}
              />
            )}

            {activeTab === 'similarity' && prediction?.similarity && (
              <MatchupSimilarityCard
                prediction={prediction}
                homeTeam={home_team?.abbreviation || 'Home'}
                awayTeam={away_team?.abbreviation || 'Away'}
              />
            )}

            {activeTab === 'similar-opponents' && (
              <SimilarOpponentBoxScores gameId={gameId} />
            )}
          </div>
        </div>

        {/* View Full Matchup Summary Button */}
        {matchup_summary && matchup_summary.matchup_dna_summary && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8 border border-gray-200 dark:border-gray-700">
            <div className="text-center">
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
                Full Matchup Analysis Available
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                View our comprehensive AI-generated matchup breakdown
              </p>
              <button
                onClick={() => navigate(`/game/${gameId}/summary`)}
                className="inline-flex items-center justify-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-lg font-semibold transition-colors shadow-md"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                View Full Matchup Summary
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default WarRoom
