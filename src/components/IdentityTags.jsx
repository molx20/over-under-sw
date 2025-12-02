/**
 * IdentityTags Component
 *
 * Displays identity tags for a team based on their scoring splits
 * against different defense tiers and locations.
 */

import GlassTooltip from './GlassTooltip'
import './GlassTooltip.css'

const TAG_COLORS = {
  'Home Giant Killers': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700',
  'Home Flat-Track Bullies': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700',
  'Road Warriors vs Good Defense': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700',
  'Road Shrinkers vs Good Defense': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700',
  'Home Scoring Suppressed vs Bad Defense': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700',
  'Consistent Scorer': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700',
  'High-Variance Scoring Identity': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700',
}

const TAG_EXPLANATIONS = {
  'Home Giant Killers': 'Scores significantly more at home vs elite defenses than season average',
  'Home Flat-Track Bullies': 'Scores much better at home vs weak defenses than vs elite defenses',
  'Road Warriors vs Good Defense': 'Performs exceptionally well on the road vs elite defenses',
  'Road Shrinkers vs Good Defense': 'Struggles significantly on the road vs elite defenses',
  'Home Scoring Suppressed vs Bad Defense': 'Counterintuitively scores less at home vs bad defenses',
  'Consistent Scorer': 'Shows little variation in scoring across different contexts',
  'High-Variance Scoring Identity': 'Large swings in scoring output depending on opponent and location',
}

function IdentityTags({ tags, teamAbbr, showTooltip = true, compact = false }) {
  if (!tags || tags.length === 0) {
    return null
  }

  return (
    <div className={`flex flex-wrap gap-2 ${compact ? 'text-xs' : 'text-sm'}`}>
      {tags.map((tag, index) => {
        const colorClass = TAG_COLORS[tag] || 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600'
        const explanation = TAG_EXPLANATIONS[tag]

        const tagContent = (
          <div
            className={`
              inline-flex items-center px-3 py-1 rounded-full border
              ${colorClass}
              ${compact ? 'text-xs' : 'text-sm'}
              font-medium
              transition-all duration-200
              ${showTooltip ? 'cursor-help' : ''}
            `}
          >
            {/* Icon based on tag type */}
            {tag.includes('Giant Killers') && (
              <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
              </svg>
            )}
            {tag.includes('Road Warriors') && (
              <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            )}
            {tag.includes('Shrinkers') && (
              <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clipRule="evenodd" />
              </svg>
            )}
            {tag.includes('Bullies') && (
              <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
              </svg>
            )}
            {tag.includes('Consistent') && (
              <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            )}
            {tag.includes('High-Variance') && (
              <svg className="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
              </svg>
            )}

            <span className="truncate">{tag}</span>
          </div>
        )

        return showTooltip && explanation ? (
          <GlassTooltip key={index} content={explanation}>
            {tagContent}
          </GlassTooltip>
        ) : (
          <div key={index}>{tagContent}</div>
        )
      })}
    </div>
  )
}

export default IdentityTags
