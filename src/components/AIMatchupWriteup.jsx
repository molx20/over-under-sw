/**
 * AIMatchupWriteup Component
 *
 * Displays AI-generated 3-section game analysis in GamePage blue header.
 * Replaces the existing Matchup Summary with betting-focused insights.
 *
 * Sections:
 * 1. Empty Possessions Analysis (🎯) - Efficiency, turnovers, extra possessions
 * 2. Archetype Matchups (🏀) - Offensive/defensive style clashes across 5 categories
 * 3. Last 5 Games Trends (📊) - Recent form, pace, efficiency, rest impact
 *
 * Props:
 * - writeup: string - Plain text with 3 sections separated by double line breaks
 * - homeTeam: object - { abbreviation, full_name }
 * - awayTeam: object - { abbreviation, full_name }
 */

function AIMatchupWriteup({ writeup, homeTeam, awayTeam }) {
  if (!writeup) return null

  // Split writeup into 3 sections (double line breaks)
  const sections = writeup.split('\n\n').filter(s => s.trim())

  // Section metadata
  const sectionConfig = [
    { title: 'Empty Possessions Analysis', icon: '🎯' },
    { title: 'Archetype Matchups', icon: '🏀' },
    { title: 'Last 5 Games Trends', icon: '📊' }
  ]

  // Helper function to render text with bold numbers
  const renderTextWithBold = (text) => {
    // Split text by **bold** markdown syntax
    const parts = text.split(/(\*\*.*?\*\*)/)

    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        // Remove ** markers and render as bold
        const boldText = part.slice(2, -2)
        return <strong key={i} className="font-bold text-white">{boldText}</strong>
      }
      return <span key={i}>{part}</span>
    })
  }

  return (
    <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-lg overflow-hidden">
      {/* Header */}
      <div className="py-3 px-4 sm:px-6 border-b border-white/20">
        <h3 className="text-sm font-semibold text-white/90">
          Game Analysis
        </h3>
      </div>

      {/* Sections */}
      <div className="p-4 sm:p-6 space-y-6">
        {sections.map((text, idx) => {
          const config = sectionConfig[idx]
          if (!config) return null // Safety: Only render if we have config for this section

          const isLastSection = idx === sections.length - 1

          return (
            <div
              key={idx}
              className={!isLastSection ? 'pb-6 border-b border-white/10' : ''}
            >
              {/* Section Header with Icon */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-2xl" role="img" aria-label={config.title}>
                  {config.icon}
                </span>
                <h4 className="text-sm font-semibold text-white/80">
                  {config.title}
                </h4>
              </div>

              {/* Section Text */}
              <p className="text-base leading-relaxed text-white/85">
                {renderTextWithBold(text)}
              </p>
            </div>
          )
        })}
      </div>

      {/* Attribution Footer */}
      <div className="px-4 sm:px-6 py-2 bg-white/5 border-t border-white/10">
        <p className="text-xs text-white/50 text-center">
          AI-generated analysis • Data-driven insights
        </p>
      </div>
    </div>
  )
}

export default AIMatchupWriteup
