/**
 * Normalizes matchup summary data from API to consistent frontend format
 *
 * Handles both old (.text) and new (.content) field names for backwards compatibility
 */

/**
 * Normalize a single section (e.g., pace_and_flow, offensive_style, etc.)
 * @param {Object} section - Section object from API
 * @returns {Object} Normalized section with { title, content }
 */
function normalizeSection(section) {
  if (!section) {
    return {
      title: "Section Unavailable",
      content: "Writeup unavailable for this section (missing data)."
    }
  }

  return {
    title: section.title || "Untitled Section",
    content: section.content || section.text || "Writeup unavailable for this section (missing data)."
  }
}

/**
 * Normalize entire matchup summary response
 * @param {Object} matchupSummary - Raw matchup_summary from API
 * @returns {Object} Normalized summary with consistent structure
 */
export function normalizeMatchupSummary(matchupSummary) {
  if (!matchupSummary) {
    console.warn('[matchupSummaryNormalizer] Received null/undefined matchup summary')
    return null
  }

  // Log raw data for debugging (only in development)
  if (process.env.NODE_ENV === 'development') {
    console.log('[matchupSummaryNormalizer] Raw API response:', {
      keys: Object.keys(matchupSummary),
      hasContent: Boolean(matchupSummary.matchup_dna_summary?.content),
      hasText: Boolean(matchupSummary.matchup_dna_summary?.text)
    })
  }

  return {
    // Normalized sections (all use .content)
    sections: {
      pace_and_flow: normalizeSection(matchupSummary.pace_and_flow),
      offensive_style: normalizeSection(matchupSummary.offensive_style),
      shooting_profile: normalizeSection(matchupSummary.shooting_profile),
      rim_and_paint: normalizeSection(matchupSummary.rim_and_paint),
      recent_form: normalizeSection(matchupSummary.recent_form),
      volatility_profile: normalizeSection(matchupSummary.volatility_profile),
      matchup_dna_summary: normalizeSection(matchupSummary.matchup_dna_summary)
    },

    // Metadata
    model_reference_total: matchupSummary.model_reference_total || null,
    home_team: matchupSummary.home_team || null,
    away_team: matchupSummary.away_team || null,
    game_id: matchupSummary.game_id || null,
    engine_version: matchupSummary.engine_version || null,
    payload_version: matchupSummary.payload_version || null,

    // Full summary text (for dedicated summary page)
    full_matchup_summary: matchupSummary.matchup_dna_summary?.content ||
                          matchupSummary.matchup_dna_summary?.text ||
                          "Full matchup summary unavailable."
  }
}

/**
 * Get a specific section by key
 * @param {Object} normalizedSummary - Normalized summary from normalizeMatchupSummary()
 * @param {string} sectionKey - Key like 'pace_and_flow'
 * @returns {Object} Section with { title, content }
 */
export function getSection(normalizedSummary, sectionKey) {
  if (!normalizedSummary?.sections?.[sectionKey]) {
    return {
      title: "Section Unavailable",
      content: "Writeup unavailable for this section (missing data)."
    }
  }

  return normalizedSummary.sections[sectionKey]
}

/**
 * Check if summary has valid content
 * @param {Object} matchupSummary - Raw or normalized summary
 * @returns {boolean} True if summary has at least one section with content
 */
export function hasValidContent(matchupSummary) {
  if (!matchupSummary) return false

  // Check if normalized format
  if (matchupSummary.sections) {
    return Object.values(matchupSummary.sections).some(
      section => section?.content && section.content !== "Writeup unavailable for this section (missing data)."
    )
  }

  // Check raw format
  const sections = [
    'pace_and_flow', 'offensive_style', 'shooting_profile',
    'rim_and_paint', 'recent_form', 'volatility_profile', 'matchup_dna_summary'
  ]

  return sections.some(key => {
    const section = matchupSummary[key]
    return section?.content || section?.text
  })
}
