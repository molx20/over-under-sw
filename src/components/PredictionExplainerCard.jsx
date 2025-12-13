import { useState } from 'react'

/**
 * Helper function to generate plain-English explanation bullets
 * based on the model's prediction and underlying factors
 */
function generateExplanation(prediction, homeTeam, awayTeam, homeStats, awayStats) {
  const bullets = []
  const { recommendation, breakdown, factors } = prediction

  // Extract key metrics
  const predictedTotal = prediction.predicted_total
  const bettingLine = prediction.betting_line
  const difference = breakdown?.difference || 0
  const gamePace = factors?.game_pace || 100
  const paceVariance = factors?.pace_variance || 0

  // Get defensive rankings from breakdown (backend now provides these)
  const homeDefRank = breakdown?.home_defense_rank || null
  const awayDefRank = breakdown?.away_defense_rank || null

  // Determine if pace is fast/slow
  const isFastPace = gamePace > 102
  const isSlowPace = gamePace < 98  // Changed from 97 to 98 to catch more slow games

  // Determine defensive strength using rankings (1-10 = elite, 11-20 = good, 21-30 = weak)
  const homeDefStrong = homeDefRank && homeDefRank <= 10
  const awayDefStrong = awayDefRank && awayDefRank <= 10
  const bothDefsStrong = homeDefStrong && awayDefStrong
  const homeDefGood = homeDefRank && homeDefRank <= 15
  const awayDefGood = awayDefRank && awayDefRank <= 15
  const bothDefsGood = homeDefGood && awayDefGood
  const bothDefsWeak = homeDefRank && awayDefRank && homeDefRank > 20 && awayDefRank > 20

  // Check adjustments
  const homeCourtAdv = breakdown?.home_court_advantage || 0
  const roadPenalty = breakdown?.road_penalty || 0
  const turnoverAdjHome = breakdown?.home_turnover_adjustment || 0
  const turnoverAdjAway = breakdown?.away_turnover_adjustment || 0
  const shootoutBonus = breakdown?.shootout_bonus || 0

  // Check recent form
  const homeTrends = prediction.home_last5_trends
  const awayTrends = prediction.away_last5_trends

  // ===== UNDER Explanations =====
  if (recommendation === 'UNDER') {
    // Elite defenses (top 10)
    if (bothDefsStrong) {
      bullets.push(`Both teams have elite defenses (${homeTeam?.abbreviation} #${homeDefRank}, ${awayTeam?.abbreviation} #${awayDefRank}), which typically leads to lower-scoring games.`)
    } else if (homeDefStrong) {
      bullets.push(`${homeTeam?.abbreviation} has an elite defense (ranked #${homeDefRank}), making it tough for opponents to score.`)
    } else if (awayDefStrong) {
      bullets.push(`${awayTeam?.abbreviation} has an elite defense (ranked #${awayDefRank}), making it tough for opponents to score.`)
    } else if (bothDefsGood) {
      // Both have good (top 15) defenses
      bullets.push(`Both teams have strong defenses (${homeTeam?.abbreviation} #${homeDefRank}, ${awayTeam?.abbreviation} #${awayDefRank}), limiting scoring opportunities.`)
    } else if (homeDefGood) {
      bullets.push(`${homeTeam?.abbreviation} has a strong defense (ranked #${homeDefRank}), which helps keep totals lower.`)
    } else if (awayDefGood) {
      bullets.push(`${awayTeam?.abbreviation} has a strong defense (ranked #${awayDefRank}), which helps keep totals lower.`)
    }

    // Slow pace
    if (isSlowPace) {
      bullets.push(`The projected game pace is slow (${gamePace.toFixed(1)} possessions), meaning fewer scoring chances for both teams.`)
    }

    // Defense quality adjustments
    const totalDefAdj = (breakdown?.home_defense_quality_adjustment || 0) + (breakdown?.away_defense_quality_adjustment || 0)
    if (totalDefAdj < -5) {
      bullets.push(`Strong defensive matchups are expected to reduce scoring by about ${Math.abs(totalDefAdj).toFixed(1)} points.`)
    }

    // Cold shooting trends
    if (homeTrends && awayTrends) {
      const homeCold = homeTrends.avg_ppg_last5 < (factors?.home_ppg || 0) - 3
      const awayCold = awayTrends.avg_ppg_last5 < (factors?.away_ppg || 0) - 3
      if (homeCold && awayCold) {
        bullets.push('Both teams have been scoring below their season averages in recent games.')
      } else if (awayCold) {
        bullets.push(`${awayTeam?.abbreviation} has been cold lately, averaging ${awayTrends.avg_ppg_last5.toFixed(1)} PPG in their last 5 games.`)
      }
    }

    // Road penalty heavy
    if (roadPenalty < -3) {
      bullets.push(`The road team struggles away from home, averaging ${Math.abs(roadPenalty).toFixed(1)} fewer points on the road.`)
    }

    // Matchup adjustments favoring under
    const matchupAdj = prediction?.matchup_adjustments?.total_adjustment || 0
    if (matchupAdj < -4) {
      bullets.push(`This specific matchup historically produces ${Math.abs(matchupAdj).toFixed(1)} fewer points than expected.`)
    }

    // If still empty, add generic explanation
    if (bullets.length === 0) {
      bullets.push(`The model projects ${predictedTotal} points, which is ${Math.abs(difference).toFixed(1)} points below the betting line.`)
      bullets.push('Multiple factors suggest this game will be lower scoring than expected.')
    }
  }

  // ===== OVER Explanations =====
  else if (recommendation === 'OVER') {
    // Fast pace
    if (isFastPace) {
      bullets.push(`The game is expected to be fast-paced (${gamePace.toFixed(1)} possessions), giving both teams more chances to score.`)
    }

    // Weak defenses (rank 21-30)
    if (bothDefsWeak) {
      bullets.push(`Both teams have weak defenses (${homeTeam?.abbreviation} #${homeDefRank}, ${awayTeam?.abbreviation} #${awayDefRank}), which usually leads to higher-scoring games.`)
    } else if (homeDefRank && homeDefRank > 20) {
      bullets.push(`${homeTeam?.abbreviation} struggles defensively (ranked #${homeDefRank}), making it easier for opponents to score.`)
    } else if (awayDefRank && awayDefRank > 20) {
      bullets.push(`${awayTeam?.abbreviation} struggles defensively (ranked #${awayDefRank}), making it easier for opponents to score.`)
    }

    // High turnover game
    if (turnoverAdjHome > 2 || turnoverAdjAway > 2) {
      bullets.push('Higher turnovers are expected, which can lead to more fast-break points and transition scoring.')
    }

    // Shootout bonus
    if (shootoutBonus > 3) {
      bullets.push('Both teams have strong three-point shooting, and the matchup favors a potential shootout.')
    }

    // Hot shooting trends
    if (homeTrends && awayTrends) {
      const homeHot = homeTrends.avg_ppg_last5 > (factors?.home_ppg || 0) + 3
      const awayHot = awayTrends.avg_ppg_last5 > (factors?.away_ppg || 0) + 3
      if (homeHot && awayHot) {
        bullets.push('Both teams have been scoring more than usual in their recent games.')
      } else if (homeHot) {
        bullets.push(`${homeTeam?.abbreviation} has been hot lately, averaging ${homeTrends.avg_ppg_last5.toFixed(1)} points in their last 5 games.`)
      } else if (awayHot) {
        bullets.push(`${awayTeam?.abbreviation} has been hot lately, averaging ${awayTrends.avg_ppg_last5.toFixed(1)} points in their last 5 games.`)
      }
    }

    // Strong home court advantage
    if (homeCourtAdv > 4) {
      bullets.push(`${homeTeam?.abbreviation} has a strong home court advantage, averaging ${homeCourtAdv} extra points at home.`)
    }

    // If still empty, add generic explanation
    if (bullets.length === 0) {
      bullets.push(`The model projects ${predictedTotal} points, which is ${difference} points above the betting line.`)
      bullets.push('This suggests the game will be higher scoring than the sportsbook expects.')
    }
  }

  // ===== NO BET Explanations =====
  else if (recommendation === 'NO BET') {
    // Close to betting line
    if (Math.abs(difference) < 3) {
      bullets.push(`The model's prediction (${predictedTotal}) is very close to the betting line (${bettingLine}).`)
      bullets.push('When the numbers are this tight, there is no clear betting edge.')
    }

    // High variance / conflicting signals
    if (paceVariance > 5) {
      bullets.push('The teams play at very different paces, making the game harder to predict.')
    }

    // Mixed defensive signals
    if (homeDefStrong && !awayDefStrong) {
      bullets.push('One team has a strong defense while the other is weak, creating conflicting signals.')
    }

    // Data quality issues
    if (breakdown?.home_data_quality === 'limited' || breakdown?.away_data_quality === 'limited') {
      bullets.push('Limited game data for one or both teams makes this prediction less reliable.')
    }

    // Inconsistent trends
    if (homeTrends && awayTrends) {
      const homeVolatile = Math.abs(homeTrends.avg_ppg_last5 - (factors?.home_ppg || 0)) > 5
      const awayVolatile = Math.abs(awayTrends.avg_ppg_last5 - (factors?.away_ppg || 0)) > 5
      if (homeVolatile || awayVolatile) {
        bullets.push('Recent performance is inconsistent, making the outcome harder to predict.')
      }
    }

    // If still empty, add generic explanation
    if (bullets.length === 0) {
      bullets.push('The model does not have enough confidence to recommend a bet on this game.')
      bullets.push('There are too many conflicting factors or the margin is too small.')
    }
  }

  // Limit to 5 bullets max
  return bullets.slice(0, 5)
}

/**
 * PredictionExplainerCard Component
 *
 * Displays a plain-English explanation of why the model made its prediction
 * Collapsible accordion-style card, collapsed by default
 */
function PredictionExplainerCard({ prediction, homeTeam, awayTeam, homeStats, awayStats }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!prediction || !prediction.recommendation) return null

  const bullets = generateExplanation(prediction, homeTeam, awayTeam, homeStats, awayStats)
  const recommendation = prediction.recommendation

  // Determine title based on recommendation
  let title = 'Why This Prediction?'
  if (recommendation === 'OVER') {
    title = 'Why the model likes the OVER:'
  } else if (recommendation === 'UNDER') {
    title = 'Why the model likes the UNDER:'
  } else if (recommendation === 'NO BET') {
    title = 'Why the model says NO BET:'
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 sm:p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
          Why This Prediction?
        </h3>
        <svg
          className={`w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Body - Collapsible */}
      {isExpanded && (
        <div className="px-4 sm:px-6 pb-4 sm:pb-6 border-t border-gray-200 dark:border-gray-700">
          <div className="pt-4">
            <p className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white mb-3">
              {title}
            </p>
            <ul className="space-y-2">
              {bullets.map((bullet, index) => (
                <li key={index} className="flex items-start text-sm sm:text-base text-gray-700 dark:text-gray-300">
                  <span className="text-primary-600 dark:text-primary-400 mr-2 mt-0.5">•</span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default PredictionExplainerCard
