/**
 * Decision Engine for NBA Game Totals
 *
 * Client-side decision logic using interpretable thresholds
 * No ML - fully deterministic and explainable
 *
 * Based on analysis showing top 3 total drivers:
 * 1. Combined FT Points (10.3% avg lift)
 * 2. Combined Paint Points (7.3% avg lift)
 * 3. Combined eFG% (6.4% avg lift)
 */

/**
 * Determine driver status based on thresholds
 * @param {number} value - Driver value
 * @param {number} greenThreshold - Threshold for green status
 * @param {number} redThreshold - Threshold for red status
 * @returns {'green'|'yellow'|'red'} Status indicator
 */
function getDriverStatus(value, greenThreshold, redThreshold) {
  if (value >= greenThreshold) return 'green'
  if (value < redThreshold) return 'red'
  return 'yellow'
}

/**
 * Make Over/Under/Pass decision based on game drivers
 *
 * @param {Object} drivers - Driver metrics
 * @param {Object} drivers.ftPoints - Free throw points { value, status, target }
 * @param {Object} drivers.paintPoints - Paint points { value, status, target }
 * @param {Object} drivers.efg - Effective FG% { value, status, target }
 * @param {Object} archetype - Archetype matchup data { label, confidence, sampleSize }
 * @param {Object} volatility - Volatility data { index, label }
 * @param {Object} marginRisk - Margin risk data { label }
 * @returns {Object} Decision { call, confidence, confidenceLabel, reason, reasoning }
 */
export function makeDecision(drivers, archetype = {}, volatility = {}, marginRisk = {}) {
  // Extract driver statuses
  const ftStatus = drivers.ftPoints?.status || 'yellow'
  const paintStatus = drivers.paintPoints?.status || 'yellow'
  const efgStatus = drivers.efg?.status || 'yellow'

  // Count greens, reds, yellows
  const statuses = [ftStatus, paintStatus, efgStatus]
  const greenCount = statuses.filter(s => s === 'green').length
  const redCount = statuses.filter(s => s === 'red').length
  const yellowCount = 3 - greenCount - redCount

  // Initialize decision variables
  let call = 'PASS'
  let confidence = 50
  const reasoning = []

  // BASE DECISION LOGIC

  // OVER logic: at least 2 greens + not blowout risk
  if (greenCount >= 2 && marginRisk.label !== 'Blowout Risk') {
    call = 'OVER'
    confidence = 60 + (greenCount * 5) // 70-75 base confidence
    reasoning.push({
      icon: '✓',
      text: `${greenCount} of 3 drivers in green zone (strong Over signals)`,
      type: 'positive'
    })
  }

  // UNDER logic: at least 2 reds + not high FT
  if (redCount >= 2 && ftStatus !== 'green') {
    call = 'UNDER'
    confidence = 60 + (redCount * 5) // 70-75 base confidence
    reasoning.push({
      icon: '✓',
      text: `${redCount} of 3 drivers in red zone (strong Under signals)`,
      type: 'positive'
    })
  }

  // PASS logic: mostly yellow OR conflicting signals OR low archetype confidence + volatility
  if (
    yellowCount >= 2 ||
    (greenCount >= 1 && redCount >= 1) ||
    (archetype.confidence === 'low' && (volatility.index || 5) > 5)
  ) {
    call = 'PASS'
    confidence = 40
    reasoning.push({
      icon: '⚠',
      text: 'Conflicting signals or insufficient data for confident call',
      type: 'warning'
    })
  }

  // ARCHETYPE ADJUSTMENTS

  if (archetype.confidence === 'high' && archetype.label) {
    const archetypeLabel = archetype.label.toLowerCase()

    // Favorable Over matchups (fast-paced, offensive teams)
    const overFavorableTerms = ['pace push', 'elite', 'fast-paced', 'three-point hunt', 'balanced high-assist']
    const isOverFavorable = overFavorableTerms.some(term => archetypeLabel.includes(term))

    if (call === 'OVER' && isOverFavorable) {
      confidence += 10
      reasoning.push({
        icon: '🎯',
        text: `Archetype matchup supports Over (${archetype.label})`,
        type: 'positive'
      })
    }

    // Favorable Under matchups (defensive grinders, slow pace)
    const underFavorableTerms = ['defensive grind', 'slow', 'low-scoring']
    const isUnderFavorable = underFavorableTerms.some(term => archetypeLabel.includes(term))

    if (call === 'UNDER' && isUnderFavorable) {
      confidence += 10
      reasoning.push({
        icon: '🎯',
        text: `Archetype matchup supports Under (${archetype.label})`,
        type: 'positive'
      })
    }
  } else if (archetype.confidence === 'low') {
    confidence -= 5
    reasoning.push({
      icon: '⚠',
      text: `Low archetype confidence (${archetype.sampleSize || 0} games) reduces certainty`,
      type: 'warning'
    })
  }

  // MARGIN RISK ADJUSTMENTS

  if (marginRisk.label === 'Blowout Risk') {
    if (call === 'OVER') {
      confidence -= 15
      reasoning.push({
        icon: '⚠',
        text: 'Blowout risk reduces Over confidence (garbage time concern)',
        type: 'warning'
      })
    } else if (call === 'UNDER') {
      confidence += 5
      reasoning.push({
        icon: '✓',
        text: 'Blowout risk supports Under (shortened rotations)',
        type: 'positive'
      })
    }
  } else {
    reasoning.push({
      icon: '⚖',
      text: 'Competitive game expected (full possessions for both teams)',
      type: 'neutral'
    })
  }

  // VOLATILITY ADJUSTMENTS

  const volatilityIndex = volatility.index || 5

  if (volatilityIndex > 6) {
    confidence -= 10
    reasoning.push({
      icon: '📊',
      text: `High volatility (${volatilityIndex.toFixed(1)}/10) increases uncertainty`,
      type: 'warning'
    })
  } else if (volatilityIndex <= 3) {
    confidence += 5
    reasoning.push({
      icon: '📊',
      text: `Low volatility (${volatilityIndex.toFixed(1)}/10) increases confidence`,
      type: 'positive'
    })
  }

  // CONFLICTING SIGNALS DETECTION

  if ((greenCount >= 2 && redCount >= 1) || (redCount >= 2 && greenCount >= 1)) {
    confidence -= 10
    reasoning.push({
      icon: '⚠',
      text: 'Mixed driver signals reduce confidence',
      type: 'warning'
    })
  }

  // DRIVER-SPECIFIC INSIGHTS

  // FT Points is the #1 driver - emphasize it
  if (ftStatus === 'green' && call === 'OVER') {
    reasoning.push({
      icon: '🎯',
      text: `Free throws trending high (${drivers.ftPoints.value} combined, above target)`,
      type: 'positive'
    })
  } else if (ftStatus === 'red' && call === 'UNDER') {
    reasoning.push({
      icon: '✓',
      text: `Free throws trending low (${drivers.ftPoints.value} combined, below target)`,
      type: 'positive'
    })
  }

  // Paint Points is the #2 driver
  if (paintStatus === 'green' && call === 'OVER') {
    reasoning.push({
      icon: '🏀',
      text: `Both teams paint-heavy (${drivers.paintPoints.value} combined)`,
      type: 'positive'
    })
  } else if (paintStatus === 'red' && call === 'UNDER') {
    reasoning.push({
      icon: '✓',
      text: `Low paint scoring expected (${drivers.paintPoints.value} combined)`,
      type: 'positive'
    })
  }

  // eFG% context
  if (efgStatus === 'yellow') {
    reasoning.push({
      icon: '⚠',
      text: `Shooting efficiency moderate (${drivers.efg.value}% eFG)`,
      type: 'warning'
    })
  }

  // CONFIDENCE LABEL

  const confidenceLabel = confidence >= 75 ? 'HIGH' : confidence >= 60 ? 'MEDIUM' : 'LOW'

  // REASON STRING (Summary)

  let reason = ''

  if (call === 'OVER') {
    reason = `${greenCount} driver${greenCount > 1 ? 's' : ''} in target range.`
    if (archetype.confidence === 'high' && reasoning.some(r => r.text.includes('supports Over'))) {
      reason += ' Strong archetype match.'
    }
    if (marginRisk.label === 'Competitive') {
      reason += ' Competitive game expected.'
    }
  } else if (call === 'UNDER') {
    reason = `${redCount} driver${redCount > 1 ? 's' : ''} below target.`
    if (marginRisk.label === 'Blowout Risk') {
      reason += ' Blowout risk supports Under.'
    }
  } else {
    reason = `Mixed signals (${greenCount} green, ${redCount} red, ${yellowCount} yellow). Pass recommended.`
  }

  // Clamp confidence to 30-95 range
  confidence = Math.min(95, Math.max(30, Math.round(confidence)))

  return {
    call,
    confidence,
    confidenceLabel,
    reason,
    reasoning: reasoning.slice(0, 6) // Limit to top 6 most important reasons
  }
}

/**
 * Helper to get driver status for display
 * Used when building drivers object in GamePage
 */
export function calculateDriverStatus(value, metric) {
  const thresholds = {
    ftPoints: { green: 38, red: 33 },
    paintPoints: { green: 68, red: 60 },
    efg: { green: 59, red: 53 }
  }

  const threshold = thresholds[metric]
  if (!threshold) return 'yellow'

  return getDriverStatus(value, threshold.green, threshold.red)
}
