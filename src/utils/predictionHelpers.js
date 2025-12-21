/**
 * Prediction Helpers
 *
 * Helper functions for deriving user-friendly labels and classifications
 * from prediction model data. All functions designed to work with the
 * prediction API response structure.
 */

/**
 * Get pace tier classification from game pace value
 * @param {number} pace - Game pace (possessions per 48 minutes)
 * @returns {object} - {label, color, icon, description}
 */
export function getPaceTier(pace) {
  if (!pace || pace === 0) {
    return { label: 'Normal', color: 'gray', icon: '➡️', description: 'Average NBA game speed' }
  }

  if (pace >= 102) {
    return {
      label: 'Fast',
      color: 'green',
      icon: '⚡',
      description: 'More possessions mean more chances to score'
    }
  }

  if (pace <= 97) {
    return {
      label: 'Slow',
      color: 'blue',
      icon: '🐢',
      description: 'Fewer possessions mean fewer points'
    }
  }

  return {
    label: 'Normal',
    color: 'gray',
    icon: '➡️',
    description: 'Average NBA game speed'
  }
}

/**
 * Get defense tier classification from defensive rank
 * @param {number} rank - Defensive rank (1-30, where 1 is best)
 * @returns {object} - {label, color, description}
 */
export function getDefenseTier(rank) {
  if (!rank || rank === 0) {
    return {
      label: 'Unknown',
      color: 'gray',
      description: 'Defense info not available'
    }
  }

  if (rank <= 10) {
    return {
      label: 'Elite',
      color: 'red',
      description: 'One of the best defenses in the league - very hard to score against'
    }
  }

  if (rank <= 20) {
    return {
      label: 'Average',
      color: 'yellow',
      description: 'Middle-of-the-pack defense'
    }
  }

  return {
    label: 'Weak',
    color: 'green',
    description: 'Easier to score against this defense'
  }
}

/**
 * Get rest status from back-to-back data
 * @param {object} b2bData - Back-to-back debug data from prediction
 * @returns {object} - {label, color, days, warning, description}
 */
export function getRestStatus(b2bData) {
  if (!b2bData) {
    return {
      label: 'Fresh',
      color: 'green',
      days: '2+',
      warning: false,
      description: 'Well-rested and ready to play'
    }
  }

  if (b2bData.is_b2b) {
    return {
      label: 'Back-to-Back',
      color: 'red',
      days: '0',
      warning: true,
      description: 'Played yesterday - might be tired'
    }
  }

  // Assume 1 day rest if not B2B but has data
  return {
    label: '1 Day Rest',
    color: 'yellow',
    days: '1',
    warning: false,
    description: 'Played 2 days ago'
  }
}

/**
 * Get offense heat status by comparing recent vs season scoring
 * @param {number} recentPPG - Recent points per game (last 5)
 * @param {number} seasonPPG - Season average points per game
 * @returns {object} - {label, color, icon, description}
 */
export function getOffenseHeat(recentPPG, seasonPPG) {
  if (!recentPPG || !seasonPPG) {
    return {
      label: 'Normal',
      color: 'gray',
      icon: '➡️',
      description: 'Scoring at their usual rate'
    }
  }

  const diff = recentPPG - seasonPPG

  if (diff >= 5) {
    return {
      label: 'Hot',
      color: 'red',
      icon: '🔥',
      description: `Scoring ${diff.toFixed(1)} more points than usual`
    }
  }

  if (diff <= -5) {
    return {
      label: 'Cold',
      color: 'blue',
      icon: '❄️',
      description: `Scoring ${Math.abs(diff).toFixed(1)} fewer points than usual`
    }
  }

  return {
    label: 'Normal',
    color: 'gray',
    icon: '➡️',
    description: 'Scoring at their normal rate'
  }
}

/**
 * Get 3-point shootout meter level from shootout bonus
 * @param {number} shootoutBonus - Total shootout bonus points
 * @returns {object} - {label, color, description}
 */
export function getShootoutMeter(shootoutBonus) {
  if (!shootoutBonus) shootoutBonus = 0

  if (shootoutBonus >= 5) {
    return {
      label: 'High',
      color: 'red',
      description: 'Lots of 3-pointers expected!'
    }
  }

  if (shootoutBonus >= 2) {
    return {
      label: 'Medium',
      color: 'yellow',
      description: 'Some extra 3-pointers expected'
    }
  }

  return {
    label: 'Low',
    color: 'green',
    description: 'Normal amount of 3-point shooting'
  }
}

/**
 * Format points value with +/- sign
 * @param {number} value - Point value to format
 * @returns {string} - Formatted string like "+2.5" or "-1.0"
 */
export function formatPoints(value) {
  if (!value || value === 0) return '0.0'
  const formatted = Math.abs(value).toFixed(1)
  return value > 0 ? `+${formatted}` : `-${formatted}`
}

/**
 * Get home/road record label from win percentage
 * @param {number} winPct - Win percentage (0.0 to 1.0)
 * @param {boolean} isHome - True if home team, false if road
 * @returns {object} - {label, color, description}
 */
export function getRecordLabel(winPct, isHome = true) {
  if (!winPct && winPct !== 0) {
    return { label: 'Unknown', color: 'gray', description: 'Record not available' }
  }

  if (isHome) {
    // Home team thresholds
    if (winPct >= 0.60) {
      return { label: 'Strong', color: 'green', description: 'Great at home' }
    }
    if (winPct >= 0.40) {
      return { label: 'Average', color: 'yellow', description: 'Average home record' }
    }
    return { label: 'Weak', color: 'red', description: 'Struggles at home' }
  } else {
    // Road team thresholds
    if (winPct >= 0.50) {
      return { label: 'Great', color: 'green', description: 'Plays well on the road' }
    }
    if (winPct >= 0.35) {
      return { label: 'OK', color: 'yellow', description: 'Average road record' }
    }
    return { label: 'Bad', color: 'red', description: 'Struggles on the road' }
  }
}

/**
 * Get matchup style chips based on game characteristics
 * @param {object} prediction - Full prediction object
 * @param {object} homeTeam - Home team object
 * @param {object} awayTeam - Away team object
 * @returns {array} - Array of chip objects with {label, color, description}
 */
export function getMatchupStyleChips(prediction, homeTeam, awayTeam) {
  const chips = []

  if (!prediction || !prediction.factors) return chips

  const { factors, breakdown, matchup_adjustments } = prediction

  // 1. Game Speed Chip
  const paceTier = getPaceTier(factors.game_pace || 100)
  chips.push({
    label: `${paceTier.label} Game`,
    color: paceTier.color,
    description: paceTier.description
  })

  // 2. 3-Point Game Chip (if high shootout potential)
  const shootoutTotal = breakdown?.shootout_bonus || 0
  if (shootoutTotal >= 3) {
    chips.push({
      label: '3-Point Game',
      color: 'purple',
      description: 'Both teams love shooting threes'
    })
  }

  // 3. Foul-Heavy Chip (if high foul rate matchup adjustment)
  const foulRate = matchup_adjustments?.adjustments?.foul_rate || 0
  if (foulRate > 3) {
    chips.push({
      label: 'Foul-Heavy',
      color: 'orange',
      description: 'Expect lots of free throws'
    })
  }

  // 4. Defense Battle Chip (if both teams have elite defense)
  const homeDefElite = breakdown?.home_defense_rank && breakdown.home_defense_rank <= 10
  const awayDefElite = breakdown?.away_defense_rank && breakdown.away_defense_rank <= 10
  if (homeDefElite && awayDefElite) {
    chips.push({
      label: 'Defense Battle',
      color: 'red',
      description: 'Two great defenses make it tough to score'
    })
  }

  // 5. Pace Mismatch Chip (if teams play at very different speeds)
  const paceVariance = factors.pace_variance || 0
  if (paceVariance > 8) {
    chips.push({
      label: 'Pace Clash',
      color: 'blue',
      description: 'Fast team meets slow team'
    })
  }

  return chips
}

/**
 * Parse record string to get wins and losses
 * @param {string} recordStr - Record string like "15-5" or "N/A"
 * @returns {object} - {wins, losses, total, pct} or null
 */
export function parseRecord(recordStr) {
  if (!recordStr || recordStr === 'N/A' || recordStr === 'Unknown') {
    return null
  }

  const parts = recordStr.split('-')
  if (parts.length !== 2) return null

  const wins = parseInt(parts[0])
  const losses = parseInt(parts[1])

  if (isNaN(wins) || isNaN(losses)) return null

  const total = wins + losses
  const pct = total > 0 ? wins / total : 0

  return { wins, losses, total, pct }
}
