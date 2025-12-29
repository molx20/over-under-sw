import { useMemo } from 'react'

/**
 * MatchupSimilarityCard Component
 *
 * Displays team similarity and cluster information including:
 * - Cluster assignments for both teams
 * - Matchup type description
 * - Similar teams for reference
 * - Cluster-based adjustments applied to prediction
 */
function MatchupSimilarityCard({ prediction, homeTeam, awayTeam }) {
  const similarityData = useMemo(() => {
    if (!prediction?.similarity) {
      return null
    }

    return prediction.similarity
  }, [prediction])

  // Don't render if no similarity data
  if (!similarityData) {
    return null
  }

  // Cluster color mapping
  const getClusterColor = (clusterId) => {
    const colors = {
      1: 'green',   // Elite Pace Pushers
      2: 'orange',  // Paint Dominators
      3: 'purple',  // Three-Point Hunters
      4: 'blue',    // Defensive Grinders
      5: 'gray',    // Balanced High-Assist
      6: 'yellow'   // ISO-Heavy
    }
    return colors[clusterId] || 'gray'
  }

  // Get cluster badge classes
  const getClusterBadgeClasses = (color) => {
    const baseClasses = 'px-3 py-1 rounded-full text-xs font-semibold'
    const colorClasses = {
      green: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      orange: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
      purple: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      gray: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
      yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
    }
    return `${baseClasses} ${colorClasses[color] || colorClasses.gray}`
  }

  const homeCluster = similarityData.home_cluster
  const awayCluster = similarityData.away_cluster
  const matchupType = similarityData.matchup_type
  const adjustments = similarityData.adjustments

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">
          Team Similarity Profile
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Playstyle clusters and matchup dynamics
        </p>
      </div>

      {/* Matchup Type Banner */}
      <div className="mb-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-primary-600 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span className="font-semibold text-primary-900 dark:text-primary-100">
            {matchupType}
          </span>
        </div>
      </div>

      {/* Team Clusters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Home Team Cluster */}
        {homeCluster && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-gray-900 dark:text-white">
                {homeTeam}
              </h4>
              <div className="flex flex-col items-end gap-1">
                <span className={getClusterBadgeClasses(getClusterColor(homeCluster.id))}>
                  {homeCluster.name}
                </span>
                {homeCluster.secondary_name && (
                  <span className={`${getClusterBadgeClasses(getClusterColor(homeCluster.secondary_id))} opacity-70 text-[10px] border-dashed`}>
                    {homeCluster.secondary_name}
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {homeCluster.description}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-500">
              <div>
                {homeCluster.confidence_label && (
                  <span className={`font-medium ${
                    homeCluster.confidence_label === 'High' ? 'text-green-600 dark:text-green-400' :
                    homeCluster.confidence_label === 'Low' ? 'text-red-600 dark:text-red-400' :
                    'text-yellow-600 dark:text-yellow-400'
                  }`}>
                    Confidence: {homeCluster.confidence_label}
                  </span>
                )}
              </div>
              {homeCluster.fit_score !== null && homeCluster.fit_score !== undefined && (
                <div title={homeCluster.secondary_fit_score ? `Secondary: ${homeCluster.secondary_fit_score.toFixed(0)}` : ''}>
                  Fit: {homeCluster.fit_score.toFixed(0)}
                </div>
              )}
            </div>
            {/* Similar Teams */}
            {similarityData.home_similar_teams && similarityData.home_similar_teams.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Similar Teams:
                </div>
                <div className="space-y-1">
                  {similarityData.home_similar_teams.map((team, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="text-gray-600 dark:text-gray-400">
                        {team.team_abbreviation}
                      </span>
                      <span className="text-gray-500 dark:text-gray-500">
                        {team.similarity_score?.toFixed(0)}% similar
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Away Team Cluster */}
        {awayCluster && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-gray-900 dark:text-white">
                {awayTeam}
              </h4>
              <div className="flex flex-col items-end gap-1">
                <span className={getClusterBadgeClasses(getClusterColor(awayCluster.id))}>
                  {awayCluster.name}
                </span>
                {awayCluster.secondary_name && (
                  <span className={`${getClusterBadgeClasses(getClusterColor(awayCluster.secondary_id))} opacity-70 text-[10px] border-dashed`}>
                    {awayCluster.secondary_name}
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {awayCluster.description}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-500">
              <div>
                {awayCluster.confidence_label && (
                  <span className={`font-medium ${
                    awayCluster.confidence_label === 'High' ? 'text-green-600 dark:text-green-400' :
                    awayCluster.confidence_label === 'Low' ? 'text-red-600 dark:text-red-400' :
                    'text-yellow-600 dark:text-yellow-400'
                  }`}>
                    Confidence: {awayCluster.confidence_label}
                  </span>
                )}
              </div>
              {awayCluster.fit_score !== null && awayCluster.fit_score !== undefined && (
                <div title={awayCluster.secondary_fit_score ? `Secondary: ${awayCluster.secondary_fit_score.toFixed(0)}` : ''}>
                  Fit: {awayCluster.fit_score.toFixed(0)}
                </div>
              )}
            </div>
            {/* Similar Teams */}
            {similarityData.away_similar_teams && similarityData.away_similar_teams.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Similar Teams:
                </div>
                <div className="space-y-1">
                  {similarityData.away_similar_teams.map((team, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="text-gray-600 dark:text-gray-400">
                        {team.team_abbreviation}
                      </span>
                      <span className="text-gray-500 dark:text-gray-500">
                        {team.similarity_score?.toFixed(0)}% similar
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Cluster Adjustments */}
      {adjustments && (
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            Cluster-Based Adjustments
          </h4>
          <div className="space-y-2">
            {/* Pace Adjustment */}
            {adjustments.pace_adjustment !== 0 && (
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0 w-20">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    adjustments.pace_adjustment > 0
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    Pace {adjustments.pace_adjustment > 0 ? '+' : ''}{adjustments.pace_adjustment?.toFixed(1)}
                  </span>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  {adjustments.pace_explanation}
                </p>
              </div>
            )}

            {/* Scoring Adjustments */}
            {(adjustments.home_scoring_adjustment !== 0 || adjustments.away_scoring_adjustment !== 0) && (
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0 w-20">
                  <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                    Scoring
                  </span>
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  <p>{adjustments.scoring_explanation}</p>
                  <p className="mt-1">
                    {homeTeam}: {adjustments.home_scoring_adjustment > 0 ? '+' : ''}{adjustments.home_scoring_adjustment?.toFixed(1)} |
                    {' '}{awayTeam}: {adjustments.away_scoring_adjustment > 0 ? '+' : ''}{adjustments.away_scoring_adjustment?.toFixed(1)}
                  </p>
                </div>
              </div>
            )}

            {/* Paint/Perimeter Adjustments */}
            {(adjustments.home_paint_perimeter_adjustment !== 0 || adjustments.away_paint_perimeter_adjustment !== 0) && (
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0 w-20">
                  <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400">
                    Style
                  </span>
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  <p>{adjustments.paint_perimeter_explanation}</p>
                  <p className="mt-1">
                    {homeTeam}: {adjustments.home_paint_perimeter_adjustment > 0 ? '+' : ''}{adjustments.home_paint_perimeter_adjustment?.toFixed(1)} |
                    {' '}{awayTeam}: {adjustments.away_paint_perimeter_adjustment > 0 ? '+' : ''}{adjustments.away_paint_perimeter_adjustment?.toFixed(1)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default MatchupSimilarityCard
