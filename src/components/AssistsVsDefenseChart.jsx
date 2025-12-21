/**
 * AssistsVsDefenseChart Component
 *
 * Bar chart showing team assists by opponent ball-movement defense tier and location.
 * X-axis: Ball-movement defense tiers (Elite, Average, Weak)
 * Y-axis: Assists per game
 * Bars: Home (blue) and Away (orange) for each tier
 */

import { useState } from 'react'
import BarDrilldownPopover from './BarDrilldownPopover'

function AssistsVsDefenseChart({ teamData, compact = false }) {
  // Drilldown state
  const [drilldownOpen, setDrilldownOpen] = useState(false)
  const [drilldownParams, setDrilldownParams] = useState(null)
  const [drilldownAnchor, setDrilldownAnchor] = useState(null)

  if (!teamData || !teamData.splits) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
        No assist splits data available
      </div>
    )
  }

  const {
    splits,
    season_avg_ast,
    team_abbreviation,
    opponent_ball_movement_tier,
    opponent_opp_ast_rank
  } = teamData

  // Extract data for chart
  const tiers = ['elite', 'average', 'bad']
  const tierLabels = {
    elite: 'Elite Defense',
    average: 'Avg Defense',
    bad: 'Weak Defense'
  }

  // Find all assist values for Y-axis scaling
  const allValues = []
  tiers.forEach(tier => {
    if (splits[tier]?.home_ast) allValues.push(splits[tier].home_ast)
    if (splits[tier]?.away_ast) allValues.push(splits[tier].away_ast)
  })
  if (season_avg_ast) allValues.push(season_avg_ast)

  // Y-axis domain: always start at 0, max = highest value + 5 padding
  const minValue = 0
  const maxValue = allValues.length > 0 ? Math.max(...allValues) + 5 : 30
  const chartRange = maxValue - minValue

  // Calculate bar heights as percentages from the bottom (0 to value)
  const getBarHeight = (value) => {
    if (!value || value <= 0) return 0
    const height = (value / chartRange) * 100
    return height
  }

  // Calculate position for season average line
  const getLinePosition = (value) => {
    if (!value) return 0
    return (value / chartRange) * 100
  }

  // Check if tier has sufficient data (at least 3 games)
  const hasSufficientData = (tier, location) => {
    const gamesKey = `${location}_games`
    return splits[tier]?.[gamesKey] >= 3
  }

  return (
    <div className={`${compact ? 'p-3' : 'p-3 sm:p-4 md:p-6'} bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 w-full max-sm:overflow-x-hidden`}>
      {/* Header */}
      <div className="mb-3 sm:mb-4">
        <h3 className={`${compact ? 'text-sm' : 'text-sm sm:text-base'} font-semibold text-gray-900 dark:text-white`}>
          Assists vs Ball-Movement Defense
        </h3>
        <p className={`${compact ? 'text-xs' : 'text-xs sm:text-sm'} text-gray-500 dark:text-gray-400 mt-1`}>
          {team_abbreviation} - Season Avg: {season_avg_ast ? season_avg_ast.toFixed(1) : 'N/A'} AST/G
        </p>
      </div>

      {/* Chart Container */}
      <div className="relative pt-2 sm:pt-4">
        {/* Chart Area with Grid */}
        <div className="relative h-64 sm:h-72 md:h-80 flex items-stretch">
          {/* Y-axis Grid Lines */}
          <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="border-t border-gray-200 dark:border-gray-600 border-dashed w-full" />
            ))}
          </div>

          {/* Y-axis Labels */}
          <div className="absolute left-0 top-0 bottom-0 -ml-8 sm:-ml-10 md:-ml-12 flex flex-col justify-between text-xs text-gray-500 dark:text-gray-400 pr-1 sm:pr-2">
            <span>{Math.round(maxValue)}</span>
            <span className="hidden sm:inline">{Math.round(chartRange * 0.75)}</span>
            <span>{Math.round(chartRange * 0.5)}</span>
            <span className="hidden sm:inline">{Math.round(chartRange * 0.25)}</span>
            <span>0</span>
          </div>

          {/* Season Average Reference Line */}
          {season_avg_ast && (
            <div
              className="absolute left-0 right-0 border-t-2 border-dashed border-blue-500 dark:border-blue-400 z-10 pointer-events-none"
              style={{ bottom: `${getLinePosition(season_avg_ast)}%` }}
            >
              <span className="absolute -top-2 right-0 text-[11px] sm:text-xs font-medium text-blue-600 dark:text-blue-400 bg-white dark:bg-gray-800 px-1 whitespace-nowrap">
                Avg: {season_avg_ast.toFixed(1)}
              </span>
            </div>
          )}

          {/* Bar Groups */}
          <div className="relative flex justify-around w-full h-full px-2 sm:px-3 md:px-4">
            {tiers.map((tier) => {
              const homeValue = splits[tier]?.home_ast
              const awayValue = splits[tier]?.away_ast
              const homeGames = splits[tier]?.home_games || 0
              const awayGames = splits[tier]?.away_games || 0
              const homeHeight = getBarHeight(homeValue)
              const awayHeight = getBarHeight(awayValue)
              const hasHomeData = hasSufficientData(tier, 'home')
              const hasAwayData = hasSufficientData(tier, 'away')

              const isOpponentTier = opponent_ball_movement_tier === tier

              return (
                <div
                  key={tier}
                  className={`flex flex-col items-center flex-1 max-w-[120px] transition-all duration-200 ${
                    isOpponentTier ? 'ring-2 ring-yellow-400 dark:ring-yellow-500 rounded-lg bg-yellow-50 dark:bg-yellow-900/10 -mx-1 px-1' : ''
                  }`}
                >
                  {/* Bars Container */}
                  <div className="relative flex justify-center gap-2 w-full h-full">
                    {/* Home Bar */}
                    {homeValue > 0 && (
                      <div
                        className={`
                          absolute bottom-0 left-0 w-1/2 group cursor-help rounded-t-sm
                          ${hasHomeData
                            ? 'bg-blue-500 dark:bg-blue-600 hover:bg-blue-600 dark:hover:bg-blue-500 shadow-md'
                            : 'bg-gray-300 dark:bg-gray-600 opacity-40'}
                          transition-all duration-200
                        `}
                        style={{
                          height: `${homeHeight}%`,
                          minHeight: homeValue > 0 ? '4px' : '0',
                          maxWidth: '45px',
                          marginLeft: 'calc(25% - 22.5px)'
                        }}
                      >
                        {/* Tooltip */}
                        {homeValue && (
                          <div className="absolute bottom-full mb-2 hidden group-hover:block group-active:block z-20
                max-sm:left-0 sm:left-1/2 sm:transform sm:-translate-x-1/2">
                            <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-md py-2 px-3 shadow-xl
                  max-sm:max-w-[85vw] max-sm:whitespace-normal sm:whitespace-nowrap">
                              <div className="font-semibold text-blue-300">Home</div>
                              <div className="text-lg font-bold">{homeValue.toFixed(1)} AST/G</div>
                              <div className="text-gray-300 dark:text-gray-400 text-xs">{homeGames} game{homeGames !== 1 ? 's' : ''}</div>
                              {!hasHomeData && (
                                <div className="text-yellow-400 text-xs mt-1">⚠ Need 3+ games</div>
                              )}
                              {homeGames >= 1 && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    const rect = e.currentTarget.closest('[class*="group"]').getBoundingClientRect()
                                    setDrilldownParams({
                                      teamId: teamData.team_id,
                                      metric: 'assists',
                                      dimension: 'ball_movement_tier',
                                      context: 'home',
                                      tier: tier,
                                      paceType: 'actual',
                                      season: teamData.season || '2025-26',
                                      barValue: homeValue
                                    })
                                    setDrilldownAnchor({ x: rect.left + rect.width / 2, y: rect.bottom })
                                    setDrilldownOpen(true)
                                  }}
                                  className={`mt-2 w-full px-2 py-1 rounded text-xs font-medium transition-colors ${
                                    homeGames >= 3
                                      ? 'bg-blue-500 hover:bg-blue-600 text-white'
                                      : 'bg-gray-600 hover:bg-gray-500 text-gray-300'
                                  }`}
                                  disabled={homeGames < 1}
                                >
                                  View games ({homeGames})
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Away Bar */}
                    {awayValue > 0 && (
                      <div
                        className={`
                          absolute bottom-0 right-0 w-1/2 group cursor-help rounded-t-sm
                          ${hasAwayData
                            ? 'bg-orange-500 dark:bg-orange-600 hover:bg-orange-600 dark:hover:bg-orange-500 shadow-md'
                            : 'bg-gray-300 dark:bg-gray-600 opacity-40'}
                          transition-all duration-200
                        `}
                        style={{
                          height: `${awayHeight}%`,
                          minHeight: awayValue > 0 ? '4px' : '0',
                          maxWidth: '45px',
                          marginRight: 'calc(25% - 22.5px)'
                        }}
                      >
                        {/* Tooltip */}
                        {awayValue && (
                          <div className="absolute bottom-full mb-2 hidden group-hover:block group-active:block z-20
                max-sm:right-0 sm:left-1/2 sm:transform sm:-translate-x-1/2">
                            <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-md py-2 px-3 shadow-xl
                  max-sm:max-w-[85vw] max-sm:whitespace-normal sm:whitespace-nowrap">
                              <div className="font-semibold text-orange-300">Away</div>
                              <div className="text-lg font-bold">{awayValue.toFixed(1)} AST/G</div>
                              <div className="text-gray-300 dark:text-gray-400 text-xs">{awayGames} game{awayGames !== 1 ? 's' : ''}</div>
                              {!hasAwayData && (
                                <div className="text-yellow-400 text-xs mt-1">⚠ Need 3+ games</div>
                              )}
                              {awayGames >= 1 && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    const rect = e.currentTarget.closest('[class*="group"]').getBoundingClientRect()
                                    setDrilldownParams({
                                      teamId: teamData.team_id,
                                      metric: 'assists',
                                      dimension: 'ball_movement_tier',
                                      context: 'away',
                                      tier: tier,
                                      paceType: 'actual',
                                      season: teamData.season || '2025-26',
                                      barValue: awayValue
                                    })
                                    setDrilldownAnchor({ x: rect.left + rect.width / 2, y: rect.bottom })
                                    setDrilldownOpen(true)
                                  }}
                                  className={`mt-2 w-full px-2 py-1 rounded text-xs font-medium transition-colors ${
                                    awayGames >= 3
                                      ? 'bg-orange-500 hover:bg-orange-600 text-white'
                                      : 'bg-gray-600 hover:bg-gray-500 text-gray-300'
                                  }`}
                                  disabled={awayGames < 1}
                                >
                                  View games ({awayGames})
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* X-axis Label */}
                  <div className="mt-2 sm:mt-3 text-center">
                    <div className={`${compact ? 'text-[10px]' : 'text-[10px] sm:text-xs'} font-medium text-gray-700 dark:text-gray-300`}>
                      {tierLabels[tier]}
                    </div>
                    {isOpponentTier && opponent_opp_ast_rank && (
                      <div className="mt-1 inline-block bg-yellow-400 dark:bg-yellow-500 text-gray-900 dark:text-gray-900 text-[9px] sm:text-[10px] font-bold px-2 py-0.5 rounded">
                        Opp (#{opponent_opp_ast_rank})
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Legend */}
        <div className="flex justify-center gap-3 sm:gap-4 mt-4 sm:mt-6 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-blue-500 dark:bg-blue-600 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">Home</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-orange-500 dark:bg-orange-600 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">Away</span>
          </div>
        </div>
      </div>

      {/* Explanation */}
      <div className="mt-4 sm:mt-6 p-3 sm:p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
          <strong>How to read:</strong> Shows each team's assists per game when facing defenses that allow different levels of ball movement.
          Elite ball-movement defenses (ranks 1-10) limit assists, while weak defenses (ranks 21-30) allow more passing and easier shot creation.
          {opponent_ball_movement_tier && (
            <span className="block mt-2 text-yellow-600 dark:text-yellow-400 font-medium">
              Today's opponent applies <strong>{opponent_ball_movement_tier}</strong> ball-movement pressure.
            </span>
          )}
        </p>
      </div>

      {/* Drilldown Popover */}
      {drilldownParams && (
        <BarDrilldownPopover
          isOpen={drilldownOpen}
          onClose={() => setDrilldownOpen(false)}
          teamId={drilldownParams.teamId}
          metric={drilldownParams.metric}
          dimension={drilldownParams.dimension}
          context={drilldownParams.context}
          tier={drilldownParams.tier}
          paceType={drilldownParams.paceType}
          season={drilldownParams.season}
          barValue={drilldownParams.barValue}
          anchorEl={drilldownAnchor}
        />
      )}
    </div>
  )
}

export default AssistsVsDefenseChart
