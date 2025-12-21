import { useState } from 'react'
import IdentityTags from './IdentityTags'
import ScoringSpitsChart from './ScoringSpitsChart'
import ScoringVsPaceChart from './ScoringVsPaceChart'
import ThreePointScoringVsDefenseChart from './ThreePointScoringVsDefenseChart'
import ThreePointScoringVsPaceChart from './ThreePointScoringVsPaceChart'
import TurnoverVsDefensePressureChart from './TurnoverVsDefensePressureChart'
import TurnoverVsPaceChart from './TurnoverVsPaceChart'
import AssistsVsDefenseChart from './AssistsVsDefenseChart'
import AssistsVsPaceChart from './AssistsVsPaceChart'
import { EXPLANATION_TEXT } from '../utils/explanationText'

/**
 * AdvancedSplitsPanel Component
 *
 * Displays Advanced Splits Analysis with metric and context toggles
 * NOW with simple 5th grade level explanations for each metric/context combination
 */
function AdvancedSplitsPanel({
  scoringSplitsData,
  threePtSplitsData,
  threePtVsPaceData,
  turnoverVsDefenseData,
  turnoverVsPaceData,
  assistsVsDefenseData,
  assistsVsPaceData,
  splitsLoading,
  threePtSplitsLoading,
  threePtVsPaceLoading,
  turnoverVsDefenseLoading,
  turnoverVsPaceLoading,
  assistsVsDefenseLoading,
  assistsVsPaceLoading,
  onShowGlossary
}) {
  // Toggle states for metric and context
  const [metric, setMetric] = useState('scoring') // 'scoring' | 'threePt' | 'turnovers' | 'assists'
  const [context, setContext] = useState('defense') // 'defense' | 'pace'

  // TEMPORARY: Mock data for Assists chart (remove after backend is ready)
  const mockAssistsData = {
    away_team: {
      team_id: 1610612745,
      team_abbreviation: 'HOU',
      full_name: 'Houston Rockets',
      season: '2025-26',
      season_avg_ast: 24.5,
      opponent_ball_movement_tier: 'average',
      opponent_opp_ast_rank: 12,
      splits: {
        elite: { home_ast: 23.2, home_games: 8, away_ast: 22.5, away_games: 7 },
        average: { home_ast: 24.8, home_games: 10, away_ast: 24.1, away_games: 9 },
        bad: { home_ast: 26.5, home_games: 6, away_ast: 25.8, away_games: 5 }
      }
    },
    home_team: {
      team_id: 1610612743,
      team_abbreviation: 'DEN',
      full_name: 'Denver Nuggets',
      season: '2025-26',
      season_avg_ast: 27.3,
      opponent_ball_movement_tier: 'elite',
      opponent_opp_ast_rank: 4,
      splits: {
        elite: { home_ast: 26.1, home_games: 9, away_ast: 25.4, away_games: 8 },
        average: { home_ast: 27.8, home_games: 11, away_ast: 26.9, away_games: 10 },
        bad: { home_ast: 29.2, home_games: 7, away_ast: 28.5, away_games: 6 }
      }
    }
  }

  // Use mock data if backend data isn't available
  const assistsData = assistsVsDefenseData || mockAssistsData

  // TEMPORARY: Mock data for Assists vs Pace chart (remove after backend is ready)
  const mockAssistsPaceData = {
    away_team: {
      team_id: 1610612745,
      team_abbreviation: 'HOU',
      full_name: 'Houston Rockets',
      season: '2025-26',
      season_avg_ast: 24.5,
      projected_pace: 100.4,
      splits: {
        slow: { home_ast: 22.8, home_games: 6, away_ast: 22.1, away_games: 5 },
        normal: { home_ast: 24.5, home_games: 12, away_ast: 23.8, away_games: 11 },
        fast: { home_ast: 26.2, home_games: 8, away_ast: 25.6, away_games: 7 }
      }
    },
    home_team: {
      team_id: 1610612743,
      team_abbreviation: 'DEN',
      full_name: 'Denver Nuggets',
      season: '2025-26',
      season_avg_ast: 27.3,
      projected_pace: 100.4,
      splits: {
        slow: { home_ast: 25.6, home_games: 7, away_ast: 24.9, away_games: 6 },
        normal: { home_ast: 27.4, home_games: 13, away_ast: 26.7, away_games: 12 },
        fast: { home_ast: 29.1, home_games: 9, away_ast: 28.4, away_games: 8 }
      }
    }
  }

  // Use mock data if backend data isn't available
  const assistsPaceData = assistsVsPaceData || mockAssistsPaceData

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            Advanced Splits Analysis
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Compare team performance across different metrics and contexts
          </p>
        </div>
        <button
          onClick={onShowGlossary}
          className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg border border-blue-200 dark:border-blue-800 transition-colors text-sm font-medium"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="hidden sm:inline">Glossary</span>
        </button>
      </div>

      {/* Metric Toggle (Scoring | 3PT | Turnovers | Assists) */}
      <div className="mb-3">
        <div className="inline-flex w-full sm:w-auto rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
          <button
            onClick={() => setMetric('scoring')}
            className={`flex-1 sm:flex-none px-3 sm:px-6 py-2 text-sm sm:text-base font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              metric === 'scoring'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Scoring
          </button>
          <button
            onClick={() => setMetric('threePt')}
            className={`flex-1 sm:flex-none px-3 sm:px-6 py-2 text-sm sm:text-base font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              metric === 'threePt'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            3PT
          </button>
          <button
            onClick={() => setMetric('turnovers')}
            className={`flex-1 sm:flex-none px-3 sm:px-6 py-2 text-sm sm:text-base font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              metric === 'turnovers'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Turnovers
          </button>
          <button
            onClick={() => setMetric('assists')}
            className={`flex-1 sm:flex-none px-3 sm:px-6 py-2 text-sm sm:text-base font-medium transition-colors ${
              metric === 'assists'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Assists
          </button>
        </div>
      </div>

      {/* Context Toggle (Defense Tiers | Pace Buckets) */}
      <div className="mb-6">
        <div className="inline-flex w-full sm:w-auto rounded-md border border-gray-300 dark:border-gray-600 overflow-hidden">
          <button
            onClick={() => setContext('defense')}
            className={`flex-1 sm:flex-none px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              context === 'defense'
                ? 'bg-gray-700 dark:bg-gray-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Defense Tiers
          </button>
          <button
            onClick={() => setContext('pace')}
            className={`flex-1 sm:flex-none px-3 sm:px-4 py-1.5 text-xs sm:text-sm font-medium transition-colors ${
              context === 'pace'
                ? 'bg-gray-700 dark:bg-gray-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Pace Buckets
          </button>
        </div>
      </div>

      {/* Explanatory Text Block - Dynamic based on metric + context */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-1">
              {metric === 'scoring' && context === 'defense' && 'About Scoring vs Defense Tiers'}
              {metric === 'scoring' && context === 'pace' && 'About Scoring vs Game Speed'}
              {metric === 'threePt' && context === 'defense' && 'About 3-Point Shooting vs Defense'}
              {metric === 'threePt' && context === 'pace' && 'About 3-Point Shooting vs Game Speed'}
              {metric === 'turnovers' && context === 'defense' && 'About Turnovers vs Defense Pressure'}
              {metric === 'turnovers' && context === 'pace' && 'About Turnovers vs Game Speed'}
              {metric === 'assists' && context === 'defense' && 'About Assists vs Ball-Movement Defense'}
              {metric === 'assists' && context === 'pace' && 'About Assists vs Game Speed'}
            </h4>
            <p className="text-sm text-blue-800 dark:text-blue-200">
              {metric === 'scoring' && EXPLANATION_TEXT.scoring.description}
              {metric === 'threePt' && EXPLANATION_TEXT.threePt.description}
              {metric === 'turnovers' && EXPLANATION_TEXT.turnovers.description}
              {metric === 'assists' && EXPLANATION_TEXT.assists?.description}
            </p>
            {context === 'defense' && (
              <p className="text-sm text-blue-800 dark:text-blue-200 mt-2">
                {metric === 'assists'
                  ? EXPLANATION_TEXT.ballMovementTiers.description
                  : EXPLANATION_TEXT.defenseTiers.description}
              </p>
            )}
            {context === 'pace' && (
              <p className="text-sm text-blue-800 dark:text-blue-200 mt-2">
                {EXPLANATION_TEXT.paceBuckets.description}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Identity Tags (only for scoring metric) */}
      {metric === 'scoring' && scoringSplitsData && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Away Team Tags */}
          {scoringSplitsData.away_team && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-3">
                {scoringSplitsData.away_team.team_abbreviation} Identity
              </h3>
              {scoringSplitsData.away_team.identity_tags && scoringSplitsData.away_team.identity_tags.length > 0 ? (
                <IdentityTags
                  tags={scoringSplitsData.away_team.identity_tags}
                  teamAbbr={scoringSplitsData.away_team.team_abbreviation}
                  showTooltip={true}
                />
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No distinctive scoring patterns detected (consistent across contexts)
                </p>
              )}
            </div>
          )}

          {/* Home Team Tags */}
          {scoringSplitsData.home_team && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-3">
                {scoringSplitsData.home_team.team_abbreviation} Identity
              </h3>
              {scoringSplitsData.home_team.identity_tags && scoringSplitsData.home_team.identity_tags.length > 0 ? (
                <IdentityTags
                  tags={scoringSplitsData.home_team.identity_tags}
                  teamAbbr={scoringSplitsData.home_team.team_abbreviation}
                  showTooltip={true}
                />
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No distinctive scoring patterns detected (consistent across contexts)
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Dynamic Chart Rendering */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Scoring + Defense */}
        {metric === 'scoring' && context === 'defense' && scoringSplitsData && (
          <>
            {scoringSplitsData.away_team && (
              <ScoringSpitsChart teamData={scoringSplitsData.away_team} />
            )}
            {scoringSplitsData.home_team && (
              <ScoringSpitsChart teamData={scoringSplitsData.home_team} />
            )}
          </>
        )}

        {/* Scoring + Pace */}
        {metric === 'scoring' && context === 'pace' && scoringSplitsData && (
          <>
            {scoringSplitsData.away_team && scoringSplitsData.away_team.pace_splits && (
              <ScoringVsPaceChart teamData={scoringSplitsData.away_team} />
            )}
            {scoringSplitsData.home_team && scoringSplitsData.home_team.pace_splits && (
              <ScoringVsPaceChart teamData={scoringSplitsData.home_team} />
            )}
          </>
        )}

        {/* 3PT + Defense */}
        {metric === 'threePt' && context === 'defense' && threePtSplitsData && (
          <>
            {threePtSplitsData.away_team && (
              <ThreePointScoringVsDefenseChart teamData={threePtSplitsData.away_team} />
            )}
            {threePtSplitsData.home_team && (
              <ThreePointScoringVsDefenseChart teamData={threePtSplitsData.home_team} />
            )}
          </>
        )}

        {/* 3PT + Pace */}
        {metric === 'threePt' && context === 'pace' && threePtVsPaceData && (
          <>
            {threePtVsPaceData.away_team && (
              <ThreePointScoringVsPaceChart teamData={threePtVsPaceData.away_team} />
            )}
            {threePtVsPaceData.home_team && (
              <ThreePointScoringVsPaceChart teamData={threePtVsPaceData.home_team} />
            )}
          </>
        )}

        {/* Turnovers + Defense */}
        {metric === 'turnovers' && context === 'defense' && turnoverVsDefenseData && (
          <>
            {turnoverVsDefenseData.away_team && (
              <TurnoverVsDefensePressureChart teamData={turnoverVsDefenseData.away_team} />
            )}
            {turnoverVsDefenseData.home_team && (
              <TurnoverVsDefensePressureChart teamData={turnoverVsDefenseData.home_team} />
            )}
          </>
        )}

        {/* Turnovers + Pace */}
        {metric === 'turnovers' && context === 'pace' && turnoverVsPaceData && (
          <>
            {turnoverVsPaceData.away_team && (
              <TurnoverVsPaceChart teamData={turnoverVsPaceData.away_team} />
            )}
            {turnoverVsPaceData.home_team && (
              <TurnoverVsPaceChart teamData={turnoverVsPaceData.home_team} />
            )}
          </>
        )}

        {/* Assists + Defense */}
        {metric === 'assists' && context === 'defense' && assistsData && (
          <>
            {assistsData.away_team && (
              <AssistsVsDefenseChart teamData={assistsData.away_team} />
            )}
            {assistsData.home_team && (
              <AssistsVsDefenseChart teamData={assistsData.home_team} />
            )}
          </>
        )}

        {/* Assists + Pace */}
        {metric === 'assists' && context === 'pace' && assistsPaceData && (
          <>
            {assistsPaceData.away_team && (
              <AssistsVsPaceChart teamData={assistsPaceData.away_team} />
            )}
            {assistsPaceData.home_team && (
              <AssistsVsPaceChart teamData={assistsPaceData.home_team} />
            )}
          </>
        )}
      </div>

      {/* Loading States */}
      {metric === 'scoring' && splitsLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading scoring splits...</p>
        </div>
      )}
      {metric === 'threePt' && context === 'defense' && threePtSplitsLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading 3PT scoring splits...</p>
        </div>
      )}
      {metric === 'threePt' && context === 'pace' && threePtVsPaceLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading 3PT scoring vs pace...</p>
        </div>
      )}
      {metric === 'turnovers' && context === 'defense' && turnoverVsDefenseLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading turnover vs defense pressure...</p>
        </div>
      )}
      {metric === 'turnovers' && context === 'pace' && turnoverVsPaceLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading turnover vs pace...</p>
        </div>
      )}
      {metric === 'assists' && context === 'defense' && assistsVsDefenseLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading assists vs defense...</p>
        </div>
      )}
      {metric === 'assists' && context === 'pace' && assistsVsPaceLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p>Loading assists vs pace...</p>
        </div>
      )}
    </div>
  )
}

export default AdvancedSplitsPanel
