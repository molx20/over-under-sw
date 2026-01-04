import { useState } from 'react'
import {
  calculateDeltaEmptyTO,
  calculateDeltaEmptyOREB,
  formatSigned,
  getDeltaEmptyColor,
  formatPts,
  getImpactColor
} from '../utils/possessionTranslation'

/**
 * OpponentResistancePanel Component
 *
 * Displays how opponent defensive pressure affects possession metrics:
 * - TO Pressure: Expected turnovers based on opponent's defense
 * - OREB Impact: Expected offensive rebounds based on opponent's rebounding
 * - Empty Index: Overall expected empty possessions metric
 *
 * Props:
 * - homeTeam: { id, name, abbreviation }
 * - awayTeam: { id, name, abbreviation }
 * - resistanceData: opponent_resistance object from API
 */
function OpponentResistancePanel({ homeTeam, awayTeam, resistanceData }) {
  const [viewMode, setViewMode] = useState('both') // 'both' | 'away' | 'home'
  const [window, setWindow] = useState('season') // 'season' | 'last5'

  if (!resistanceData || !resistanceData.team || !resistanceData.opp) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6 text-center">
        <p className="text-gray-600 dark:text-gray-400">No opponent resistance data available</p>
      </div>
    )
  }

  const showAway = viewMode === 'both' || viewMode === 'away'
  const showHome = viewMode === 'both' || viewMode === 'home'

  // Get data for selected window
  const homeData = resistanceData.team[window]
  const awayData = resistanceData.opp[window]

  return (
    <div className="space-y-4">
      {/* Header with Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white">
          Opponent Resistance Impact
        </h3>

        <div className="flex gap-2">
          {/* Window Toggle */}
          <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
            <button
              onClick={() => setWindow('season')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                window === 'season'
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              Season
            </button>
            <button
              onClick={() => setWindow('last5')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                window === 'last5'
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              Last 5
            </button>
          </div>

          {/* Team Toggle */}
          <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 p-1 rounded-lg">
            <button
              onClick={() => setViewMode('both')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                viewMode === 'both'
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              Both
            </button>
            <button
              onClick={() => setViewMode('away')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                viewMode === 'away'
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              {awayTeam?.abbreviation || 'Away'}
            </button>
            <button
              onClick={() => setViewMode('home')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                viewMode === 'home'
                  ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              {homeTeam?.abbreviation || 'Home'}
            </button>
          </div>
        </div>
      </div>

      {/* Grid Layout */}
      <div className={`grid gap-6 ${viewMode === 'both' ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
        {/* Away Team Card */}
        {showAway && (
          <ResistanceCard
            team={awayTeam}
            data={awayData}
            isHome={false}
          />
        )}

        {/* Home Team Card */}
        {showHome && (
          <ResistanceCard
            team={homeTeam}
            data={homeData}
            isHome={true}
          />
        )}
      </div>

      {/* Empty Edge Summary */}
      {viewMode === 'both' && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              <span className="font-semibold text-gray-900 dark:text-white">Empty Edge</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {homeTeam?.abbreviation} vs {awayTeam?.abbreviation}
              </span>
              <EmptyEdgeBadge edge={resistanceData.expected?.[`empty_edge_index_${window}`] || 0} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * ResistanceCard - Shows resistance metrics for a single team
 */
function ResistanceCard({ team, data, isHome }) {
  if (!data) return null

  // Calculate delta empties (pregame translation)
  const teamPossessions = data.avg_possessions || 0
  const deltaEmptyTO = calculateDeltaEmptyTO(teamPossessions, data.expected_to_delta)
  const deltaEmptyOREB = calculateDeltaEmptyOREB(teamPossessions, data.expected_oreb_delta)

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className={`px-6 py-4 ${isHome ? 'bg-gradient-to-r from-primary-600 to-primary-700' : 'bg-gradient-to-r from-gray-700 to-gray-800'}`}>
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-white">
            {team?.abbreviation || team?.name || 'Team'}
          </h3>
          <span className="text-xs font-semibold text-white/80 uppercase tracking-wide">
            {isHome ? 'Home' : 'Away'}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="p-6 space-y-4">
        {/* Section: Opponent Resistance (Empty Possessions) */}
        <div>
          <h6 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            Opponent Resistance (Empty Possessions)
          </h6>

          <div className="space-y-4">
            {/* TO Pressure */}
            <ResistanceMetric
              label="TO Pressure"
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              }
              identity={data.to_pct}
              expected={data.expected_to_pct}
              delta={data.expected_to_delta}
              unit="%"
              description="Turnover rate adjusted for opponent's defensive pressure"
              deltaEmpty={deltaEmptyTO}
              metricType="empty"
            />

            {/* OREB Impact */}
            <ResistanceMetric
              label="OREB Impact"
              icon={
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              }
              identity={data.oreb_pct}
              expected={data.expected_oreb_pct}
              delta={data.expected_oreb_delta}
              unit="%"
              description="Offensive rebound rate adjusted for opponent's rebounding strength"
              deltaEmpty={deltaEmptyOREB}
              metricType="empty"
            />
          </div>
        </div>

        {/* Divider */}
        <div className="border-t-2 border-gray-300 dark:border-gray-600"></div>

        {/* Section: Scoring Environment (Free Throws) */}
        <div>
          <h6 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            Scoring Environment (Free Throws)
          </h6>

          {/* Foul Rate */}
          <ResistanceMetric
            label="Foul Rate"
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            identity={data.ftr}
            expected={data.expected_ftr}
            delta={data.expected_ftr_delta}
            unit="%"
            description="Free throw rate (FTA/FGA) - higher values mean more scoring opportunities"
            deltaEmpty={null}
            metricType="scoring"
          />

          {/* Expected FT Points - Only show if data available */}
          {data.free_throw_points && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
              <h6 className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Expected FT Points
              </h6>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600 dark:text-gray-400">Baseline FT Points:</span>
                  <span className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                    {formatPts(data.free_throw_points.expected_ft_points_baseline)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600 dark:text-gray-400">Opponent-Adjusted FT Points:</span>
                  <span className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                    {formatPts(data.free_throw_points.expected_ft_points_adjusted)}
                  </span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Net FT Impact:</span>
                  <span className={`text-base font-bold ${getImpactColor(data.free_throw_points.net_ft_points_impact)}`}>
                    {data.free_throw_points.net_ft_points_impact > 0 ? '+' : ''}
                    {formatPts(data.free_throw_points.net_ft_points_impact)} pts
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Opponent Impact on Possessions */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <h6 className="text-sm font-bold text-gray-900 dark:text-white mb-3">
            Opponent Impact on Possessions
          </h6>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600 dark:text-gray-400">From Turnover Pressure:</span>
              <span className="text-sm font-bold text-orange-600 dark:text-orange-400">
                {formatSigned(deltaEmptyTO)} empty poss
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600 dark:text-gray-400">From Offensive Rebounding:</span>
              <span className="text-sm font-bold text-green-600 dark:text-green-400">
                {formatSigned(deltaEmptyOREB)} empty poss
              </span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-gray-200 dark:border-gray-600">
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Net Opponent Effect:</span>
              <span className={`text-base font-bold ${getDeltaEmptyColor(deltaEmptyTO + deltaEmptyOREB)}`}>
                {formatSigned((deltaEmptyTO || 0) + (deltaEmptyOREB || 0))} empty poss
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * ResistanceMetric - Individual metric row with identity → expected
 *
 * @param {string} metricType - "empty" | "scoring"
 *   - "empty": More = bad (red/orange), Less = good (green) [TO, OREB]
 *   - "scoring": More = good (green), Less = bad (red) [FTr]
 */
function ResistanceMetric({ label, icon, identity, expected, delta, unit, description, deltaEmpty, metricType = "empty" }) {
  const isIncrease = delta > 0
  const isSignificant = Math.abs(delta) >= 1

  // Color logic splits based on metric type
  const getValueColor = () => {
    if (!isSignificant) return 'text-gray-900 dark:text-white'

    if (metricType === "scoring") {
      // Scoring metrics: More = GREEN, Less = RED
      return isIncrease
        ? 'text-green-600 dark:text-green-400'
        : 'text-red-600 dark:text-red-400'
    } else {
      // Empty possession metrics: More = ORANGE/RED, Less = GREEN
      return isIncrease
        ? 'text-orange-600 dark:text-orange-400'
        : 'text-green-600 dark:text-green-400'
    }
  }

  const getBadgeColor = () => {
    if (!isSignificant) return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'

    if (metricType === "scoring") {
      // Scoring metrics: More = GREEN, Less = RED
      return isIncrease
        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
    } else {
      // Empty possession metrics: More = ORANGE, Less = GREEN
      return isIncrease
        ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300'
        : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <div className="text-gray-600 dark:text-gray-400">
          {icon}
        </div>
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{label}</span>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Identity */}
          <span className="text-lg font-mono text-gray-600 dark:text-gray-400">
            {identity?.toFixed(1)}{unit}
          </span>

          {/* Arrow */}
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>

          {/* Expected */}
          <span className={`text-lg font-mono font-bold ${getValueColor()}`}>
            {expected?.toFixed(1)}{unit}
          </span>
        </div>

        {/* Delta Badge */}
        <div className={`px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${getBadgeColor()}`}>
          {isIncrease ? (
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 15l7-7 7 7" />
            </svg>
          ) : delta < 0 ? (
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
            </svg>
          ) : null}
          <span>{delta > 0 ? '+' : ''}{delta?.toFixed(1)}</span>
        </div>
      </div>

      <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>

      {/* Delta Empty Possessions (Translation) - Only for empty metrics */}
      {deltaEmpty != null && metricType === "empty" && (
        <p className={`text-xs font-medium ${getDeltaEmptyColor(deltaEmpty)}`}>
          ≈ {formatSigned(deltaEmpty)} empty possessions
        </p>
      )}
    </div>
  )
}

/**
 * EmptyEdgeBadge - Shows which team has empty possession advantage
 */
function EmptyEdgeBadge({ edge }) {
  const absEdge = Math.abs(edge)
  const isPositive = edge > 0  // Positive = home team advantage
  const isSignificant = absEdge >= 5

  let bgColor, textColor, label
  if (absEdge < 5) {
    bgColor = 'bg-gray-100 dark:bg-gray-700'
    textColor = 'text-gray-700 dark:text-gray-300'
    label = 'Even'
  } else if (isPositive) {
    bgColor = 'bg-green-100 dark:bg-green-900'
    textColor = 'text-green-700 dark:text-green-300'
    label = 'Home Advantage'
  } else {
    bgColor = 'bg-blue-100 dark:bg-blue-900'
    textColor = 'text-blue-700 dark:text-blue-300'
    label = 'Away Advantage'
  }

  return (
    <div className={`px-3 py-1.5 rounded-full ${bgColor} ${textColor} flex items-center gap-2`}>
      <span className="text-sm font-bold">
        {edge > 0 ? '+' : ''}{edge.toFixed(1)}
      </span>
      <span className="text-xs font-semibold">{label}</span>
    </div>
  )
}

export default OpponentResistancePanel
