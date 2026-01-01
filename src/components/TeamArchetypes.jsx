/**
 * TeamArchetypes Component
 *
 * Displays offensive and defensive archetypes with season/last-10 comparison
 * Replaces the old IdentityTags system
 */

import { useMemo, useState } from 'react'
import GlassTooltip from './GlassTooltip'
import SimilarTeamsChips from './SimilarTeamsChips'
import ArchetypeDrilldownModal from './ArchetypeDrilldownModal'
import GamesVsArchetypeModal from './GamesVsArchetypeModal'
import { buildArchetypeTeamsIndex, getSimilarTeams } from '../utils/archetypeHelpers'
import { useArchetypeGames, useTeamVsArchetypeGames } from '../utils/api'

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

function TeamArchetypes({
  archetypes,
  teamName,
  teamId,
  opponentTeamId,     // NEW: Opponent's team ID
  opponentTeamAbbr,   // NEW: Opponent's team abbreviation
  allTeamsArchetypes,
  showComparison = true,
  compact = false
}) {
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

  // Build archetype index
  const archetypeIndex = useMemo(() => {
    if (!allTeamsArchetypes) return null
    return buildArchetypeTeamsIndex(allTeamsArchetypes)
  }, [allTeamsArchetypes])

  // Get similar teams helper
  const getSimilar = (type, archetypeId) => {
    if (!archetypeIndex) return []
    return getSimilarTeams(type, archetypeId, teamName, archetypeIndex)
  }

  // Drilldown modal state (own games with archetype)
  const [drilldownModal, setDrilldownModal] = useState(null)

  const openDrilldown = (archetype, type, window) => {
    setDrilldownModal({ archetype, type, window })
  }

  const closeDrilldown = () => {
    setDrilldownModal(null)
  }

  // Fetch games for drilldown modal (only when modal is open)
  const { data: archetypeGamesData, isLoading: gamesLoading } = useArchetypeGames(
    teamId,
    drilldownModal?.type,
    drilldownModal?.archetype?.id,
    drilldownModal?.window,
    '2025-26',
    !!drilldownModal  // Only fetch when modal is open
  )

  // VS Archetype modal state (opponent's games vs this archetype)
  const [vsArchetypeModal, setVsArchetypeModal] = useState(null)

  const openVsArchetype = (archetype, type, window) => {
    setVsArchetypeModal({ archetype, type, window })
  }

  const closeVsArchetype = () => {
    setVsArchetypeModal(null)
  }

  // Fetch opponent's games vs this archetype (only when modal is open)
  const { data: vsArchetypeData, isLoading: vsGamesLoading } = useTeamVsArchetypeGames(
    opponentTeamId,
    vsArchetypeModal?.type,
    vsArchetypeModal?.archetype?.id,
    vsArchetypeModal?.window,
    '2025-26',
    !!vsArchetypeModal && !!opponentTeamId  // Only fetch when modal is open and opponent exists
  )

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
          similarTeams={getSimilar('offensive', season_offensive?.id)}
          onClick={() => openDrilldown(season_offensive, 'offensive', 'season')}
          onVsClick={opponentTeamId ? () => openVsArchetype(season_offensive, 'offensive', 'season') : null}
          hasOpponent={!!opponentTeamId}
        />
        {showComparison && last10_offensive && style_shifts?.offensive && (
          <>
            <ArchetypeBadge
              archetype={last10_offensive}
              label="Last 10"
              className="mt-2"
              compact={compact}
              similarTeams={getSimilar('offensive', last10_offensive?.id)}
              onClick={() => openDrilldown(last10_offensive, 'offensive', 'last10')}
              onVsClick={opponentTeamId ? () => openVsArchetype(last10_offensive, 'offensive', 'last10') : null}
              hasOpponent={!!opponentTeamId}
            />
            <div className={`mt-2 flex items-center gap-2 px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg ${compact ? 'text-xs' : 'text-sm'}`}>
              <svg className="w-4 h-4 text-orange-600 dark:text-orange-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span className="text-orange-700 dark:text-orange-300 font-medium">
                {style_shifts.offensive_details}
              </span>
            </div>
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
          similarTeams={getSimilar('defensive', season_defensive?.id)}
          onClick={() => openDrilldown(season_defensive, 'defensive', 'season')}
          onVsClick={opponentTeamId ? () => openVsArchetype(season_defensive, 'defensive', 'season') : null}
          hasOpponent={!!opponentTeamId}
        />
        {showComparison && last10_defensive && style_shifts?.defensive && (
          <>
            <ArchetypeBadge
              archetype={last10_defensive}
              label="Last 10"
              className="mt-2"
              compact={compact}
              similarTeams={getSimilar('defensive', last10_defensive?.id)}
              onClick={() => openDrilldown(last10_defensive, 'defensive', 'last10')}
              onVsClick={opponentTeamId ? () => openVsArchetype(last10_defensive, 'defensive', 'last10') : null}
              hasOpponent={!!opponentTeamId}
            />
            <div className={`mt-2 flex items-center gap-2 px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg ${compact ? 'text-xs' : 'text-sm'}`}>
              <svg className="w-4 h-4 text-orange-600 dark:text-orange-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span className="text-orange-700 dark:text-orange-300 font-medium">
                {style_shifts.defensive_details}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Archetype Drilldown Modal */}
      {drilldownModal && (
        <ArchetypeDrilldownModal
          isOpen={!!drilldownModal}
          onClose={closeDrilldown}
          archetype={drilldownModal.archetype}
          archetypeType={drilldownModal.type}
          window={drilldownModal.window}
          teamAbbr={teamName}
          games={archetypeGamesData?.games || []}
          stats={archetypeGamesData?.stats || {}}
          isLoading={gamesLoading}
        />
      )}

      {/* Games vs Archetype Modal */}
      {vsArchetypeModal && opponentTeamId && (
        <GamesVsArchetypeModal
          isOpen={!!vsArchetypeModal}
          onClose={closeVsArchetype}
          archetype={vsArchetypeModal.archetype}
          archetypeType={vsArchetypeModal.type}
          window={vsArchetypeModal.window}
          targetTeamAbbr={opponentTeamAbbr}
          selectedTeamAbbr={teamName}
          games={vsArchetypeData?.games || []}
          summary={vsArchetypeData?.summary || {}}
          isLoading={vsGamesLoading}
        />
      )}
    </div>
  )
}

function ArchetypeBadge({ archetype, label, className = '', compact = false, similarTeams = [], onClick, onVsClick, hasOpponent = false }) {
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
          <div className="flex items-center gap-2">
            <GlassTooltip content={archetype.description}>
              <button
                onClick={onClick}
                className={`inline-flex items-center px-3 py-1 rounded-full border ${colorClass} ${compact ? 'text-xs' : 'text-sm'} font-medium cursor-pointer hover:opacity-80 transition-opacity`}
              >
                {archetype.name}
              </button>
            </GlassTooltip>
            {hasOpponent && onVsClick && (
              <GlassTooltip content="See opponent's games vs this archetype">
                <button
                  onClick={onVsClick}
                  className="p-1.5 rounded-lg bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
                  title="View opponent's games vs this archetype"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                </button>
              </GlassTooltip>
            )}
          </div>
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

          {/* Similar teams chips */}
          <SimilarTeamsChips teams={similarTeams} compact={compact} />
        </div>
      </div>
    </div>
  )
}

export default TeamArchetypes
