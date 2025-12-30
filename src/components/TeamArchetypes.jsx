/**
 * TeamArchetypes Component
 *
 * Displays offensive and defensive archetypes with season/last-10 comparison
 * Replaces the old IdentityTags system
 */

import GlassTooltip from './GlassTooltip'

const ARCHETYPE_COLORS = {
  // Offensive archetypes
  'foul_pressure_paint_attack': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700',
  'perimeter_spacing_offense': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border-green-300 dark:border-green-700',
  'balanced_high_assist': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700',
  'second_chance_rebounders': 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700',
  'iso_low_assist': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700',

  // Defensive archetypes
  'foul_baiting_suppressor': 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-300 dark:border-indigo-700',
  'perimeter_lockdown': 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 border-teal-300 dark:border-teal-700',
  'paint_protection_elite': 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 border-cyan-300 dark:border-cyan-700',
  'turnover_forcing_pressure': 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300 border-pink-300 dark:border-pink-700',
  'balanced_disciplined': 'bg-gray-100 dark:bg-gray-700/30 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600',
}

function TeamArchetypes({ archetypes, teamName, showComparison = true, compact = false }) {
  if (!archetypes) {
    return null
  }

  const {
    season_offensive,
    season_defensive,
    last10_offensive,
    last10_defensive,
    style_shifts
  } = archetypes

  return (
    <div className={`space-y-${compact ? '3' : '4'}`}>
      {/* Offensive Archetype */}
      <div>
        <div className={`text-xs font-medium text-gray-500 dark:text-gray-400 mb-${compact ? '1' : '2'} uppercase tracking-wide`}>
          Offensive Style
        </div>
        <ArchetypeBadge
          archetype={season_offensive}
          label="Season"
          compact={compact}
        />
        {showComparison && last10_offensive && (
          <>
            <ArchetypeBadge
              archetype={last10_offensive}
              label="Last 10"
              className="mt-2"
              compact={compact}
            />
            {style_shifts?.offensive && (
              <div className={`mt-2 flex items-center gap-2 px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg ${compact ? 'text-xs' : 'text-sm'}`}>
                <svg className="w-4 h-4 text-orange-600 dark:text-orange-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="text-orange-700 dark:text-orange-300 font-medium">
                  {style_shifts.offensive_details}
                </span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Defensive Archetype */}
      <div>
        <div className={`text-xs font-medium text-gray-500 dark:text-gray-400 mb-${compact ? '1' : '2'} uppercase tracking-wide`}>
          Defensive Style
        </div>
        <ArchetypeBadge
          archetype={season_defensive}
          label="Season"
          compact={compact}
        />
        {showComparison && last10_defensive && (
          <>
            <ArchetypeBadge
              archetype={last10_defensive}
              label="Last 10"
              className="mt-2"
              compact={compact}
            />
            {style_shifts?.defensive && (
              <div className={`mt-2 flex items-center gap-2 px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg ${compact ? 'text-xs' : 'text-sm'}`}>
                <svg className="w-4 h-4 text-orange-600 dark:text-orange-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="text-orange-700 dark:text-orange-300 font-medium">
                  {style_shifts.defensive_details}
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function ArchetypeBadge({ archetype, label, className = '', compact = false }) {
  if (!archetype) {
    return null
  }

  const colorClass = ARCHETYPE_COLORS[archetype.id] || 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600'

  return (
    <div className={className}>
      <div className="flex items-start gap-2 mb-1">
        <span className={`text-xs font-medium text-gray-500 dark:text-gray-400 ${compact ? 'pt-1' : 'pt-1.5'}`}>
          {label}:
        </span>
        <div className="flex-1">
          <GlassTooltip content={archetype.description}>
            <div className={`inline-flex items-center px-3 py-1 rounded-full border ${colorClass} ${compact ? 'text-xs' : 'text-sm'} font-medium cursor-help`}>
              {archetype.name}
            </div>
          </GlassTooltip>
          <p className={`${compact ? 'text-xs' : 'text-sm'} text-gray-600 dark:text-gray-400 mt-1`}>
            {archetype.description}
          </p>
          {archetype.scoring_profile && (
            <p className={`${compact ? 'text-xs' : 'text-sm'} text-gray-500 dark:text-gray-500 mt-0.5 italic`}>
              {archetype.scoring_profile}
            </p>
          )}
          {archetype.allows && archetype.suppresses && (
            <div className={`${compact ? 'text-xs' : 'text-sm'} text-gray-500 dark:text-gray-500 mt-1 space-y-0.5`}>
              <div className="flex items-start gap-1">
                <span className="text-green-600 dark:text-green-400">✓</span>
                <span>Allows: {archetype.allows}</span>
              </div>
              <div className="flex items-start gap-1">
                <span className="text-red-600 dark:text-red-400">✗</span>
                <span>Suppresses: {archetype.suppresses}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TeamArchetypes
