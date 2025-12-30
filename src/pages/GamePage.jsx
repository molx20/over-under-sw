import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Last5GamesPanel from '../components/Last5GamesPanel'
import AdvancedSplitsPanel from '../components/AdvancedSplitsPanel'
import DecisionCard from '../components/DecisionCard'
import TeamContextTab from '../components/TeamContextTab'
import { makeDecision } from '../utils/decisionEngine'
import { useGameDetail, useGameScoringSplits, useGameThreePointScoringSplits, useGameThreePointScoringVsPace, useGameTurnoverVsDefensePressure, useGameTurnoverVsPace, useGameAssistsVsDefense, useGameAssistsVsPace } from '../utils/api'

function GamePage() {
  console.log('[GamePage] ===== COMPONENT RENDERING =====')
  const { gameId } = useParams()
  console.log('[GamePage] gameId from useParams:', gameId)
  const navigate = useNavigate()

  // Tab state for main content sections (DATA ONLY MODE)
  const [activeTab, setActiveTab] = useState('last5') // 'last5' | 'splits' | 'similar-opponents'

  // Use React Query for automatic caching and loading states
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

  // DIAGNOSTIC: Log BEFORE assists hooks
  console.log('[GamePage] BEFORE assists hooks - gameId:', gameId)

  // Fetch assists vs defense for both teams
  const {
    data: assistsVsDefenseData,
    isLoading: assistsVsDefenseLoading,
  } = useGameAssistsVsDefense(gameId, '2025-26')

  console.log('[GamePage] AFTER useGameAssistsVsDefense')

  // Fetch assists vs pace for both teams
  const {
    data: assistsVsPaceData,
    isLoading: assistsVsPaceLoading,
  } = useGameAssistsVsPace(gameId, '2025-26')

  console.log('[GamePage] AFTER useGameAssistsVsPace')

  // DIAGNOSTIC: Log assists hook results
  console.log('[GamePage] assistsVsDefenseData from hook:', assistsVsDefenseData)
  console.log('[GamePage] assistsVsDefenseLoading from hook:', assistsVsDefenseLoading)
  console.log('[GamePage] assistsVsPaceData from hook:', assistsVsPaceData)
  console.log('[GamePage] assistsVsPaceLoading from hook:', assistsVsPaceLoading)

  // Show loading state only on initial load (no cached data)
  if (isLoading && !gameData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          <div className="mt-6 space-y-2">
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">Loading matchup data…</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Fetching team stats, trends, and recent games.</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">This usually takes 5–10 seconds.</p>
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

  // Calculate decision values (without useMemo to avoid infinite render with React Query)
  let decision = null
  let drivers = null
  let archetype = null
  let volatility = null
  let marginRisk = null

  if (home_stats && away_stats) {
    // Calculate combined FT points
    const homeFT = (home_stats.fta_per_game || 0) * ((home_stats.ft_pct || 0) / 100)
    const awayFT = (away_stats.fta_per_game || 0) * ((away_stats.ft_pct || 0) / 100)
    const ftPoints = homeFT + awayFT

    // Calculate combined paint points
    const paintPoints = (home_stats.paint_pts_per_game || 0) + (away_stats.paint_pts_per_game || 0)

    // Calculate combined eFG% (weighted by FGA)
    const homeFGM = home_stats.fgm || 0
    const homeFG3M = home_stats.fg3m || 0
    const homeFGA = home_stats.fga || 1
    const awayFGM = away_stats.fgm || 0
    const awayFG3M = away_stats.fg3m || 0
    const awayFGA = away_stats.fga || 1

    const homeEFG = ((homeFGM + 0.5 * homeFG3M) / homeFGA) * 100
    const awayEFG = ((awayFGM + 0.5 * awayFG3M) / awayFGA) * 100
    const combinedEFG = (homeEFG * homeFGA + awayEFG * awayFGA) / (homeFGA + awayFGA)

    // Build drivers object
    drivers = {
      ftPoints: {
        value: Math.round(ftPoints),
        status: ftPoints >= 38 ? 'green' : ftPoints < 33 ? 'red' : 'yellow',
        target: '38+'
      },
      paintPoints: {
        value: Math.round(paintPoints),
        status: paintPoints >= 68 ? 'green' : paintPoints < 60 ? 'red' : 'yellow',
        target: '68+'
      },
      efg: {
        value: Math.round(combinedEFG * 10) / 10,
        status: combinedEFG >= 59 ? 'green' : combinedEFG < 53 ? 'red' : 'yellow',
        target: '59%+'
      }
    }

    // Get archetype data (transform new format to old format for DecisionCard)
    const homeArchetypes = gameData.home_archetypes
    archetype = homeArchetypes ? {
      cluster_name: homeArchetypes.season_offensive?.name || 'Balanced',
      cluster_description: homeArchetypes.season_offensive?.description || '',
      confidence: 'medium',
      sample_size: 20
    } : {}

    volatility = {
      index: gameData.combined_volatility_index || 5.0,
      label: gameData.volatility_label || 'Medium'
    }
    marginRisk = gameData.margin_risk || { label: 'Competitive' }

    // Make decision
    decision = makeDecision(drivers, archetype, volatility, marginRisk)
  }

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

      {/* Decision Card */}
      {decision && drivers && (
        <div className="mb-6">
          <DecisionCard
            decision={decision}
            drivers={drivers}
            archetype={archetype}
            marginRisk={marginRisk}
            volatility={volatility}
          />
        </div>
      )}

      {/* Game Matchup Header with Scoring Environment (DATA ONLY MODE) */}
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

          {/* Matchup Summary */}
          {matchup_summary && matchup_summary.matchup_dna_summary && (
            <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-lg p-4 sm:p-6">
              <div className="flex items-center justify-center mb-3">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-base sm:text-lg font-semibold">Matchup Summary</h3>
              </div>
              <p className="text-sm sm:text-base leading-relaxed text-white/90 text-left max-w-4xl mx-auto">
                {matchup_summary.matchup_dna_summary.text}
              </p>
            </div>
          )}

          {/* Tab Navigation */}
          <div className="mt-6 sm:mt-8 pt-6 border-t border-white/20">
            <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
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
              <button
                onClick={() => setActiveTab('team-context')}
                className={`px-4 sm:px-6 py-2 rounded-lg font-medium transition-all text-sm sm:text-base ${
                  activeTab === 'team-context'
                    ? 'bg-white text-primary-700 shadow-lg'
                    : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                Team Context
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Content Panels (DATA ONLY MODE) */}
      {/* Last 5 Games Tab */}
      {activeTab === 'last5' && prediction && (
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
            homeArchetypes={gameData.home_archetypes}
            awayArchetypes={gameData.away_archetypes}
          />
        </div>
      )}

      {/* Team Context Tab */}
      {activeTab === 'team-context' && (
        <div className="mb-6 sm:mb-8">
          <TeamContextTab
            homeTeam={home_team}
            awayTeam={away_team}
            homeStats={home_stats}
            awayStats={away_stats}
            homeRecentGames={home_recent_games}
            awayRecentGames={away_recent_games}
            emptyPossessionsData={gameData.empty_possessions}
          />
        </div>
      )}

      {/* Debug watermark - shows commit hash in footer (dev mode only) */}
      {import.meta.env.MODE !== 'production' && (
        <div className="fixed bottom-0 right-0 text-xs text-gray-400 dark:text-gray-600 p-2 opacity-50 bg-gray-100 dark:bg-gray-800 rounded-tl">
          Build: {import.meta.env.VITE_GIT_COMMIT_HASH || 'dev-local'} | {new Date().toISOString().split('T')[0]}
        </div>
      )}
    </div>
  )
}

export default GamePage
