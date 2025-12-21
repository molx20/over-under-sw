/**
 * ScoringVsPaceChart Component
 *
 * Bar chart showing team scoring by game pace bucket and location.
 * X-axis: Pace buckets (Slow, Normal, Fast)
 * Y-axis: Points per game
 * Bars: Home (one color) and Away (another color) for each bucket
 */

import { useState } from 'react'
import BarDrilldownPopover from './BarDrilldownPopover'

function ScoringVsPaceChart({ teamData, compact = false }) {
  // Drilldown state
  const [drilldownOpen, setDrilldownOpen] = useState(false)
  const [drilldownParams, setDrilldownParams] = useState(null)
  const [drilldownAnchor, setDrilldownAnchor] = useState(null)
  if (!teamData || !teamData.pace_splits) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
        No pace splits data available
      </div>
    )
  }

  const { pace_splits, season_avg_ppg, team_abbreviation, projected_pace } = teamData

  // Determine which bucket the projected pace falls into
  const getPaceBucket = (pace) => {
    if (!pace) return null
    if (pace < 96.0) return 'slow'
    if (pace > 101.0) return 'fast'
    return 'normal'
  }

  const projectedBucket = getPaceBucket(projected_pace)

  // Extract data for chart
  const buckets = ['slow', 'normal', 'fast']
  const bucketLabels = {
    slow: 'Slow Pace',
    normal: 'Normal Pace',
    fast: 'Fast Pace'
  }

  // Find all PPG values for Y-axis scaling
  const allValues = []
  buckets.forEach(bucket => {
    if (pace_splits[bucket]?.home_ppg) allValues.push(pace_splits[bucket].home_ppg)
    if (pace_splits[bucket]?.away_ppg) allValues.push(pace_splits[bucket].away_ppg)
  })
  if (season_avg_ppg) allValues.push(season_avg_ppg)

  // Y-axis domain: always start at 0, max = highest value + 5 padding
  const minValue = 0
  const maxValue = Math.max(...allValues) + 5
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

  // Check if bucket has sufficient data (at least 3 games)
  const hasSufficientData = (bucket, location) => {
    const gamesKey = `${location}_games`
    return pace_splits[bucket]?.[gamesKey] >= 3
  }

  return (
    <div className={`${compact ? 'p-3' : 'p-3 sm:p-4 md:p-6'} bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 w-full max-sm:overflow-x-hidden`}>
      {/* Header */}
      <div className="mb-3 sm:mb-4">
        <h3 className={`${compact ? 'text-sm' : 'text-sm sm:text-base'} font-semibold text-gray-900 dark:text-white`}>
          Scoring vs Pace
        </h3>
        <p className={`${compact ? 'text-xs' : 'text-xs sm:text-sm'} text-gray-500 dark:text-gray-400 mt-1`}>
          {team_abbreviation} - Season Avg: {season_avg_ppg ? season_avg_ppg.toFixed(1) : 'N/A'} PPG
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
          {season_avg_ppg && (
            <div
              className="absolute left-0 right-0 border-t-2 border-dashed border-blue-500 dark:border-blue-400 z-10 pointer-events-none"
              style={{ bottom: `${getLinePosition(season_avg_ppg)}%` }}
            >
              <span className="absolute -top-2 right-0 text-[11px] sm:text-xs font-medium text-blue-600 dark:text-blue-400 bg-white dark:bg-gray-800 px-1 whitespace-nowrap">
                Avg: {season_avg_ppg.toFixed(1)}
              </span>
            </div>
          )}

          {/* Bar Groups */}
          <div className="relative flex justify-around w-full h-full px-2 sm:px-3 md:px-4">
            {buckets.map((bucket) => {
              const homeValue = pace_splits[bucket]?.home_ppg
              const awayValue = pace_splits[bucket]?.away_ppg
              const homeGames = pace_splits[bucket]?.home_games || 0
              const awayGames = pace_splits[bucket]?.away_games || 0
              const homeHeight = getBarHeight(homeValue)
              const awayHeight = getBarHeight(awayValue)
              const hasHomeData = hasSufficientData(bucket, 'home')
              const hasAwayData = hasSufficientData(bucket, 'away')

              const isProjectedBucket = projectedBucket === bucket

              return (
                <div
                  key={bucket}
                  className={`flex flex-col items-center flex-1 max-w-[120px] transition-all duration-200 ${
                    isProjectedBucket ? 'ring-2 ring-yellow-400 dark:ring-yellow-500 rounded-lg bg-yellow-50 dark:bg-yellow-900/10 -mx-1 px-1' : ''
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
                          minHeight: '4px',
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
                              <div className="text-lg font-bold">{homeValue.toFixed(1)} PPG</div>
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
                                      metric: 'scoring',
                                      dimension: 'pace_bucket',
                                      context: 'home',
                                      bucket: bucket,
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
                          minHeight: '4px',
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
                              <div className="text-lg font-bold">{awayValue.toFixed(1)} PPG</div>
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
                                      metric: 'scoring',
                                      dimension: 'pace_bucket',
                                      context: 'away',
                                      bucket: bucket,
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

                  {/* X-axis label */}
                  <div className="mt-2 sm:mt-3 text-[10px] sm:text-xs text-center text-gray-700 dark:text-gray-300 font-medium px-0.5 sm:px-1">
                    <div className="font-semibold leading-tight">{bucketLabels[bucket]}</div>
                    <div className="text-gray-500 dark:text-gray-400 text-[9px] sm:text-xs mt-0.5 leading-tight">
                      ({bucket === 'slow' ? '<96' : bucket === 'fast' ? '>101' : '96-101'} poss/48)
                    </div>
                    {isProjectedBucket && projected_pace && (
                      <div className="mt-1 px-1 sm:px-2 py-0.5 bg-yellow-400 dark:bg-yellow-500 text-yellow-900 dark:text-yellow-950 text-[9px] sm:text-xs font-semibold rounded">
                        Proj ({projected_pace.toFixed(1)})
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* X-axis baseline */}
        <div className="border-t-2 border-gray-400 dark:border-gray-500 mt-1"></div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-3 sm:gap-4 md:gap-6 mt-4 sm:mt-6 pt-3 sm:pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="w-4 h-4 sm:w-5 sm:h-5 bg-blue-500 dark:bg-blue-600 rounded shadow-sm"></div>
          <span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 font-medium">Home</span>
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="w-4 h-4 sm:w-5 sm:h-5 bg-orange-500 dark:bg-orange-600 rounded shadow-sm"></div>
          <span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 font-medium">Away</span>
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="w-5 sm:w-6 h-0.5 bg-blue-500 dark:bg-blue-400 border-dashed" style={{borderTop: '2px dashed'}}></div>
          <span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 font-medium">Season Avg</span>
        </div>
      </div>

      {/* Info note */}
      <div className="mt-3 sm:mt-4 text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 text-center leading-relaxed">
        Pace buckets based on game pace (possessions per 48 minutes)
        <br className="hidden sm:block" />
        <span className="sm:hidden"> • </span>
        Minimum 3 games per category for reliable data
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
          bucket={drilldownParams.bucket}
          paceType={drilldownParams.paceType}
          season={drilldownParams.season}
          barValue={drilldownParams.barValue}
          anchorEl={drilldownAnchor}
        />
      )}
    </div>
  )
}

export default ScoringVsPaceChart
