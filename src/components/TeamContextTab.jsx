/**
 * TeamContextTab Component
 *
 * Wrapper component for Team Context tab in Deep Dive
 * Combines: TeamFormIndex, EmptyPossessionsGauge, OpponentResistancePanel
 */

import TeamFormIndex from './TeamFormIndex'
import EmptyPossessionsGauge from './EmptyPossessionsGauge'
import OpponentResistancePanel from './OpponentResistancePanel'

function TeamContextTab({
  homeTeam,
  awayTeam,
  homeStats,
  awayStats,
  homeRecentGames,
  awayRecentGames,
  emptyPossessionsData,
  opponentResistanceData
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

      {/* Section 2: Empty Possessions Analysis */}
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

      {/* Section 3: Opponent Resistance */}
      {opponentResistanceData && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
          <OpponentResistancePanel
            homeTeam={homeTeam}
            awayTeam={awayTeam}
            resistanceData={opponentResistanceData}
          />
        </div>
      )}
    </div>
  )
}

export default TeamContextTab
