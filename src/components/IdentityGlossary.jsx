/**
 * IdentityGlossary Component
 *
 * Modal/popover that explains all identity tags with detailed descriptions.
 * Helps users understand what each tag means and how they're calculated.
 */

import { useState } from 'react'

const IDENTITY_GLOSSARY = [
  {
    tag: 'Home Giant Killers',
    color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300',
    icon: '⬆️',
    shortDescription: 'Scores significantly more at home vs elite defenses than season average',
    fullDescription: 'This team scores 4+ points per game MORE at home against elite defenses (ranked 1-10) compared to their season average. They rise to the challenge of tough opponents when playing at home.',
    criteria: '• Home PPG vs Elite > Season Avg + 4 pts\n• Minimum 3 games vs elite defenses at home',
  },
  {
    tag: 'Home Flat-Track Bullies',
    color: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border-yellow-300',
    icon: '🔥',
    shortDescription: 'Scores much better at home vs weak defenses than vs elite defenses',
    fullDescription: 'This team scores 3+ points per game MORE at home against bad defenses (ranked 21-30) than against elite defenses. They capitalize on favorable matchups at home but struggle more against top opponents.',
    criteria: '• Home PPG vs Bad > Home PPG vs Elite + 3 pts\n• Minimum 3 games in each category at home',
  },
  {
    tag: 'Road Warriors vs Good Defense',
    color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300',
    icon: '⭐',
    shortDescription: 'Performs exceptionally well on the road vs elite defenses',
    fullDescription: 'This team scores 4+ points per game MORE on the road against elite defenses compared to their season average. They thrive in hostile environments even against the toughest defensive opponents.',
    criteria: '• Away PPG vs Elite > Season Avg + 4 pts\n• Minimum 3 games vs elite defenses on road',
  },
  {
    tag: 'Road Shrinkers vs Good Defense',
    color: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300',
    icon: '⬇️',
    shortDescription: 'Struggles significantly on the road vs elite defenses',
    fullDescription: 'This team scores 4+ points per game LESS on the road against elite defenses compared to their season average. The combination of a hostile crowd and top-tier defense suppresses their offense.',
    criteria: '• Away PPG vs Elite < Season Avg - 4 pts\n• Minimum 3 games vs elite defenses on road',
  },
  {
    tag: 'Home Scoring Suppressed vs Bad Defense',
    color: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300',
    icon: '⚠️',
    shortDescription: 'Counterintuitively scores less at home vs bad defenses',
    fullDescription: 'This team scores 4+ points per game LESS at home against bad defenses compared to their season average. This counterintuitive pattern may indicate motivational issues, stylistic mismatches, or complacency against weaker opponents.',
    criteria: '• Home PPG vs Bad < Season Avg - 4 pts\n• Minimum 3 games vs bad defenses at home',
  },
  {
    tag: 'Consistent Scorer',
    color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-300',
    icon: '📊',
    shortDescription: 'Shows little variation in scoring across different contexts',
    fullDescription: 'This team maintains steady scoring output regardless of opponent defense quality or location. All scoring splits stay within 3 points of each other, indicating reliable and predictable offensive production.',
    criteria: '• All splits within 3 pts range\n• Minimum 4 valid split categories\n• Only applies if no other specific tags match',
  },
  {
    tag: 'High-Variance Scoring Identity',
    color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300',
    icon: '📈',
    shortDescription: 'Large swings in scoring output based on context',
    fullDescription: 'This team shows an 8+ point spread between their highest and lowest scoring contexts. Their performance is highly dependent on opponent defense quality and location, making them less predictable.',
    criteria: '• Spread between highest and lowest split ≥ 8 pts\n• Minimum 4 valid split categories',
  },
]

const DEFENSE_TIERS = [
  {
    tier: 'Elite Defense',
    ranks: 'Ranks 1-10',
    description: 'Top 10 defenses in the league by defensive rating (fewest points allowed per 100 possessions)',
    color: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-200',
  },
  {
    tier: 'Average Defense',
    ranks: 'Ranks 11-20',
    description: 'Middle-tier defenses, representing league-average defensive ability',
    color: 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 border-yellow-200',
  },
  {
    tier: 'Bad Defense',
    ranks: 'Ranks 21-30',
    description: 'Bottom 10 defenses in the league, allowing the most points per 100 possessions',
    color: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border-green-200',
  },
]

function IdentityGlossary({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('identities') // 'identities' or 'tiers'

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 z-10">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Identity Tags Glossary
                </h2>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Tabs */}
              <div className="flex gap-4 mt-4">
                <button
                  onClick={() => setActiveTab('identities')}
                  className={`pb-2 px-1 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'identities'
                      ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  Identity Tags (7)
                </button>
                <button
                  onClick={() => setActiveTab('tiers')}
                  className={`pb-2 px-1 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'tiers'
                      ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  Defense Tiers
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-140px)]">
              {activeTab === 'identities' ? (
                <div className="space-y-6">
                  {/* Introduction */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      Identity tags are automatically generated based on how teams score against different defense tiers at home and on the road.
                      Tags require <strong>minimum 3 games</strong> per category and use <strong>4-point thresholds</strong> for significance.
                    </p>
                  </div>

                  {/* Identity Tags */}
                  {IDENTITY_GLOSSARY.map((identity, index) => (
                    <div
                      key={index}
                      className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-5 border border-gray-200 dark:border-gray-600"
                    >
                      {/* Tag Badge */}
                      <div className={`inline-flex items-center px-3 py-1.5 rounded-full border ${identity.color} text-sm font-medium mb-3`}>
                        <span className="mr-2">{identity.icon}</span>
                        {identity.tag}
                      </div>

                      {/* Short Description */}
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 italic">
                        {identity.shortDescription}
                      </p>

                      {/* Full Description */}
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                        {identity.fullDescription}
                      </p>

                      {/* Criteria */}
                      <div className="bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600 p-3">
                        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">
                          Criteria
                        </h4>
                        <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                          {identity.criteria}
                        </pre>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Introduction */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      Defense tiers categorize NBA teams based on their <strong>defensive rating rank</strong> (1-30, where 1 is the best defense).
                      This helps identify how teams perform against varying levels of defensive opposition.
                    </p>
                  </div>

                  {/* Defense Tiers */}
                  {DEFENSE_TIERS.map((tier, index) => (
                    <div
                      key={index}
                      className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-5 border border-gray-200 dark:border-gray-600"
                    >
                      {/* Tier Badge */}
                      <div className={`inline-flex items-center px-4 py-2 rounded-lg border ${tier.color} font-semibold mb-3`}>
                        {tier.tier}
                        <span className="ml-2 text-sm opacity-75">({tier.ranks})</span>
                      </div>

                      {/* Description */}
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {tier.description}
                      </p>
                    </div>
                  ))}

                  {/* Additional Info */}
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-5 border border-gray-200 dark:border-gray-600">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-3">
                      How Rankings Are Calculated
                    </h4>
                    <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                      <li className="flex items-start">
                        <span className="mr-2">•</span>
                        <span><strong>Defensive Rating</strong>: Points allowed per 100 possessions (lower is better)</span>
                      </li>
                      <li className="flex items-start">
                        <span className="mr-2">•</span>
                        <span><strong>Updated Daily</strong>: Rankings refresh with each day's sync from NBA stats</span>
                      </li>
                      <li className="flex items-start">
                        <span className="mr-2">•</span>
                        <span><strong>Season-Long</strong>: Based on entire season performance, not just recent games</span>
                      </li>
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
              <div className="flex justify-between items-center">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Thresholds: 4 pts (significant), 3 pts (moderate) • Min 3 games per category
                </p>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default IdentityGlossary
