import { Link } from 'react-router-dom'

function GameCard({ game }) {
  const { home_team, away_team, game_time, game_id } = game

  return (
    <Link to={`/game/${game_id}`} className="block">
      <div className="game-card-mobile group">
        {/* Teams - Simplified Layout */}
        <div className="mb-4">
          {/* Away Team */}
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center space-x-3">
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Away
              </span>
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                {away_team.abbreviation}
              </span>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[140px]">
              {away_team.name}
            </span>
          </div>

          {/* VS Indicator */}
          <div className="flex items-center justify-center my-2">
            <div className="flex items-center space-x-2 text-gray-400 dark:text-gray-600">
              <div className="h-px w-12 bg-current"></div>
              <span className="text-xs font-bold">VS</span>
              <div className="h-px w-12 bg-current"></div>
            </div>
          </div>

          {/* Home Team */}
          <div className="flex items-center justify-between mt-2.5">
            <div className="flex items-center space-x-3">
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Home
              </span>
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                {home_team.abbreviation}
              </span>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[140px]">
              {home_team.name}
            </span>
          </div>
        </div>

        {/* Game Time */}
        {game_time && (
          <div className="flex items-center justify-center py-2 px-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-4">
            <svg className="w-4 h-4 text-gray-500 dark:text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {game_time}
            </span>
          </div>
        )}

        {/* CTA Button - Full Width, Large Touch Target */}
        <button className="w-full min-h-[48px] bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white rounded-xl font-semibold text-base shadow-sm active:scale-[0.98] transition-all flex items-center justify-center space-x-2 group-hover:shadow-md">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span>View Analysis</span>
        </button>
      </div>
    </Link>
  )
}

export default GameCard
