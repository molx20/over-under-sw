import { useState } from 'react'
import {
  calculateExpectedEmptyPossessions,
  calculateExpectedScoringPossessions,
  round1,
  roundWhole,
  formatPts,
  getImpactColor,
  getDeltaVsLeagueColor
} from '../utils/possessionTranslation'

/**
 * PossessionInsightsPanel Component
 *
 * Displays game-level possession insights in 2 sections:
 * 1. What drives this matchup (Top 3 bullets)
 * 2. Total lens (Combined empty possessions)
 *
 * Props:
 * - homeTeam: { id, name, abbreviation }
 * - awayTeam: { id, name, abbreviation }
 * - homeInsights: { section_1_drivers, section_3_total }
 * - awayInsights: { section_1_drivers, section_3_total }
 * - metadata: { game_id, game_date, generated_at }
 */
function PossessionInsightsPanel({ homeTeam, awayTeam, homeInsights, awayInsights, metadata }) {
  const [viewMode, setViewMode] = useState('both') // 'both' | 'away' | 'home'

  if (!homeInsights || !awayInsights) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6 text-center">
        <p className="text-gray-600 dark:text-gray-400">No possession insights available</p>
      </div>
    )
  }

  const showAway = viewMode === 'both' || viewMode === 'away'
  const showHome = viewMode === 'both' || viewMode === 'home'

  return (
    <div className="space-y-4">
      {/* Team Toggle */}
      <div className="flex gap-2 justify-center">
        <button
          onClick={() => setViewMode('both')}
          className={`px-4 py-2 rounded-lg font-medium transition-all text-sm ${
            viewMode === 'both'
              ? 'bg-primary-600 text-white shadow-md'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          Both Teams
        </button>
        <button
          onClick={() => setViewMode('away')}
          className={`px-4 py-2 rounded-lg font-medium transition-all text-sm ${
            viewMode === 'away'
              ? 'bg-primary-600 text-white shadow-md'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          {awayTeam?.abbreviation || 'Away'}
        </button>
        <button
          onClick={() => setViewMode('home')}
          className={`px-4 py-2 rounded-lg font-medium transition-all text-sm ${
            viewMode === 'home'
              ? 'bg-primary-600 text-white shadow-md'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          {homeTeam?.abbreviation || 'Home'}
        </button>
      </div>

      {/* Grid Layout */}
      <div className={`grid gap-6 ${viewMode === 'both' ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
        {/* Away Team Card */}
        {showAway && (
          <TeamInsightsCard
            team={awayTeam}
            insights={awayInsights}
          />
        )}

        {/* Home Team Card */}
        {showHome && (
          <TeamInsightsCard
            team={homeTeam}
            insights={homeInsights}
          />
        )}
      </div>

      {/* Metadata Footer */}
      {metadata && (
        <div className="text-center pt-4 border-t border-gray-200 dark:border-gray-700">
          {metadata.is_projection && (
            <div className="mb-3">
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Projected - Based on Season Averages
              </span>
            </div>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Generated: {new Date(metadata.generated_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  )
}

/**
 * TeamInsightsCard Component
 *
 * Displays all 4 sections for a single team
 */
function TeamInsightsCard({ team, insights }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-4">
        <h3 className="text-xl font-bold text-white">
          {team?.abbreviation || team?.name || 'Team'}
        </h3>
      </div>

      <div className="p-6 space-y-6">
        {/* Section 1: What Drives This Matchup */}
        <Section1Drivers drivers={insights.section_1_drivers} />

        {/* Section 2: Total Lens */}
        <Section3TotalLens total={insights.section_3_total} />
      </div>
    </div>
  )
}

/**
 * Section 1: What Drives This Matchup
 */
function Section1Drivers({ drivers }) {
  if (!drivers || drivers.length === 0) return null

  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        What Drives This Matchup
      </h4>
      <ul className="space-y-2">
        {drivers.slice(0, 3).map((bullet, idx) => (
          <li key={idx} className="flex items-start gap-2">
            <span className="text-primary-600 dark:text-primary-400 mt-0.5">•</span>
            <span className="text-sm text-gray-700 dark:text-gray-300">{bullet}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * Section 3: Total Lens
 */
function Section3TotalLens({ total }) {
  if (!total) return null

  const { combined_empty, combined_opportunities, label } = total

  const getBadgeColor = (label) => {
    switch (label) {
      case 'Over-friendly':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'High variance':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      case 'Under-friendly':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  // Calculate translation counts (pregame projections)
  const projectedPossessions = combined_opportunities || 0
  const expectedEmptyPossessions = calculateExpectedEmptyPossessions(projectedPossessions, combined_empty)
  const expectedScoringPossessions = calculateExpectedScoringPossessions(projectedPossessions, expectedEmptyPossessions)

  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
        Total Lens
      </h4>

      {/* Clarification Caption */}
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 italic">
        Combined Opportunities = Projected Game Possessions
      </p>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Projected Game Possessions</span>
          <span className="text-sm font-bold text-gray-900 dark:text-white">{combined_opportunities}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Expected Empty Possessions</span>
          <span className="text-sm font-bold text-gray-900 dark:text-white">
            {calculateExpectedEmptyPossessions(projectedPossessions, combined_empty).toFixed(1)}
          </span>
        </div>
        <div className="pt-2">
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getBadgeColor(label)}`}>
            Variance: {label}
          </span>
        </div>
      </div>

      {/* Translation (Counts) Section */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <h5 className="text-sm font-semibold text-gray-900 dark:text-white">
            Translation (Counts)
          </h5>
          <button
            className="group relative"
            title="Turns rates into expected counts so you can 'feel' the matchup. Pregame projection."
          >
            <svg className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
              Turns rates into expected counts so you can 'feel' the matchup. Pregame projection.
            </span>
          </button>
          <span className="ml-auto text-xs px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full font-medium">
            Projected — Pregame
          </span>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">Projected Possessions (Game)</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {round1(projectedPossessions).toFixed(1)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">Expected Empty Possessions</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {expectedEmptyPossessions.toFixed(1)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">Expected Scoring Possessions</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {expectedScoringPossessions.toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      {/* Translation (Counts) - NEW SECTION - Only show if data available */}
      {total.projected_game_possessions != null && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <h5 className="text-sm font-semibold text-gray-900 dark:text-white">
              Translation (Counts)
            </h5>
            <button
              className="group relative"
              title="Turns rates into expected counts so you can 'feel' the matchup. Pregame projection."
            >
              <svg className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                Turns rates into expected counts so you can 'feel' the matchup. Pregame projection.
              </span>
            </button>
            <span className="ml-auto text-xs px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full font-medium">
              Projected — Pregame
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">Projected Game Possessions:</span>
              <span className="text-lg font-bold text-gray-900 dark:text-white">
                {roundWhole(total.projected_game_possessions)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">Expected Empty Possessions:</span>
              <span className="text-lg font-bold text-orange-600 dark:text-orange-400">
                {roundWhole(total.expected_empty_possessions_game)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">Expected Scoring Possessions:</span>
              <span className="text-lg font-bold text-green-600 dark:text-green-400">
                {roundWhole(total.projected_game_possessions - total.expected_empty_possessions_game)}
              </span>
            </div>

            <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600 dark:text-gray-400">League Avg Empty Rate:</span>
                <span className="text-gray-700 dark:text-gray-300 font-semibold">
                  {round1(total.league_avg_empty_rate)}%
                </span>
              </div>
              <div className="flex items-center justify-between text-xs mt-1">
                <span className="text-gray-600 dark:text-gray-400">This Game Expected:</span>
                <span className={`font-bold ${getDeltaVsLeagueColor(total.expected_empty_rate - total.league_avg_empty_rate)}`}>
                  {round1(total.expected_empty_rate)}%
                  {' '}
                  ({total.expected_empty_rate > total.league_avg_empty_rate ? '+' : ''}
                  {round1(total.expected_empty_rate - total.league_avg_empty_rate)}%)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* FT Points Environment - Only show if data available */}
      {total.combined_ft_points && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h5 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            FT Points Environment
          </h5>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">Combined FT Points (Adj):</span>
              <span className="text-sm font-bold text-gray-900 dark:text-white">
                {formatPts(total.combined_ft_points.adjusted)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600 dark:text-gray-400">Net FT Impact:</span>
              <span className={`text-sm font-bold ${getImpactColor(total.combined_ft_points.net_impact)}`}>
                {total.combined_ft_points.net_impact > 0 ? '+' : ''}
                {formatPts(total.combined_ft_points.net_impact)} pts
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PossessionInsightsPanel
