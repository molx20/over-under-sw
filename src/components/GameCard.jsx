import { Link } from 'react-router-dom'

function GameCard({ game }) {
  const { home_team, away_team, prediction, game_time, game_id } = game

  if (!prediction) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
        <div className="text-center text-gray-500 dark:text-gray-400">
          Loading prediction...
        </div>
      </div>
    )
  }

  const { predicted_total, betting_line, recommendation, confidence, breakdown } = prediction

  // Determine color based on recommendation
  const getRecommendationColor = () => {
    if (recommendation === 'OVER') return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
    if (recommendation === 'UNDER') return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
    return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20'
  }

  const getBorderColor = () => {
    if (recommendation === 'OVER') return 'border-l-4 border-green-500'
    if (recommendation === 'UNDER') return 'border-l-4 border-red-500'
    return 'border-l-4 border-yellow-500'
  }

  return (
    <Link to={`/game/${game_id}`}>
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-xl transition-all cursor-pointer ${getBorderColor()}`}>
        {/* Teams */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">AWAY</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {away_team.abbreviation}
              </span>
            </div>
            <span className="text-lg font-bold text-gray-700 dark:text-gray-300">
              {breakdown.away_projected}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">HOME</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {home_team.abbreviation}
              </span>
            </div>
            <span className="text-lg font-bold text-gray-700 dark:text-gray-300">
              {breakdown.home_projected}
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-gray-700 my-4"></div>

        {/* Prediction Info */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Betting Line</span>
            <span className="font-semibold text-gray-900 dark:text-white">{betting_line}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Predicted Total</span>
            <span className="font-semibold text-gray-900 dark:text-white">{predicted_total}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">Difference</span>
            <span className={`font-bold ${breakdown.difference > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {breakdown.difference > 0 ? '+' : ''}{breakdown.difference}
            </span>
          </div>
        </div>

        {/* Recommendation Badge */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center">
            <div className={`px-4 py-2 rounded-full font-bold text-sm ${getRecommendationColor()}`}>
              {recommendation}
            </div>
            <div className="flex flex-col items-end">
              <span className="text-xs text-gray-500 dark:text-gray-400">Confidence</span>
              <span className="font-bold text-lg text-gray-900 dark:text-white">{confidence}%</span>
            </div>
          </div>
        </div>

        {/* Game Time */}
        {game_time && (
          <div className="mt-3 text-center text-xs text-gray-500 dark:text-gray-400">
            {game_time}
          </div>
        )}
      </div>
    </Link>
  )
}

export default GameCard
