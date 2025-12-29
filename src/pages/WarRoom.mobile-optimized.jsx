import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGameDetail } from '../utils/api'

/**
 * Mobile-First War Room
 *
 * Design Principles:
 * - Progressive disclosure (collapse sections)
 * - One column layout
 * - Clear visual hierarchy
 * - 44px+ tap targets
 * - Minimal cognitive load
 */

function WarRoom() {
  const { gameId } = useParams()
  const navigate = useNavigate()

  // Section collapse state
  const [expandedSections, setExpandedSections] = useState({
    prediction: true,    // Always expanded by default
    stats: false,
    form: false,
    similar: false,
    advanced: false,
  })

  const { data: gameData, isLoading, isError, error } = useGameDetail(gameId, null)

  // Toggle section expansion
  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  // Loading state - Simple and fast
  if (isLoading && !gameData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center space-y-4 p-6">
          <div className="w-16 h-16 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            Loading analysis...
          </p>
        </div>
      </div>
    )
  }

  // Error state
  if (isError || !gameData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="mobile-container py-8">
          <button
            onClick={() => navigate('/')}
            className="mb-4 flex items-center space-x-2 text-primary-600 dark:text-primary-400 active:text-primary-700"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="font-medium">Back</span>
          </button>

          <div className="bg-red-50 dark:bg-red-900/20 rounded-2xl p-6 border-2 border-red-200 dark:border-red-800">
            <div className="text-center space-y-4">
              <div className="text-5xl">⚠️</div>
              <h3 className="text-lg font-bold text-red-900 dark:text-red-100">
                Failed to load
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300">
                {error?.message || 'Game not found'}
              </p>
              <button
                onClick={() => navigate('/')}
                className="btn-mobile bg-red-600 text-white hover:bg-red-700"
              >
                Back to Games
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const { prediction, home_team, away_team, matchup_summary } = gameData

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Minimal Sticky Header */}
      <div className="sticky top-0 z-50 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="mobile-container py-3">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="flex items-center space-x-2 text-primary-600 dark:text-primary-400 active:text-primary-700 min-h-[44px]"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="font-semibold text-base">Back</span>
            </button>
            <div className="text-right">
              <div className="text-sm font-bold text-gray-900 dark:text-white">
                {away_team.abbreviation} @ {home_team.abbreviation}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mobile-container py-6">
        {/* Hero Section - Matchup Card */}
        <div className="bg-gradient-to-br from-primary-600 to-primary-700 rounded-2xl shadow-lg p-6 mb-6 text-white">
          {/* Badge */}
          <div className="flex justify-center mb-4">
            <span className="inline-block px-4 py-1.5 bg-white/20 backdrop-blur-sm rounded-full text-xs font-bold uppercase tracking-wide">
              War Room
            </span>
          </div>

          {/* Teams */}
          <div className="text-center mb-6">
            <div className="flex items-center justify-center space-x-4 mb-2">
              <span className="text-3xl font-black tracking-tight">
                {away_team.abbreviation}
              </span>
              <span className="text-white/60 text-xl font-bold">vs</span>
              <span className="text-3xl font-black tracking-tight">
                {home_team.abbreviation}
              </span>
            </div>
            <p className="text-white/80 text-sm">
              {away_team.name} @ {home_team.name}
            </p>
          </div>

          {/* Prediction Pill */}
          {prediction && (
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
              <div className="text-center">
                <div className="text-white/70 text-xs font-semibold uppercase tracking-wide mb-1">
                  Projected Total
                </div>
                <div className="text-4xl font-black mb-1">
                  {prediction.projected_total?.toFixed(1)}
                </div>
                <div className="text-white/80 text-sm">
                  Line: {prediction.over_under_line} ({prediction.recommendation})
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Collapsible Sections */}
        <div className="space-y-4">
          {/* Section: Key Stats */}
          <CollapsibleSection
            icon="📊"
            title="Key Stats"
            subtitle="Team metrics & trends"
            isExpanded={expandedSections.stats}
            onToggle={() => toggleSection('stats')}
          >
            <div className="space-y-4 pt-4">
              <StatRow label="Pace" homeValue="98.5" awayValue="102.3" />
              <StatRow label="Off Rating" homeValue="115.2" awayValue="112.8" />
              <StatRow label="Def Rating" homeValue="108.4" awayValue="110.1" />
              <div className="text-xs text-gray-500 dark:text-gray-400 text-center mt-4">
                Season averages
              </div>
            </div>
          </CollapsibleSection>

          {/* Section: Recent Form */}
          <CollapsibleSection
            icon="🔥"
            title="Recent Form"
            subtitle="Last 5 games"
            isExpanded={expandedSections.form}
            onToggle={() => toggleSection('form')}
          >
            <div className="pt-4 text-center text-sm text-gray-600 dark:text-gray-400">
              Form analysis goes here
            </div>
          </CollapsibleSection>

          {/* Section: Similar Opponents */}
          <CollapsibleSection
            icon="🎯"
            title="Similar Matchups"
            subtitle="How they perform vs similar teams"
            isExpanded={expandedSections.similar}
            onToggle={() => toggleSection('similar')}
          >
            <div className="pt-4 text-center text-sm text-gray-600 dark:text-gray-400">
              Similar opponent analysis
            </div>
          </CollapsibleSection>

          {/* Section: Advanced Metrics */}
          <CollapsibleSection
            icon="⚡"
            title="Advanced Metrics"
            subtitle="Deep dive analytics"
            isExpanded={expandedSections.advanced}
            onToggle={() => toggleSection('advanced')}
          >
            <div className="pt-4 text-center text-sm text-gray-600 dark:text-gray-400">
              Advanced stats & splits
            </div>
          </CollapsibleSection>
        </div>

        {/* Summary (if available) */}
        {matchup_summary && (
          <div className="mt-6 p-5 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-3 flex items-center">
              <span className="mr-2">💡</span>
              Analysis Summary
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {matchup_summary}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Collapsible Section Component
 * Tap target: 56px height minimum
 */
function CollapsibleSection({ icon, title, subtitle, isExpanded, onToggle, children }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full min-h-[56px] px-5 py-4 flex items-center justify-between active:bg-gray-50 dark:active:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center space-x-3 text-left flex-1">
          <span className="text-2xl" role="img" aria-label={title}>
            {icon}
          </span>
          <div>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">
              {title}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {subtitle}
            </p>
          </div>
        </div>
        <svg
          className={`w-6 h-6 text-gray-400 transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2.5}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-5 pb-5 border-t border-gray-100 dark:border-gray-700">
          {children}
        </div>
      )}
    </div>
  )
}

/**
 * Stat Row Component
 * Shows comparison between two values
 */
function StatRow({ label, homeValue, awayValue }) {
  return (
    <div className="flex items-center justify-between">
      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 flex-1">
        {label}
      </div>
      <div className="flex items-center space-x-4">
        <div className="text-sm font-bold text-primary-600 dark:text-primary-400 w-14 text-right">
          {awayValue}
        </div>
        <div className="w-px h-4 bg-gray-300 dark:bg-gray-600"></div>
        <div className="text-sm font-bold text-gray-900 dark:text-white w-14">
          {homeValue}
        </div>
      </div>
    </div>
  )
}

export default WarRoom
