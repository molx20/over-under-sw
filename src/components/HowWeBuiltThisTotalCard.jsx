import { useMemo } from 'react'
import {
  getPaceTier,
  getDefenseTier,
  getRestStatus,
  getShootoutMeter,
  formatPoints
} from '../utils/predictionHelpers'
import { EXPLANATION_TEXT } from '../utils/explanationText'

/**
 * HowWeBuiltThisTotalCard Component
 *
 * Shows a step-by-step breakdown of how the prediction total was calculated.
 * Explains each adjustment in simple, 5th grade reading level language.
 */
function HowWeBuiltThisTotalCard({ prediction, homeTeam, awayTeam }) {
  const calculations = useMemo(() => {
    if (!prediction || !prediction.breakdown) return null

    const { breakdown, factors, back_to_back_debug, matchup_adjustments } = prediction

    // Get smart baselines from backend (NEW!)
    const homeBaseline = breakdown.home_baseline || 0
    const awayBaseline = breakdown.away_baseline || 0

    // Game speed tier
    const paceTier = getPaceTier(factors?.game_pace || 100)

    // Defense tiers for each team
    const homeDefTier = getDefenseTier(breakdown.away_defense_rank) // Home offense vs away defense
    const awayDefTier = getDefenseTier(breakdown.home_defense_rank) // Away offense vs home defense
    const totalDefAdj = (breakdown.home_defense_quality_adjustment || 0) +
                        (breakdown.away_defense_quality_adjustment || 0)

    // Home edge & road trouble
    const homeEdge = breakdown.home_court_advantage || 0
    const roadTrouble = breakdown.road_penalty || 0

    // 3-Point shootout meter
    const shootoutTotal = breakdown.shootout_bonus || 0
    const shootoutMeter = getShootoutMeter(shootoutTotal)

    // Rest status for both teams
    const homeRest = getRestStatus(back_to_back_debug?.home)
    const awayRest = getRestStatus(back_to_back_debug?.away)
    const bothTired = homeRest.warning && awayRest.warning
    const oneTired = (homeRest.warning || awayRest.warning) && !bothTired
    const totalB2BAdjustment = ((back_to_back_debug?.home?.off_adj || 0) +
                                (back_to_back_debug?.home?.def_adj || 0) +
                                (back_to_back_debug?.away?.off_adj || 0) +
                                (back_to_back_debug?.away?.def_adj || 0))

    // Matchup bonuses
    const matchupTotal = matchup_adjustments?.total_adjustment || 0

    // Total change from baseline
    const totalChange = (breakdown.home_projected + breakdown.away_projected) -
                       (homeBaseline + awayBaseline)

    return {
      homeBaseline,
      awayBaseline,
      paceTier,
      homeDefTier,
      awayDefTier,
      totalDefAdj,
      homeEdge,
      roadTrouble,
      shootoutMeter,
      shootoutTotal,
      homeRest,
      awayRest,
      bothTired,
      oneTired,
      totalB2BAdjustment,
      matchupTotal,
      totalChange
    }
  }, [prediction, homeTeam, awayTeam])

  if (!calculations) return null

  // Reusable Badge component
  const Badge = ({ label, color, size = 'md' }) => {
    const colorClasses = {
      green: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
      red: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
      blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
      yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300',
      purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
      gray: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
    }

    const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'

    return (
      <span className={`inline-block rounded-full font-semibold ${colorClasses[color]} ${sizeClasses}`}>
        {label}
      </span>
    )
  }

  // Reusable Section component
  const Section = ({ title, children, icon }) => (
    <div className="border-b border-gray-200 dark:border-gray-700 pb-4 mb-4 last:border-0 last:pb-0 last:mb-0">
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-lg">{icon}</span>}
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h4>
      </div>
      {children}
    </div>
  )

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
      <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-4">
        How We Built This Total
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
        Here's the step-by-step breakdown of how we got to our prediction:
      </p>

      {/* 1. Starting Score */}
      <Section title="1. Starting Score" icon="🎯">
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
          {EXPLANATION_TEXT.startingScore.description}
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
              {awayTeam?.abbreviation || 'Away'} (Away)
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {calculations.awayBaseline.toFixed(1)}
            </div>
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
            <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
              {homeTeam?.abbreviation || 'Home'} (Home)
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {calculations.homeBaseline.toFixed(1)}
            </div>
          </div>
        </div>
      </Section>

      {/* 2. Game Speed */}
      <Section title="2. Game Speed" icon={calculations.paceTier.icon}>
        <div className="flex items-center justify-between mb-2">
          <Badge label={calculations.paceTier.label} color={calculations.paceTier.color} />
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {prediction.breakdown?.game_pace?.toFixed(1) || '100.0'} pace
          </span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          {EXPLANATION_TEXT.gameSpeed[calculations.paceTier.label.toLowerCase()]}
        </p>
      </Section>

      {/* 3. Defense Pressure */}
      <Section title="3. Defense Pressure" icon="🛡️">
        <div className="space-y-3 mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400">
                vs {awayTeam?.abbreviation || 'Away'} Defense:
              </span>
              <Badge label={calculations.awayDefTier.label} color={calculations.awayDefTier.color} size="sm" />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400">
                vs {homeTeam?.abbreviation || 'Home'} Defense:
              </span>
              <Badge label={calculations.homeDefTier.label} color={calculations.homeDefTier.color} size="sm" />
            </div>
          </div>
        </div>
        <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
          <span className="text-sm text-gray-700 dark:text-gray-300">Defense impact:</span>
          <span className={`text-lg font-bold ${calculations.totalDefAdj < 0 ? 'text-red-600 dark:text-red-400' : calculations.totalDefAdj > 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-600'}`}>
            {formatPoints(calculations.totalDefAdj)} pts
          </span>
        </div>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
          {EXPLANATION_TEXT.defensePressure.description}
        </p>
      </Section>

      {/* 4. Home Edge & Road Trouble */}
      <Section title="4. Home Edge & Road Trouble" icon="🏠">
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
          {EXPLANATION_TEXT.homeEdge.description}
        </p>
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Home boost ({homeTeam?.abbreviation}):
            </span>
            <span className="text-sm font-bold text-green-600 dark:text-green-400">
              {formatPoints(calculations.homeEdge)} pts
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Road penalty ({awayTeam?.abbreviation}):
            </span>
            <span className="text-sm font-bold text-red-600 dark:text-red-400">
              {formatPoints(calculations.roadTrouble)} pts
            </span>
          </div>
        </div>
      </Section>

      {/* 5. 3-Point Game Meter */}
      <Section title="5. 3-Point Game Meter" icon="🏀">
        <div className="flex items-center justify-between mb-2">
          <Badge label={calculations.shootoutMeter.label} color={calculations.shootoutMeter.color} />
          <span className="text-lg font-bold text-purple-600 dark:text-purple-400">
            {formatPoints(calculations.shootoutTotal)} pts
          </span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          {calculations.shootoutMeter.description}
        </p>
      </Section>

      {/* 6. Tired or Fresh? */}
      <Section title="6. Tired or Fresh?" icon="💪">
        <div className="space-y-2 mb-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {awayTeam?.abbreviation || 'Away'}:
            </span>
            <Badge
              label={calculations.awayRest.label}
              color={calculations.awayRest.color}
              size="sm"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {homeTeam?.abbreviation || 'Home'}:
            </span>
            <Badge
              label={calculations.homeRest.label}
              color={calculations.homeRest.color}
              size="sm"
            />
          </div>
        </div>
        <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
          <span className="text-sm text-gray-700 dark:text-gray-300">Fatigue impact:</span>
          <span className={`text-lg font-bold ${calculations.totalB2BAdjustment < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600'}`}>
            {formatPoints(calculations.totalB2BAdjustment)} pts
          </span>
        </div>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
          {calculations.bothTired ? EXPLANATION_TEXT.restStatus.bothTired :
           calculations.oneTired ? EXPLANATION_TEXT.restStatus.oneTired :
           EXPLANATION_TEXT.restStatus.fresh}
        </p>
      </Section>

      {/* 7. Little Matchup Bonuses */}
      <Section title="7. Little Matchup Bonuses" icon="⚔️">
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
          {EXPLANATION_TEXT.matchupBonuses.description}
        </p>
        <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
          <span className="text-sm text-gray-700 dark:text-gray-300">All matchup tweaks:</span>
          <span className={`text-lg font-bold ${calculations.matchupTotal > 0 ? 'text-green-600 dark:text-green-400' : calculations.matchupTotal < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600'}`}>
            {formatPoints(calculations.matchupTotal)} pts
          </span>
        </div>
      </Section>

      {/* 8. Ball Movement Bonuses (if applicable) */}
      {((prediction.breakdown?.assist_bonus || 0) > 0 || (prediction.breakdown?.turnover_pace_bonus || 0) > 0) && (
        <Section title="8. Ball Movement Bonuses" icon="🎯">
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
            {EXPLANATION_TEXT.bonuses?.description || 'Special bonuses for exceptional ball movement and game flow.'}
          </p>
          <div className="space-y-2">
            {(prediction.breakdown?.assist_bonus || 0) > 0 && (
              <div className="flex justify-between items-center bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">🏀</span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    High-assist fast game
                  </span>
                </div>
                <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                  {formatPoints(prediction.breakdown.assist_bonus)} pts
                </span>
              </div>
            )}
            {(prediction.breakdown?.turnover_pace_bonus || 0) > 0 && (
              <div className="flex justify-between items-center bg-purple-50 dark:bg-purple-900/20 rounded-lg p-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">⚡</span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Turnover pace impact
                  </span>
                </div>
                <span className="text-lg font-bold text-purple-600 dark:text-purple-400">
                  {formatPoints(prediction.breakdown.turnover_pace_bonus)} pts
                </span>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
            {EXPLANATION_TEXT.bonuses?.details || 'These bonuses apply to the overall game scoring potential based on team playing styles.'}
          </p>
        </Section>
      )}

      {/* 9. Total Change & Final */}
      <div className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 rounded-lg p-4 mt-4">
        {/* Calculation Formula */}
        <div className="mb-4 p-3 bg-white/50 dark:bg-gray-900/50 rounded-lg">
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">
            How we calculated it:
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-bold text-green-600 dark:text-green-400">
              {prediction.breakdown.home_projected}
            </span>
            <span className="text-gray-500">+</span>
            <span className="font-bold text-blue-600 dark:text-blue-400">
              {prediction.breakdown.away_projected}
            </span>
            {((prediction.breakdown?.assist_bonus || 0) + (prediction.breakdown?.turnover_pace_bonus || 0)) > 0 && (
              <>
                <span className="text-gray-500">+</span>
                <span className="font-bold text-purple-600 dark:text-purple-400">
                  {((prediction.breakdown?.assist_bonus || 0) + (prediction.breakdown?.turnover_pace_bonus || 0)).toFixed(1)}
                </span>
                <span className="text-xs text-gray-500">(bonuses)</span>
              </>
            )}
            <span className="text-gray-500">=</span>
            <span className="font-bold text-primary-600 dark:text-primary-400 text-lg">
              {prediction.predicted_total}
            </span>
          </div>
        </div>

        {/* Total Change from Starting Score */}
        <div className="flex justify-between items-center mb-3">
          <span className="text-base font-semibold text-gray-900 dark:text-white">
            Total Change from Starting Score:
          </span>
          <span className={`text-2xl font-bold ${calculations.totalChange > 0 ? 'text-green-600 dark:text-green-400' : calculations.totalChange < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600'}`}>
            {formatPoints(calculations.totalChange)} pts
          </span>
        </div>

        {/* Final Predicted Total */}
        <div className="border-t border-primary-200 dark:border-primary-700 pt-3">
          <div className="flex justify-between items-center">
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              Final Predicted Total:
            </span>
            <span className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {prediction.predicted_total}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HowWeBuiltThisTotalCard
