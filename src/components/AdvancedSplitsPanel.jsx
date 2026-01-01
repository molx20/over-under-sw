import { useState } from 'react'
import TeamArchetypes from './TeamArchetypes'
import ArchetypeRankingsPanel from './ArchetypeRankingsPanel'
import ScoringSpitsChart from './ScoringSpitsChart'
import ScoringVsPaceChart from './ScoringVsPaceChart'
import ThreePointScoringVsDefenseChart from './ThreePointScoringVsDefenseChart'
import ThreePointScoringVsPaceChart from './ThreePointScoringVsPaceChart'
import TurnoverVsDefensePressureChart from './TurnoverVsDefensePressureChart'
import TurnoverVsPaceChart from './TurnoverVsPaceChart'
import AssistsVsDefenseChart from './AssistsVsDefenseChart'
import AssistsVsPaceChart from './AssistsVsPaceChart'
import { EXPLANATION_TEXT } from '../utils/explanationText'
import { useTeamArchetypes } from '../utils/api'

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
  homeArchetypes,
  awayArchetypes
}) {
  // Toggle states for metric, context, and window
  const [metric, setMetric] = useState('scoring') // 'scoring' | 'threePt' | 'turnovers' | 'assists' | 'rebounds'
  const [context, setContext] = useState('defense') // 'defense' | 'pace'
  const [window, setWindow] = useState('season') // 'season' | 'last10'
  const [showExplanation, setShowExplanation] = useState(false) // Collapsed by default on mobile

  // Fetch ALL teams' archetypes for similar teams display
  const { data: allTeamsArchetypes } = useTeamArchetypes(null, '2025-26')

  // DIAGNOSTIC LOGGING
  console.log('[AdvancedSplitsPanel] Current metric:', metric)
  console.log('[AdvancedSplitsPanel] Current context:', context)
  console.log('[AdvancedSplitsPanel] homeArchetypes:', homeArchetypes)
  console.log('[AdvancedSplitsPanel] awayArchetypes:', awayArchetypes)

  if (metric === 'assists') {
    console.log('[AdvancedSplitsPanel] ASSISTS TAB ACTIVE')
    console.log('[AdvancedSplitsPanel] assistsVsDefenseData:', assistsVsDefenseData)
    console.log('[AdvancedSplitsPanel] assistsVsDefenseData?.away_team:', assistsVsDefenseData?.away_team)
    console.log('[AdvancedSplitsPanel] assistsVsDefenseData?.home_team:', assistsVsDefenseData?.home_team)
    console.log('[AdvancedSplitsPanel] assistsVsDefenseLoading:', assistsVsDefenseLoading)
    console.log('[AdvancedSplitsPanel] Render check: metric===assists && context===defense && assistsVsDefenseData =',
      metric === 'assists' && context === 'defense' && !!assistsVsDefenseData)
  }

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
      </div>

      {/* Metric Toggle (Scoring | 3PT | Turnovers | Assists | Rebounds) */}
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
            className={`flex-1 sm:flex-none px-3 sm:px-6 py-2 text-sm sm:text-base font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              metric === 'assists'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Assists
          </button>
          <button
            onClick={() => setMetric('rebounds')}
            className={`flex-1 sm:flex-none px-3 sm:px-6 py-2 text-sm sm:text-base font-medium transition-colors ${
              metric === 'rebounds'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Rebounds
          </button>
        </div>
      </div>

      {/* Context Toggle (Defense Tiers | Pace Buckets) - Only for non-Rebounds */}
      {metric !== 'rebounds' && (
        <div className="mb-3">
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
      )}

      {/* Time Window Toggle (Season | Last 10) - Only for Archetypes */}
      <div className="mb-6">
        <div className="inline-flex w-full sm:w-auto rounded-md border border-gray-300 dark:border-gray-600 overflow-hidden">
          <button
            onClick={() => setWindow('season')}
            className={`flex-1 sm:flex-none px-6 sm:px-8 py-2 text-sm font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              window === 'season'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Season
          </button>
          <button
            onClick={() => setWindow('last10')}
            className={`flex-1 sm:flex-none px-6 sm:px-8 py-2 text-sm font-medium transition-colors ${
              window === 'last10'
                ? 'bg-primary-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            Last 10
          </button>
        </div>
      </div>

      {/* Explanatory Text Block - Collapsible on mobile */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden mb-6">
        <button
          onClick={() => setShowExplanation(!showExplanation)}
          className="w-full flex items-center justify-between p-3 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors min-h-[44px]"
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-semibold text-blue-900 dark:text-blue-300">
              About {metric === 'scoring' && 'Scoring'}{metric === 'threePt' && 'Three-Point'}{metric === 'turnovers' && 'Turnover'}{metric === 'assists' && 'Assists'}{metric === 'rebounds' && 'Rebounding'} Archetypes
            </span>
          </div>
          <svg
            className={`w-5 h-5 text-blue-600 dark:text-blue-400 transition-transform ${
              showExplanation ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showExplanation && (
          <div className="px-4 pb-4 pt-2 border-t border-blue-200 dark:border-blue-700">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Archetypes classify teams based on their {metric === 'scoring' && 'offensive and defensive scoring patterns'}
              {metric === 'threePt' && 'three-point shooting tendencies and volume'}
              {metric === 'turnovers' && 'ball security and defensive pressure'}
              {metric === 'assists' && 'playmaking and ball movement'}
              {metric === 'rebounds' && 'rebounding effort and second-chance opportunities'}.
              Each team is assigned to one of four archetypes for both offense and defense based on their performance metrics.
            </p>
            <p className="text-sm text-blue-800 dark:text-blue-200 mt-2">
              <strong>Percentile rankings</strong> show how each team compares to the league average (50th percentile).
              Higher percentiles indicate stronger performance in that archetype's defining characteristics.
              Toggle between <strong>Season</strong> (full season stats) and <strong>Last 10</strong> (recent form) to identify style shifts.
            </p>
          </div>
        )}
      </div>

      {/* Archetype Panel with Actual Stats */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        {metric === 'scoring' && scoringSplitsData && (
          <ArchetypeRankingsPanel
            family="scoring"
            homeArchetypes={homeArchetypes}
            awayArchetypes={awayArchetypes}
            window={window}
            homeStats={scoringSplitsData?.home_team}
            awayStats={scoringSplitsData?.away_team}
            context={context}
          />
        )}

        {metric === 'threePt' && (context === 'defense' ? threePtSplitsData : threePtVsPaceData) && (
          <ArchetypeRankingsPanel
            family="threes"
            homeArchetypes={homeArchetypes}
            awayArchetypes={awayArchetypes}
            window={window}
            homeStats={context === 'defense' ? threePtSplitsData?.home_team : threePtVsPaceData?.home_team}
            awayStats={context === 'defense' ? threePtSplitsData?.away_team : threePtVsPaceData?.away_team}
            context={context}
          />
        )}

        {metric === 'turnovers' && (context === 'defense' ? turnoverVsDefenseData : turnoverVsPaceData) && (
          <ArchetypeRankingsPanel
            family="turnovers"
            homeArchetypes={homeArchetypes}
            awayArchetypes={awayArchetypes}
            window={window}
            homeStats={context === 'defense' ? turnoverVsDefenseData?.home_team : turnoverVsPaceData?.home_team}
            awayStats={context === 'defense' ? turnoverVsDefenseData?.away_team : turnoverVsPaceData?.away_team}
            context={context}
          />
        )}

        {metric === 'assists' && (context === 'defense' ? assistsVsDefenseData : assistsVsPaceData) && (
          <ArchetypeRankingsPanel
            family="assists"
            homeArchetypes={homeArchetypes}
            awayArchetypes={awayArchetypes}
            window={window}
            homeStats={context === 'defense' ? assistsVsDefenseData?.home_team : assistsVsPaceData?.home_team}
            awayStats={context === 'defense' ? assistsVsDefenseData?.away_team : assistsVsPaceData?.away_team}
            context={context}
          />
        )}

        {metric === 'rebounds' && scoringSplitsData && (
          <ArchetypeRankingsPanel
            family="rebounds"
            homeArchetypes={homeArchetypes}
            awayArchetypes={awayArchetypes}
            window={window}
            homeStats={scoringSplitsData?.home_team}
            awayStats={scoringSplitsData?.away_team}
            context="defense"
          />
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
