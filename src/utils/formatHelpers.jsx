/**
 * Shared formatting utilities for NBA stats display
 */

/**
 * Format a delta value with color coding
 *
 * @param {number} delta - The delta value to format
 * @param {boolean} invertColors - If true, negative is good (for defensive stats)
 * @param {boolean} isPercentage - If true, append '%' symbol
 * @returns {JSX.Element} Formatted delta with appropriate color
 */
export const formatDelta = (delta, invertColors = false, isPercentage = false) => {
  if (!delta || Math.abs(delta) < 0.1) {
    return <span className="text-gray-500 dark:text-gray-400">(+0.0{isPercentage ? '%' : ''})</span>
  }

  // For defensive stats, negative is good (invertColors = true)
  const isPositive = invertColors ? delta < 0 : delta > 0
  const colorClass = isPositive
    ? 'text-green-600 dark:text-green-400'
    : 'text-red-600 dark:text-red-400'

  return (
    <span className={colorClass}>
      ({delta > 0 ? '+' : ''}{delta.toFixed(1)}{isPercentage ? '%' : ''})
    </span>
  )
}

/**
 * Determine if a stat should use inverted color coding
 * (lower is better for defensive metrics)
 *
 * @param {string} statKey - The stat key (e.g., 'def_rtg', 'ppg')
 * @returns {boolean} True if colors should be inverted
 */
export const shouldInvertColors = (statKey) => {
  const defensiveStats = ['def_rtg', 'opp_ppg']
  return defensiveStats.includes(statKey)
}

/**
 * Determine if a stat is a percentage stat that should display with % symbol
 *
 * @param {string} statKey - The stat key (e.g., 'fg_pct', 'ppg')
 * @returns {boolean} True if stat is a percentage
 */
export const isPercentageStat = (statKey) => {
  const percentageStats = ['fg_pct', 'three_pct', 'ft_pct']
  return percentageStats.includes(statKey)
}
