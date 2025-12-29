import React from 'react'

/**
 * ScoringMixBar - Horizontal stacked bar showing 3PT/2PT/FT percentage breakdown
 *
 * Props:
 *   - data: Object with { pct_3pt, pct_2pt, pct_ft, games, avg_pts }
 *   - label: String label for the bar (e.g., "Last 5")
 *   - showValues: Boolean to show percentage values on segments (default: true)
 */
function ScoringMixBar({ data, label, showValues = true }) {
  if (!data || data.games === 0) {
    return (
      <div className="flex items-center gap-3 h-10">
        <div className="w-16 text-xs font-medium text-gray-600 dark:text-gray-400">
          {label}
        </div>
        <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded h-full flex items-center justify-center">
          <span className="text-xs text-gray-500 dark:text-gray-500">No data</span>
        </div>
      </div>
    )
  }

  const { pct_3pt, pct_2pt, pct_ft, games, avg_pts } = data

  // Ensure percentages sum to 100 (accounting for rounding)
  const total = pct_3pt + pct_2pt + pct_ft
  const normalized_3pt = total > 0 ? (pct_3pt / total) * 100 : 0
  const normalized_2pt = total > 0 ? (pct_2pt / total) * 100 : 0
  const normalized_ft = total > 0 ? (pct_ft / total) * 100 : 0

  // Determine if values should be shown (segment > 10% width)
  const show3ptValue = showValues && normalized_3pt >= 10
  const show2ptValue = showValues && normalized_2pt >= 10
  const showFtValue = showValues && normalized_ft >= 10

  return (
    <div className="flex items-center gap-3 h-10">
      {/* Label */}
      <div className="w-16 text-xs font-medium text-gray-700 dark:text-gray-300">
        {label}
      </div>

      {/* Stacked Bar */}
      <div className="flex-1 flex h-full rounded overflow-hidden shadow-sm">
        {/* 3PT Segment (Green) */}
        {normalized_3pt > 0 && (
          <div
            className="bg-green-500 dark:bg-green-600 flex items-center justify-center relative group"
            style={{ width: `${normalized_3pt}%` }}
          >
            {show3ptValue && (
              <span className="text-xs font-semibold text-white">
                {pct_3pt.toFixed(1)}%
              </span>
            )}
            {/* Hover tooltip */}
            <div className="absolute bottom-full mb-2 hidden group-hover:block bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-10">
              3PT: {pct_3pt.toFixed(1)}%
            </div>
          </div>
        )}

        {/* 2PT Segment (Blue) */}
        {normalized_2pt > 0 && (
          <div
            className="bg-blue-500 dark:bg-blue-600 flex items-center justify-center relative group"
            style={{ width: `${normalized_2pt}%` }}
          >
            {show2ptValue && (
              <span className="text-xs font-semibold text-white">
                {pct_2pt.toFixed(1)}%
              </span>
            )}
            {/* Hover tooltip */}
            <div className="absolute bottom-full mb-2 hidden group-hover:block bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-10">
              2PT: {pct_2pt.toFixed(1)}%
            </div>
          </div>
        )}

        {/* FT Segment (Orange) */}
        {normalized_ft > 0 && (
          <div
            className="bg-orange-500 dark:bg-orange-600 flex items-center justify-center relative group"
            style={{ width: `${normalized_ft}%` }}
          >
            {showFtValue && (
              <span className="text-xs font-semibold text-white">
                {pct_ft.toFixed(1)}%
              </span>
            )}
            {/* Hover tooltip */}
            <div className="absolute bottom-full mb-2 hidden group-hover:block bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-10">
              FT: {pct_ft.toFixed(1)}%
            </div>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="w-20 text-right">
        <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
          {avg_pts.toFixed(1)} ppg
        </div>
        <div className="text-[10px] text-gray-500 dark:text-gray-500">
          {games} {games === 1 ? 'game' : 'games'}
        </div>
      </div>
    </div>
  )
}

export default ScoringMixBar
