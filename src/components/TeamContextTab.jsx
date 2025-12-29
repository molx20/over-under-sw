/**
 * TeamContextTab Component
 *
 * Wrapper component for Team Context tab in Deep Dive
 * Combines: TeamFormIndex, MatchupIndicators, VolatilityProfile, EmptyPossessionsGauge
 */

import TeamFormIndex from './TeamFormIndex'
import MatchupIndicators from './MatchupIndicators'
import VolatilityProfile from './VolatilityProfile'
import EmptyPossessionsGauge from './EmptyPossessionsGauge'

function TeamContextTab({
  homeTeam,
  awayTeam,
  homeStats,
  awayStats,
  homeRecentGames,
  awayRecentGames,
  emptyPossessionsData
}) {
  return (
    <div className="space-y-6">
      {/* Section 1: Team Form Index */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Team Form Index
        </h2>
        <TeamFormIndex
          homeTeam={homeTeam}
          awayTeam={awayTeam}
          homeStats={homeStats}
          awayStats={awayStats}
          homeRecentGames={homeRecentGames}
          awayRecentGames={awayRecentGames}
        />
      </div>

      {/* Section 2: Matchup Indicators */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Matchup Indicators
        </h2>
        <MatchupIndicators
          homeTeam={homeTeam}
          awayTeam={awayTeam}
          homeStats={homeStats}
          awayStats={awayStats}
        />
      </div>

      {/* Section 3: Volatility Profile */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Volatility Profile
        </h2>
        <VolatilityProfile
          homeTeam={homeTeam}
          awayTeam={awayTeam}
          homeRecentGames={homeRecentGames}
          awayRecentGames={awayRecentGames}
          homeStats={homeStats}
          awayStats={awayStats}
        />
      </div>

      {/* Section 4: Empty Possessions Analysis */}
      {emptyPossessionsData && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Empty Possessions Analysis
          </h2>
          <EmptyPossessionsGauge
            homeTeam={homeTeam}
            awayTeam={awayTeam}
            emptyPossessionsData={emptyPossessionsData}
          />
        </div>
      )}
    </div>
  )
}

export default TeamContextTab
