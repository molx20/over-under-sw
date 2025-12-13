/**
 * MatchupDNA Component - AI-Generated Matchup Breakdown
 *
 * Displays narrative-driven matchup analysis with 7 structured sections:
 * 1. Pace & Game Flow (5 sentences)
 * 2. Offensive Style Matchup (5 sentences)
 * 3. Shooting & 3PT Profile (5 sentences)
 * 4. Rim Pressure & Paint Matchup (5 sentences)
 * 5. Recent Form Check (5 sentences)
 * 6. Volatility Profile (5 sentences)
 * 7. Matchup DNA Summary (8-10 sentences)
 *
 * All sections are AI-generated and cached for performance.
 */
function MatchupDNA({ matchupSummary, homeTeam, awayTeam }) {
  // Handle loading/missing state
  if (!matchupSummary) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
        <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-4">
          Matchup Breakdown
        </h2>
        <div className="text-center py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mx-auto"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mx-auto"></div>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
            Generating matchup analysis...
          </p>
        </div>
      </div>
    )
  }

  // Section component for consistent formatting
  const Section = ({ title, text, icon }) => (
    <div className="mb-6 pb-6 border-b border-gray-200 dark:border-gray-700 last:border-0">
      <div className="flex items-center gap-2 mb-3">
        {icon && <span className="text-2xl">{icon}</span>}
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
        </h3>
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
        {text}
      </p>
    </div>
  )

  // Extract sections from summary
  const {
    pace_and_flow,
    offensive_style,
    shooting_profile,
    rim_and_paint,
    recent_form,
    volatility_profile,
    matchup_dna_summary,
    model_reference_total
  } = matchupSummary

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
      {/* Header */}
      <div className="mb-6 pb-4 border-b-2 border-gray-200 dark:border-gray-700">
        <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-2">
          Matchup Breakdown
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          AI-powered analysis of {awayTeam?.abbreviation || 'Away'} @ {homeTeam?.abbreviation || 'Home'}
        </p>
      </div>

      {/* Model Reference Total Banner */}
      {model_reference_total && (
        <div className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase mb-1">
                Model Reference Total
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Based on the analysis below
              </p>
            </div>
            <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {model_reference_total}
            </div>
          </div>
        </div>
      )}

      {/* Narrative Sections */}
      <div className="space-y-0">
        {/* Section 1: Pace & Game Flow */}
        {pace_and_flow && (
          <Section
            icon="⚡"
            title={pace_and_flow.title || "Pace & Game Flow"}
            text={pace_and_flow.content || pace_and_flow.text || "Writeup unavailable for this section (missing data)."}
          />
        )}

        {/* Section 2: Offensive Style Matchup */}
        {offensive_style && (
          <Section
            icon="🏀"
            title={offensive_style.title || "Offensive Style Matchup"}
            text={offensive_style.content || offensive_style.text || "Writeup unavailable for this section (missing data)."}
          />
        )}

        {/* Section 3: Shooting & 3PT Profile */}
        {shooting_profile && (
          <Section
            icon="🎯"
            title={shooting_profile.title || "Shooting & 3PT Profile"}
            text={shooting_profile.content || shooting_profile.text || "Writeup unavailable for this section (missing data)."}
          />
        )}

        {/* Section 4: Rim Pressure & Paint Matchup */}
        {rim_and_paint && (
          <Section
            icon="💪"
            title={rim_and_paint.title || "Rim Pressure & Paint Matchup"}
            text={rim_and_paint.content || rim_and_paint.text || "Writeup unavailable for this section (missing data)."}
          />
        )}

        {/* Section 5: Recent Form Check */}
        {recent_form && (
          <Section
            icon="📊"
            title={recent_form.title || "Recent Form Check"}
            text={recent_form.content || recent_form.text || "Writeup unavailable for this section (missing data)."}
          />
        )}

        {/* Section 6: Volatility Profile */}
        {volatility_profile && (
          <Section
            icon="🌊"
            title={volatility_profile.title || "Volatility Profile"}
            text={volatility_profile.content || volatility_profile.text || "Writeup unavailable for this section (missing data)."}
          />
        )}

        {/* Section 7: Matchup DNA Summary */}
        {matchup_dna_summary && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-lg p-4 mt-2">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">
                  {matchup_dna_summary.title || "Matchup DNA Summary"}
                </h4>
                <p className="text-sm text-blue-800 dark:text-blue-200 leading-relaxed whitespace-pre-wrap">
                  {matchup_dna_summary.content || matchup_dna_summary.text || "Writeup unavailable for this section (missing data)."}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Note */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          Analysis generated by AI • For matchup context only, not picks or betting advice
        </p>
      </div>
    </div>
  )
}

export default MatchupDNA
