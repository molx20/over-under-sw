import { Link } from 'react-router-dom'

function GameCard({ game }) {
  const { home_team, away_team, game_time, game_id } = game

  return (
    <Link to={`/game/${game_id}`}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-xl transition-all cursor-pointer border-l-4 border-primary-500">
        {/* Matchup Header */}
        <div className="mb-4">
          <div className="text-center mb-3">
            <span className="inline-block px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-semibold rounded-full">
              MATCHUP ANALYTICS
            </span>
          </div>

          {/* Teams */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">AWAY</span>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  {away_team.abbreviation}
                </span>
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {away_team.name}
              </span>
            </div>

            <div className="flex justify-center">
              <span className="text-gray-400 dark:text-gray-600 font-bold">@</span>
            </div>

            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">HOME</span>
                <span className="text-lg font-bold text-gray-900 dark:text-white">
                  {home_team.abbreviation}
                </span>
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {home_team.name}
              </span>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-gray-700 my-4"></div>

        {/* Call to Action */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-semibold transition-colors">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            View War Room
          </div>
        </div>

        {/* Game Time */}
        {game_time && (
          <div className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400">
            <svg className="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {game_time}
          </div>
        )}
      </div>
    </Link>
  )
}

export default GameCard
