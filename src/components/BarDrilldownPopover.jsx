import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * BarDrilldownPopover
 *
 * Reusable popover component that shows the detailed list of games
 * that make up a specific bar in any chart.
 *
 * Props:
 *   - isOpen: boolean
 *   - onClose: function
 *   - teamId: number
 *   - metric: 'scoring' | 'threept' | 'turnovers'
 *   - dimension: 'defense_tier' | 'pace_bucket' | 'threept_def_tier' | 'pressure_tier'
 *   - context: 'home' | 'away'
 *   - bucket: 'slow' | 'normal' | 'fast' (for pace_bucket)
 *   - tier: 'elite' | 'avg' | 'bad' | 'low' (for tier dimensions)
 *   - pace_type: 'actual' | 'projected' (default: 'actual')
 *   - season: string (default: '2025-26')
 *   - barValue: number (expected value from chart)
 *   - anchorEl: DOM element or {x, y} position for popover anchor
 */
export default function BarDrilldownPopover({
  isOpen,
  onClose,
  teamId,
  metric,
  dimension,
  context,
  bucket,
  tier,
  paceType = 'actual',
  season = '2025-26',
  barValue,
  anchorEl
}) {
  const navigate = useNavigate()
  const [games, setGames] = useState([])
  const [count, setCount] = useState(0)
  const [computedValue, setComputedValue] = useState(null)
  const [avgPace, setAvgPace] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [position, setPosition] = useState({ top: 0, left: 0 })

  // Calculate popover position based on anchor
  useEffect(() => {
    if (!isOpen || !anchorEl) return

    const calculatePosition = () => {
      if (anchorEl instanceof Element) {
        const rect = anchorEl.getBoundingClientRect()
        const scrollY = window.scrollY || window.pageYOffset
        const scrollX = window.scrollX || window.pageXOffset

        // Position popover to the right and slightly below the anchor
        setPosition({
          top: rect.bottom + scrollY + 8,
          left: rect.left + scrollX
        })
      } else if (anchorEl.x !== undefined && anchorEl.y !== undefined) {
        // Use direct coordinates
        setPosition({
          top: anchorEl.y + 8,
          left: anchorEl.x
        })
      }
    }

    calculatePosition()
    window.addEventListener('resize', calculatePosition)
    window.addEventListener('scroll', calculatePosition, true)

    return () => {
      window.removeEventListener('resize', calculatePosition)
      window.removeEventListener('scroll', calculatePosition, true)
    }
  }, [isOpen, anchorEl])

  // Fetch drilldown data when opened
  useEffect(() => {
    if (!isOpen) {
      return
    }

    const fetchDrilldownData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const params = new URLSearchParams({
          metric,
          dimension,
          context,
          pace_type: paceType,
          season
        })

        if (dimension === 'pace_bucket') {
          params.append('bucket', bucket)
        } else {
          params.append('tier', tier)
        }

        const response = await fetch(`/api/team/${teamId}/drilldown?${params}`)
        const data = await response.json()

        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Failed to load drilldown data')
        }

        setGames(data.games || [])
        setCount(data.count || 0)
        setComputedValue(data.bar_value)
        setAvgPace(data.avg_pace)
      } catch (err) {
        console.error('[Drilldown] Error fetching data:', err)
        setError(err.message)
      } finally {
        setIsLoading(false)
      }
    }

    fetchDrilldownData()
  }, [isOpen, teamId, metric, dimension, context, bucket, tier, paceType, season])

  // Handle game row click
  const handleGameClick = (gameId) => {
    navigate(`/game/${gameId}`)
    onClose()
  }

  // Get metric label
  const getMetricLabel = () => {
    if (metric === 'scoring') return 'PTS'
    if (metric === 'threept') return '3PT PTS'
    if (metric === 'turnovers') return 'TOV'
    return ''
  }

  // Get dimension label
  const getDimensionLabel = () => {
    if (dimension === 'pace_bucket') return bucket?.charAt(0).toUpperCase() + bucket?.slice(1) + ' Pace'
    if (dimension === 'defense_tier') return tier?.charAt(0).toUpperCase() + tier?.slice(1) + ' Defense'
    if (dimension === 'threept_def_tier') return tier?.charAt(0).toUpperCase() + tier?.slice(1) + ' 3PT Def'
    if (dimension === 'pressure_tier') return tier?.charAt(0).toUpperCase() + tier?.slice(1) + ' Pressure'
    return ''
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-25 z-40"
        onClick={onClose}
      />

      {/* Popover - Desktop: positioned near bar, Mobile: bottom sheet */}
      <div
        className="fixed z-50 bg-white dark:bg-gray-800 shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col
                   sm:rounded-lg sm:w-96 sm:max-h-96
                   max-sm:bottom-0 max-sm:left-0 max-sm:right-0 max-sm:w-full max-sm:max-h-[85vh] max-sm:rounded-t-2xl max-sm:pb-safe"
        style={{
          top: window.innerWidth >= 640 ? `${position.top}px` : 'auto',
          left: window.innerWidth >= 640 ? `${position.left}px` : '0',
          transform: window.innerWidth >= 640 ? 'translateX(-50%)' : 'none'
        }}
      >
        {/* Mobile drag handle */}
        <div className="sm:hidden flex justify-center pt-2 pb-1">
          <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
        </div>

        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {getDimensionLabel()} • {context === 'home' ? 'Home' : 'Away'}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {count} {count === 1 ? 'game' : 'games'} • Avg: {computedValue?.toFixed(1)} {getMetricLabel()}
              {avgPace && ` • ${avgPace} pace`}
            </p>
            <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 italic">
              Regular season + NBA Cup only
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          )}

          {error && (
            <div className="px-4 py-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {!isLoading && !error && games.length === 0 && (
            <div className="px-4 py-12 text-center text-sm text-gray-500 dark:text-gray-400">
              No games found
            </div>
          )}

          {!isLoading && !error && games.length > 0 && (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {games.map((game, index) => (
                <div
                  key={game.game_id || index}
                  onClick={() => handleGameClick(game.game_id)}
                  className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                        <span className={game.is_home ? 'text-blue-600' : 'text-orange-600'}>
                          {game.is_home ? 'vs' : '@'}
                        </span>
                        <span>{game.opponent_abbr}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(game.game_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                      </div>

                      <div className="mt-1 flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                        <span>
                          {game.team_pts}-{game.opp_pts} ({game.team_pts > game.opp_pts ? 'W' : 'L'})
                        </span>
                        {game.total_points && (
                          <span>Total: {game.total_points}</span>
                        )}
                      </div>
                    </div>

                    <div className="text-right ml-3">
                      {metric === 'scoring' && (
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                          {game.team_pts} PTS
                        </div>
                      )}

                      {metric === 'threept' && (
                        <div>
                          <div className="text-sm font-semibold text-gray-900 dark:text-white">
                            {game.three_pt_points} PTS
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {game.fg3m}/{game.fg3a} ({(game.fg3_pct * 100).toFixed(0)}%)
                          </div>
                        </div>
                      )}

                      {metric === 'turnovers' && (
                        <div className="text-sm font-semibold text-gray-900 dark:text-white">
                          {game.team_tov} TOV
                        </div>
                      )}

                      {/* Show tier/rank info if applicable */}
                      {game.opponent_rank && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          #{game.opponent_rank}
                        </div>
                      )}

                      {/* Show pace if pace dimension */}
                      {dimension === 'pace_bucket' && game.pace_value && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {game.pace_value.toFixed(1)} pace
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer - validation */}
        {!isLoading && !error && computedValue !== null && barValue !== null && (
          <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {Math.abs(computedValue - barValue) < 0.2 ? (
                <span className="text-green-600 dark:text-green-400">✓ Values match</span>
              ) : (
                <span className="text-yellow-600 dark:text-yellow-400">
                  Chart: {barValue.toFixed(1)} • Computed: {computedValue.toFixed(1)}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
