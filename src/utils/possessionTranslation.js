/**
 * Possession Translation Utilities
 *
 * Helper functions to translate rates/percentages into intuitive counts
 * for pregame matchup analysis.
 */

/**
 * Normalize percentage value to fraction (0..1)
 * Handles both percentage (43.5) and fraction (0.435) formats
 *
 * @param {number} value - The percentage/fraction value
 * @returns {number} Normalized fraction between 0 and 1
 */
export function normalizePct(value) {
  if (value == null || isNaN(value)) return 0

  // If value > 1.5, assume it's a percentage (e.g., 43.5%)
  // Otherwise treat as fraction (e.g., 0.435)
  if (value > 1.5) {
    return value / 100
  }
  return value
}

/**
 * Round number to 1 decimal place
 *
 * @param {number} x - Number to round
 * @returns {number} Rounded number
 */
export function round1(x) {
  if (x == null || isNaN(x)) return 0
  return Math.round(x * 10) / 10
}

/**
 * Format number with sign (+/-) and 1 decimal
 *
 * @param {number} x - Number to format
 * @returns {string} Formatted string like "+1.2" or "-0.7"
 */
export function formatSigned(x) {
  if (x == null || isNaN(x)) return '—'

  const rounded = round1(x)
  if (rounded > 0) {
    return `+${rounded.toFixed(1)}`
  } else if (rounded < 0) {
    return rounded.toFixed(1)
  } else {
    return '0.0'
  }
}

/**
 * Calculate expected empty possessions from projected possessions and empty %
 *
 * @param {number} projectedPossessions - Total projected possessions
 * @param {number} combinedEmptyPct - Combined empty % (will be normalized)
 * @returns {number} Expected empty possessions
 */
export function calculateExpectedEmptyPossessions(projectedPossessions, combinedEmptyPct) {
  if (!projectedPossessions || !combinedEmptyPct) return 0

  const emptyFraction = normalizePct(combinedEmptyPct)
  return round1(projectedPossessions * emptyFraction)
}

/**
 * Calculate expected scoring possessions
 *
 * @param {number} projectedPossessions - Total projected possessions
 * @param {number} expectedEmptyPossessions - Expected empty possessions
 * @returns {number} Expected scoring possessions
 */
export function calculateExpectedScoringPossessions(projectedPossessions, expectedEmptyPossessions) {
  if (!projectedPossessions) return 0

  return round1(projectedPossessions - expectedEmptyPossessions)
}

/**
 * Calculate delta empty possessions from TO impact
 *
 * @param {number} teamPossessions - Team's projected possessions
 * @param {number} deltaToPct - Change in TO% (percentage points)
 * @returns {number} Delta empty possessions from turnovers
 */
export function calculateDeltaEmptyTO(teamPossessions, deltaToPct) {
  if (!teamPossessions || deltaToPct == null) return null

  // Delta empty possessions = possessions * (delta_to_pct / 100)
  return round1(teamPossessions * (deltaToPct / 100))
}

/**
 * Calculate delta empty possessions from OREB impact
 * Uses temporary anchor of 0.55 misses per possession until backend provides better data
 *
 * @param {number} teamPossessions - Team's projected possessions
 * @param {number} deltaOrebPct - Change in OREB% (percentage points)
 * @returns {number} Delta empty possessions from offensive rebounds (negative means fewer empties)
 */
export function calculateDeltaEmptyOREB(teamPossessions, deltaOrebPct) {
  if (!teamPossessions || deltaOrebPct == null) return null

  // Temporary placeholder: assume 0.55 misses per possession
  const MISSES_PER_POSSESSION = 0.55
  const misses = teamPossessions * MISSES_PER_POSSESSION

  // Negative because more OREBs = fewer empty possessions
  return round1(-(misses * (deltaOrebPct / 100)))
}

/**
 * Get color class for delta empties
 * Positive empties (more empties) = caution/orange
 * Negative empties (fewer empties) = green
 *
 * @param {number} delta - Delta value
 * @returns {string} Tailwind color classes
 */
export function getDeltaEmptyColor(delta) {
  if (delta == null || delta === 0) {
    return 'text-gray-600 dark:text-gray-400'
  }

  if (delta > 0) {
    // More empty possessions = bad (orange/caution)
    return 'text-orange-600 dark:text-orange-400'
  } else {
    // Fewer empty possessions = good (green)
    return 'text-green-600 dark:text-green-400'
  }
}

/**
 * Get color class for delta vs league average
 * Above league avg = red (bad), below = green (good)
 *
 * @param {number} delta - Delta from league average
 * @returns {string} Tailwind color classes
 */
export function getDeltaVsLeagueColor(delta) {
  if (delta == null || Math.abs(delta) < 0.5) {
    return 'text-gray-600 dark:text-gray-400'
  }

  if (delta > 0) {
    // Above league average empty rate = bad (red)
    return 'text-red-600 dark:text-red-400'
  } else {
    // Below league average empty rate = good (green)
    return 'text-green-600 dark:text-green-400'
  }
}

/**
 * Round to whole number
 *
 * @param {number} x - Number to round
 * @returns {number} Whole number
 */
export function roundWhole(x) {
  if (x == null || isNaN(x)) return 0
  if (Math.abs(x) < 0.5) return 0
  return Math.round(x)
}
