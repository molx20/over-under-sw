import PredictionExplainerCard from './PredictionExplainerCard'
import HowWeBuiltThisTotalCard from './HowWeBuiltThisTotalCard'

/**
 * PredictionPanel Component
 *
 * Displays the Prediction Breakdown, Key Factors, How We Built This Total Card, and Explainer Card
 */
function PredictionPanel({ prediction, homeTeam, awayTeam, homeStats, awayStats }) {
  if (!prediction || !prediction.breakdown) return null

  return (
    <div className="space-y-6">
      {/* Model Output Summary */}
      {prediction.betting_line && prediction.predicted_total && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-4">Model Output</h3>
          <div className="flex flex-col sm:flex-row justify-center items-center sm:space-x-8 space-y-4 sm:space-y-0">
            <div className="text-center">
              <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-1">Betting Line</div>
              <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">{prediction.betting_line}</div>
            </div>
            <div className="text-2xl sm:text-3xl text-gray-400 rotate-90 sm:rotate-0">→</div>
            <div className="text-center">
              <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-1">Predicted Total</div>
              <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">{prediction.predicted_total}</div>
            </div>
          </div>
          {prediction.recommendation && (
            <div className="mt-4 flex justify-center">
              <div className={`px-6 py-2 rounded-full text-lg font-bold text-white ${
                prediction.recommendation === 'OVER' ? 'bg-green-500' :
                prediction.recommendation === 'UNDER' ? 'bg-red-500' : 'bg-yellow-500'
              }`}>
                {prediction.recommendation}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Prediction Breakdown + Key Factors side-by-side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {/* Prediction Breakdown */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-3 sm:mb-4">Prediction Breakdown</h3>
          <div className="space-y-2 sm:space-y-3">
            <div className="flex justify-between text-sm sm:text-base">
              <span className="text-gray-600 dark:text-gray-400">Home Projected ({homeTeam?.abbreviation || 'Home'})</span>
              <span className="font-semibold text-gray-900 dark:text-white">{prediction.breakdown?.home_projected || 'N/A'}</span>
            </div>
            <div className="flex justify-between text-sm sm:text-base">
              <span className="text-gray-600 dark:text-gray-400">Away Projected ({awayTeam?.abbreviation || 'Away'})</span>
              <span className="font-semibold text-gray-900 dark:text-white">{prediction.breakdown?.away_projected || 'N/A'}</span>
            </div>
            <div className="flex justify-between text-sm sm:text-base">
              <span className="text-gray-600 dark:text-gray-400">Game Pace</span>
              <span className="font-semibold text-gray-900 dark:text-white">{prediction.breakdown?.game_pace || 'N/A'}</span>
            </div>
            {prediction.betting_line && prediction.breakdown?.difference !== undefined && (
              <div className="flex justify-between pt-2 sm:pt-3 border-t border-gray-200 dark:border-gray-700 text-sm sm:text-base">
                <span className="text-gray-600 dark:text-gray-400">Total Difference</span>
                <span className={`font-bold ${prediction.breakdown.difference > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {prediction.breakdown.difference > 0 ? '+' : ''}{prediction.breakdown.difference}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Key Factors */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-3 sm:mb-4">Key Factors</h3>
          <div className="space-y-2 sm:space-y-3">
            <div className="flex justify-between text-sm sm:text-base">
              <span className="text-gray-600 dark:text-gray-400">Home Team Pace ({homeTeam?.abbreviation || 'Home'})</span>
              <span className="font-semibold text-gray-900 dark:text-white">{prediction.factors?.home_pace ? prediction.factors.home_pace.toFixed(1) : 'N/A'}</span>
            </div>
            <div className="flex justify-between text-sm sm:text-base">
              <span className="text-gray-600 dark:text-gray-400">Away Team Pace ({awayTeam?.abbreviation || 'Away'})</span>
              <span className="font-semibold text-gray-900 dark:text-white">{prediction.factors?.away_pace ? prediction.factors.away_pace.toFixed(1) : 'N/A'}</span>
            </div>
            <div className="flex justify-between text-sm sm:text-base">
              <span className="text-gray-600 dark:text-gray-400">Projected Game Pace</span>
              <span className="font-semibold text-gray-900 dark:text-white">{prediction.factors?.game_pace || 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* How We Built This Total Card */}
      <HowWeBuiltThisTotalCard
        prediction={prediction}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
      />

      {/* Why This Prediction? Explainer Card */}
      <PredictionExplainerCard
        prediction={prediction}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homeStats={homeStats}
        awayStats={awayStats}
      />
    </div>
  )
}

export default PredictionPanel
