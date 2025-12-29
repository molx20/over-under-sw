/**
 * Decision Steps Helper Functions
 *
 * Pure calculation functions for the Empty Possessions Analysis decision framework.
 * Guides users from conversion metrics → market type → line check instructions.
 */

/**
 * Step 1: Determine edge type based on conversion score gap and combined average
 *
 * @param {number} conversionA - Team A blended conversion score (0-100)
 * @param {number} conversionB - Team B blended conversion score (0-100)
 * @param {object} teamAInfo - Team A metadata { abbreviation, full_name }
 * @param {object} teamBInfo - Team B metadata { abbreviation, full_name }
 * @returns {object} - { edgeType, winnerTeam, gap, combined, summary }
 *
 * Edge Types:
 *   - 'one-team-edge': gap >= 7 (significant advantage for one team)
 *   - 'both-teams-edge': gap < 7 AND combined >= 41 (both teams efficient)
 *   - 'low-conversion': combined < 38 (both teams inefficient)
 *   - 'mixed-neutral': default (moderate/unclear edge)
 */
export function computeStep1(conversionA, conversionB, teamAInfo, teamBInfo) {
  // Input validation and defaults
  const scoreA = typeof conversionA === 'number' ? conversionA : 0
  const scoreB = typeof conversionB === 'number' ? conversionB : 0

  // Get team names with fallbacks
  const teamAName = teamAInfo?.abbreviation || teamAInfo?.full_name || 'Team A'
  const teamBName = teamBInfo?.abbreviation || teamBInfo?.full_name || 'Team B'

  // Calculate gap and combined score
  const gap = Math.abs(scoreA - scoreB)
  const combined = (scoreA + scoreB) / 2

  // Determine winner (higher conversion score)
  const winnerTeam = scoreA > scoreB ? teamAName : teamBName
  const winnerScore = scoreA > scoreB ? scoreA : scoreB

  // Apply decision rules (priority order)
  let edgeType
  let summary

  if (gap >= 7) {
    // One-team edge: Significant gap suggests focusing on the stronger team
    edgeType = 'one-team-edge'
    summary = `One-team edge: ${winnerTeam} advantage (gap: ${gap.toFixed(1)})`
  } else if (gap < 7 && combined >= 41) {
    // Both-teams edge: Both teams efficient, good for game total
    edgeType = 'both-teams-edge'
    summary = `Both teams efficient: Game Total worth checking (combined: ${combined.toFixed(1)})`
  } else if (combined < 38) {
    // Low-conversion: Both teams inefficient, avoid overs
    edgeType = 'low-conversion'
    summary = `Low conversion environment: Avoid overs (combined: ${combined.toFixed(1)})`
  } else {
    // Mixed/neutral: Moderate scores, unclear edge
    edgeType = 'mixed-neutral'
    summary = `Mixed/neutral: Only bet if the line is discounted (gap: ${gap.toFixed(1)})`
  }

  return {
    edgeType,
    winnerTeam,
    winnerScore,
    gap,
    combined,
    summary
  }
}

/**
 * Step 2: Determine primary market type based on Step 1 edge classification
 *
 * @param {object} step1Result - Output from computeStep1
 * @returns {object} - { marketType, primaryMarket, confidence, recommendation }
 *
 * Market Types:
 *   - 'team-total': Check specific team's total line
 *   - 'game-total': Check combined game total line
 *   - 'pass': Pass on this game or lean under
 *   - 'discounted-only': Only bet if team total is discounted
 */
export function computeStep2(step1Result) {
  if (!step1Result || !step1Result.edgeType) {
    return {
      marketType: 'pass',
      primaryMarket: 'DATA UNAVAILABLE',
      confidence: 'low',
      recommendation: 'Missing conversion data - cannot make recommendation'
    }
  }

  const { edgeType, winnerTeam } = step1Result

  switch (edgeType) {
    case 'one-team-edge':
      return {
        marketType: 'team-total',
        primaryMarket: `${winnerTeam} TEAM TOTAL`,
        confidence: 'high',
        recommendation: `Strong conversion advantage for ${winnerTeam}. Focus on their team total line.`
      }

    case 'both-teams-edge':
      return {
        marketType: 'game-total',
        primaryMarket: 'GAME TOTAL',
        confidence: 'high',
        recommendation: 'Both teams showing efficient conversion. Game total OVER has potential.'
      }

    case 'low-conversion':
      return {
        marketType: 'pass',
        primaryMarket: 'PASS (or UNDER lean)',
        confidence: 'medium',
        recommendation: 'Low conversion environment suggests avoiding OVER bets. Consider UNDER or pass.'
      }

    case 'mixed-neutral':
      return {
        marketType: 'discounted-only',
        primaryMarket: `${winnerTeam} TEAM TOTAL (only if discounted)`,
        confidence: 'low',
        recommendation: `Unclear edge. Only consider ${winnerTeam} team total if line is discounted due to injuries or public fading.`
      }

    default:
      return {
        marketType: 'pass',
        primaryMarket: 'PASS',
        confidence: 'low',
        recommendation: 'Unable to determine market type'
      }
  }
}

/**
 * Step 3: Generate contextual line check instructions based on Step 2 market type
 *
 * @param {object} step2Result - Output from computeStep2
 * @returns {object} - { title, instructions, examples, warnings }
 */
export function getStep3Content(step2Result) {
  if (!step2Result || !step2Result.marketType) {
    return {
      title: 'Data Unavailable',
      instructions: ['Missing conversion data for this game.'],
      examples: [],
      warnings: ['Cannot provide line check instructions without conversion scores.']
    }
  }

  const { marketType, primaryMarket } = step2Result

  switch (marketType) {
    case 'team-total':
      return {
        title: 'Team Total Line Check',
        instructions: [
          `Open your sportsbook and find the ${primaryMarket} line`,
          'Compare the line to the team\'s Season PPG and Last 5 PPG (shown in the team card above)',
          'Check the opponent\'s conversion score - a lower opponent score means weaker defense, which supports the OVER',
          'Look for value: If the line is lower than their recent scoring average AND opponent defense is weak, consider the OVER',
          'Consider context: Injuries, back-to-back games, or rest days can impact scoring'
        ],
        examples: [
          'Example: If the team averages 115 PPG (season) and 118 PPG (last 5), and the line is 112.5, that\'s potential value for the OVER - especially if opponent conversion score is low (weak defense).',
          'Red flag: If their Last 5 PPG is trending DOWN while opponent conversion is HIGH (strong defense), the OVER is risky even if the line looks low.'
        ],
        warnings: [
          'Don\'t blindly bet OVER just because conversion is high - check if the LINE is actually beatable',
          'Factor in pace: A high-conversion team in a slow-paced game might not hit their total',
          'Watch for key injuries that could lower scoring output'
        ]
      }

    case 'game-total':
      return {
        title: 'Game Total Line Check',
        instructions: [
          `Open your sportsbook and find the ${primaryMarket} line`,
          'Look at BOTH teams\' Season PPG and Last 5 PPG',
          'Add their recent averages together - does it exceed the game total line?',
          'Check both teams\' conversion scores - both should be decent (ideally both above 40) to support the OVER',
          'Verify pace: If this is a fast-paced matchup, the OVER has stronger support'
        ],
        examples: [
          'Example: Team A averaging 118 PPG + Team B averaging 112 PPG = 230 combined. If the game total line is 225.5, and both teams have conversion scores above 45, the OVER has value.',
          'Red flag: If one team is trending DOWN in Last 5 scoring, or if pace is slow, the OVER is risky even if conversion looks good.'
        ],
        warnings: [
          'Require BOTH teams to have decent conversion scores - if only one team is efficient, focus on their team total instead',
          'Confirm with pace data - slow-paced games can kill OVER bets even with high conversion',
          'Watch for defensive adjustments or key defensive players returning from injury'
        ]
      }

    case 'pass':
      return {
        title: 'Pass or UNDER Lean',
        instructions: [
          'This game shows low conversion efficiency - avoid OVER bets',
          'If you must bet, consider the UNDER on game total or individual team totals',
          'Check the lines: If the sportsbook has set a low total (reflecting the poor conversion), there may not be value on the UNDER either',
          'Better to pass and wait for a clearer opportunity with stronger conversion metrics'
        ],
        examples: [
          'Example: Both teams with conversion scores under 35, game total line is 210.5. Even though the line is low, betting UNDER is risky because you\'re counting on poor offense to continue.',
          'Safe play: Pass on this game entirely and find matchups where at least one team has strong conversion (45+).'
        ],
        warnings: [
          'Low conversion doesn\'t guarantee UNDER wins - teams can still have outlier performances',
          'If both teams are cold shooters AND playing slow pace, the UNDER might hit, but it\'s low-confidence',
          'Avoid high-risk bets in low-conviction spots'
        ]
      }

    case 'discounted-only':
      return {
        title: 'Conditional Team Total (Discounted Lines Only)',
        instructions: [
          `Find the ${primaryMarket} line on your sportsbook`,
          'This is a MODERATE edge at best - only bet if you see clear line value',
          'Line value indicators: Injuries to key defenders on the opponent, public money fading the team (causing line to drop), or rest advantage',
          'Compare to Season/Last 5 PPG - the line should be noticeably lower than their average for you to have an edge',
          'If the line matches or exceeds their average, PASS - there\'s no edge here'
        ],
        examples: [
          'Example: Team averages 114 PPG (season) and 116 PPG (last 5). Line opens at 112.5 due to public fading them. That\'s a 3-4 point discount - potential value if opponent defense is weak.',
          'Red flag: Same team but line is 115.5. No discount, no value. Pass.'
        ],
        warnings: [
          'This is NOT a strong edge - be selective and disciplined',
          'Require external factors (injuries, rest, line movement) to support the bet',
          'If in doubt, pass and wait for a clearer one-team-edge or both-teams-edge spot'
        ]
      }

    default:
      return {
        title: 'Line Check Instructions',
        instructions: ['Unable to determine specific line check strategy.'],
        examples: [],
        warnings: ['Review conversion scores and try refreshing the data.']
      }
  }
}

/**
 * Get Tailwind color classes for Step 1 edge type
 *
 * @param {string} edgeType - Edge type from computeStep1
 * @returns {string} - Tailwind CSS class string
 */
export function getStep1DisplayColor(edgeType) {
  switch (edgeType) {
    case 'one-team-edge':
      return 'bg-green-100 border-green-300 text-green-700 dark:bg-green-900/20 dark:border-green-700 dark:text-green-400'
    case 'both-teams-edge':
      return 'bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900/20 dark:border-blue-700 dark:text-blue-400'
    case 'low-conversion':
      return 'bg-red-100 border-red-300 text-red-700 dark:bg-red-900/20 dark:border-red-700 dark:text-red-400'
    case 'mixed-neutral':
      return 'bg-yellow-100 border-yellow-300 text-yellow-700 dark:bg-yellow-900/20 dark:border-yellow-700 dark:text-yellow-400'
    default:
      return 'bg-gray-100 border-gray-300 text-gray-700 dark:bg-gray-900/20 dark:border-gray-700 dark:text-gray-400'
  }
}

/**
 * Get Tailwind color classes for Step 2 market type
 *
 * @param {string} marketType - Market type from computeStep2
 * @returns {string} - Tailwind CSS class string
 */
export function getStep2DisplayColor(marketType) {
  switch (marketType) {
    case 'team-total':
      return 'bg-purple-100 border-purple-300 text-purple-700 dark:bg-purple-900/20 dark:border-purple-700 dark:text-purple-400'
    case 'game-total':
      return 'bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900/20 dark:border-blue-700 dark:text-blue-400'
    case 'pass':
      return 'bg-gray-100 border-gray-300 text-gray-700 dark:bg-gray-900/20 dark:border-gray-700 dark:text-gray-400'
    case 'discounted-only':
      return 'bg-orange-100 border-orange-300 text-orange-700 dark:bg-orange-900/20 dark:border-orange-700 dark:text-orange-400'
    default:
      return 'bg-gray-100 border-gray-300 text-gray-700 dark:bg-gray-900/20 dark:border-gray-700 dark:text-gray-400'
  }
}
