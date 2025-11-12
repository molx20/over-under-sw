import { Link } from 'react-router-dom'

function GameCard({ game }) {
  const { home_team, away_team, prediction, game_time, game_id } = game

  // Show matchup preview if prediction not yet available
  if (!prediction) {
    return (
      <Link to={`/game/${game_id}`}>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-xl transition-all cursor-pointer border-l-4 border-gray-400">
          {/* Teams */}
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">AWAY</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {away_team.abbreviation}
                </span>
              </div>
              {away_team.score !== null && away_team.score !== undefined && (
                <span className="text-lg font-bold text-gray-700 dark:text-gray-300">
                  {away_team.score}
                </span>
              )}
            </div>
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">HOME</span>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {home_team.abbreviation}
                </span>
              </div>
              {home_team.score !== null && home_team.score !== undefined && (
                <span className="text-lg font-bold text-gray-700 dark:text-gray-300">
                  {home_team.score}
                </span>
              )}
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700 my-4"></div>

          {/* Call to Action */}
          <div className="text-center py-4">
            <div className="text-gray-600 dark:text-gray-400 text-sm mb-2">
              Click to view detailed prediction
            </div>
            <div className="inline-flex items-center justify-center px-4 py-2 bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 rounded-lg text-sm font-medium">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Generate Prediction
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
