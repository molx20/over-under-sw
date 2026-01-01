/**
 * SimilarTeamsChips Component
 *
 * Displays similar teams as chips with expand/collapse functionality
 * Shows up to 6 team chips with "View all (n)" button to expand
 */

import { useState } from 'react'

function SimilarTeamsChips({ teams, compact = false }) {
  const [showAll, setShowAll] = useState(false)

  if (!teams || teams.length === 0) return null

  const displayTeams = showAll ? teams : teams.slice(0, 6)
  const hasMore = teams.length > 6

  return (
    <div className={`mt-2 ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="flex items-center gap-1 mb-1">
        <span className="text-gray-500 dark:text-gray-400 font-medium">Similar teams:</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {displayTeams.map(team => (
          <span
            key={team}
            className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs font-medium"
          >
            {team}
          </span>
        ))}
        {hasMore && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="inline-flex items-center px-2 py-0.5 rounded bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs font-medium hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
          >
            {showAll ? 'Show less' : `View all (${teams.length})`}
          </button>
        )}
      </div>
    </div>
  )
}

export default SimilarTeamsChips
