import axios from 'axios'
import { useQuery } from '@tanstack/react-query'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

// Configure axios defaults
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for logging and performance timing
api.interceptors.request.use(
  (config) => {
    // Add start time for performance measurement
    config.metadata = { startTime: Date.now() }
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.params || '')
    return config
  },
  (error) => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for logging and error handling with timing
api.interceptors.response.use(
  (response) => {
    // Calculate request duration
    const duration = Date.now() - response.config.metadata.startTime
    console.debug(`[PERF] ${response.config.url}: ${duration}ms`, response.status)

    // Add timing to response for client-side analysis
    response.duration = duration

    return response
  },
  (error) => {
    // Log timing even for errors
    if (error.config?.metadata?.startTime) {
      const duration = Date.now() - error.config.metadata.startTime
      console.debug(`[PERF] ${error.config.url}: ${duration}ms (error)`)
    }

    if (error.code === 'ECONNABORTED') {
      console.error('[API] Request timeout:', error.config?.url)
    } else if (error.response) {
      console.error(`[API] Error ${error.response.status}:`, error.response.data)
    } else if (error.request) {
      console.error('[API] No response received:', error.request)
    } else {
      console.error('[API] Error:', error.message)
    }
    return Promise.reject(error)
  }
)

export const fetchGames = async (date = null) => {
  try {
    const params = date ? { date } : {}
    const response = await api.get('/games', { params })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data
  } catch (error) {
    console.error('[fetchGames] Error:', error)

    // Provide user-friendly error messages
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timed out. Please try again.')
    }
    if (error.response?.status === 404) {
      throw new Error('API endpoint not found. Please check your configuration.')
    }
    if (error.response?.status >= 500) {
      throw new Error('Server error. Please try again later.')
    }

    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch games')
  }
}

export const fetchGameDetail = async (gameId, bettingLine = null) => {
  try {
    const params = {
      game_id: gameId,
    }
    // Add betting line if provided
    if (bettingLine !== null && !isNaN(bettingLine)) {
      params.betting_line = bettingLine
    }

    // Game detail requests need longer timeout due to prediction generation
    // NBA API can be slow, especially with advanced stats
    const response = await api.get('/game_detail', {
      params,
      timeout: 120000  // 120 seconds - Railway has higher timeout limits
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data
  } catch (error) {
    console.error('[fetchGameDetail] Error:', error)

    // Provide user-friendly error messages
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timed out. The NBA Stats API is running slow. Please click "Try Again" to retry - it may work from cache on the second try.')
    }
    if (error.response?.status === 404) {
      throw new Error('Game not found or API endpoint unavailable.')
    }
    if (error.response?.status >= 500) {
      throw new Error('Server error while generating prediction. Please try again.')
    }

    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch game details')
  }
}

// Health check utility
export const checkAPIHealth = async () => {
  try {
    const response = await api.get('/health', { timeout: 5000 })
    return response.data
  } catch (error) {
    console.error('[checkAPIHealth] API health check failed:', error)
    return { success: false, error: error.message }
  }
}

// Fetch team stats with league rankings
export const fetchTeamStatsWithRanks = async (teamId, season = '2025-26') => {
  try {
    const response = await api.get('/team-stats-with-ranks', {
      params: { team_id: teamId, season },
      timeout: 10000
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data
  } catch (error) {
    console.error('[fetchTeamStatsWithRanks] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch team stats with rankings')
  }
}

// ============================================
// Auto-Learning Endpoints
// ============================================

/**
 * Trigger the full auto-learning cycle
 */
export const runAutoLearning = async () => {
  try {
    const response = await api.post('/auto-learning/run', {}, {
      timeout: 180000  // 3 minutes - can take a while
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Auto-learning failed')
    }

    return response.data
  } catch (error) {
    console.error('[runAutoLearning] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to run auto-learning')
  }
}

/**
 * Get prediction history
 */
export const getPredictionHistory = async (limit = 50, withLearning = false) => {
  try {
    const response = await api.get('/prediction-history', {
      params: { limit, with_learning: withLearning }
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Failed to fetch history')
    }

    return response.data
  } catch (error) {
    console.error('[getPredictionHistory] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch prediction history')
  }
}

// ============================================
// React Query Hooks for Optimized Caching
// ============================================

/**
 * Hook to fetch games list with aggressive caching
 * Cache key: ['games', date]
 * Stale time: 30 seconds (configured globally)
 */
export const useGames = (date = null) => {
  return useQuery({
    queryKey: ['games', date],
    queryFn: () => fetchGames(date),
    staleTime: 30_000,        // Fresh for 30 seconds
    cacheTime: 300_000,       // Keep in memory for 5 minutes
    refetchOnWindowFocus: false,
  })
}

/**
 * Hook to fetch game detail with prediction
 * Cache key: ['game-detail', gameId, bettingLine]
 * Stale time: 30 seconds
 *
 * Features:
 * - Shows cached result instantly on repeat views
 * - Refreshes in background if stale
 * - Deduplicates concurrent requests
 */
export const useGameDetail = (gameId, bettingLine = null) => {
  return useQuery({
    queryKey: ['game-detail', gameId, bettingLine],
    queryFn: () => fetchGameDetail(gameId, bettingLine),
    enabled: !!gameId,        // Only run if gameId is provided
    staleTime: 30_000,        // Consider data fresh for 30 seconds
    cacheTime: 300_000,       // Keep unused data in cache for 5 minutes
    retry: 1,                 // Only retry once on failure
    refetchOnWindowFocus: false,
    // Keep previous data while fetching new data (smoother UX)
    keepPreviousData: true,
  })
}

/**
 * Hook to fetch team stats with league rankings
 * Cache key: ['team-stats-ranks', teamId, season]
 * Stale time: 6 hours (rankings don't change frequently)
 */
export const useTeamStatsWithRanks = (teamId, season = '2025-26') => {
  return useQuery({
    queryKey: ['team-stats-ranks', teamId, season],
    queryFn: () => fetchTeamStatsWithRanks(teamId, season),
    enabled: !!teamId,
    staleTime: 21_600_000,    // Fresh for 6 hours (rankings change slowly)
    cacheTime: 86_400_000,    // Keep in memory for 24 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

// ============================================
// Team Stats Comparison (Season + Last-N)
// ============================================

/**
 * Fetch team stats comparison (season stats with ranks + last-N stats with deltas)
 */
export const fetchTeamStatsComparison = async (teamId, season = '2025-26', n = 5) => {
  try {
    const response = await api.get('/team-stats-comparison', {
      params: { team_id: teamId, season, n },
      timeout: 10000
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data
  } catch (error) {
    console.error('[fetchTeamStatsComparison] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch team stats comparison')
  }
}

/**
 * Hook to fetch team stats comparison (season + last-N)
 * Cache key: ['team-stats-comparison', teamId, season, n]
 * Stale time: 1 hour (last-N changes with new games)
 */
export const useTeamStatsComparison = (teamId, season = '2025-26', n = 5) => {
  return useQuery({
    queryKey: ['team-stats-comparison', teamId, season, n],
    queryFn: () => fetchTeamStatsComparison(teamId, season, n),
    enabled: !!teamId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

// ============================================
// Defense-Adjusted Scoring Splits
// ============================================

/**
 * Fetch defense-adjusted scoring splits for a single team
 */
export const fetchTeamScoringSplits = async (teamId, season = '2025-26') => {
  try {
    const response = await api.get('/team-scoring-splits', {
      params: { team_id: teamId, season },
      timeout: 10000
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data.data
  } catch (error) {
    console.error('[fetchTeamScoringSplits] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch team scoring splits')
  }
}

/**
 * Fetch defense-adjusted scoring splits for both teams in a game
 */
export const fetchGameScoringSplits = async (gameId, season = '2025-26') => {
  try {
    const response = await api.get('/game-scoring-splits', {
      params: { game_id: gameId, season },
      timeout: 10000
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data.data
  } catch (error) {
    console.error('[fetchGameScoringSplits] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch game scoring splits')
  }
}

/**
 * Hook to fetch team scoring splits
 * Cache key: ['team-scoring-splits', teamId, season]
 * Stale time: 1 hour (splits change with new game logs)
 */
export const useTeamScoringSplits = (teamId, season = '2025-26') => {
  return useQuery({
    queryKey: ['team-scoring-splits', teamId, season],
    queryFn: () => fetchTeamScoringSplits(teamId, season),
    enabled: !!teamId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Hook to fetch game scoring splits for both teams
 * Cache key: ['game-scoring-splits', gameId, season]
 * Stale time: 1 hour
 */
export const useGameScoringSplits = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-scoring-splits', gameId, season],
    queryFn: () => fetchGameScoringSplits(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

// ============================================
// Three-Point Scoring Splits
// ============================================

/**
 * Fetch 3PT defense-adjusted scoring splits for both teams in a game
 */
export const fetchGameThreePointScoringSplits = async (gameId, season = '2025-26') => {
  try {
    const response = await api.get('/game-three-pt-scoring-splits', {
      params: { game_id: gameId, season },
      timeout: 10000
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data.data
  } catch (error) {
    console.error('[fetchGameThreePointScoringSplits] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch 3PT scoring splits')
  }
}

/**
 * Hook to fetch game 3PT scoring splits for both teams
 * Cache key: ['game-three-pt-scoring-splits', gameId, season]
 * Stale time: 1 hour
 */
export const useGameThreePointScoringSplits = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-three-pt-scoring-splits', gameId, season],
    queryFn: () => fetchGameThreePointScoringSplits(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch 3PT scoring vs pace for both teams in a game
 */
const fetchGameThreePointScoringVsPace = async (gameId, season) => {
  try {
    const response = await axios.get('/api/game-three-pt-scoring-vs-pace', {
      params: { game_id: gameId, season }
    })

    console.log('[fetchGameThreePointScoringVsPace] Response:', response.data)

    if (!response.data?.success || !response.data?.data) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data.data
  } catch (error) {
    console.error('[fetchGameThreePointScoringVsPace] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch 3PT scoring vs pace')
  }
}

/**
 * Hook to fetch game 3PT scoring vs pace for both teams
 * Cache key: ['game-three-pt-scoring-vs-pace', gameId, season]
 * Stale time: 1 hour
 */
export const useGameThreePointScoringVsPace = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-three-pt-scoring-vs-pace', gameId, season],
    queryFn: () => fetchGameThreePointScoringVsPace(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch turnover vs defense pressure for both teams in a game
 */
const fetchGameTurnoverVsDefensePressure = async (gameId, season) => {
  try {
    const response = await axios.get('/api/game-turnover-vs-defense-pressure', {
      params: { game_id: gameId, season }
    })
    return response.data.data || {}
  } catch (error) {
    console.error('Error fetching turnover vs defense pressure:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch turnover vs defense pressure')
  }
}

/**
 * Hook to fetch game turnover vs defense pressure for both teams
 * Cache key: ['game-turnover-vs-defense-pressure', gameId, season]
 * Stale time: 1 hour
 */
export const useGameTurnoverVsDefensePressure = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-turnover-vs-defense-pressure', gameId, season],
    queryFn: () => fetchGameTurnoverVsDefensePressure(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch turnover vs pace for both teams in a game
 */
const fetchGameTurnoverVsPace = async (gameId, season) => {
  try {
    const response = await axios.get('/api/game-turnover-vs-pace', {
      params: { game_id: gameId, season }
    })
    return response.data.data || {}
  } catch (error) {
    console.error('Error fetching turnover vs pace:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch turnover vs pace')
  }
}

/**
 * Hook to fetch game turnover vs pace for both teams
 * Cache key: ['game-turnover-vs-pace', gameId, season]
 * Stale time: 1 hour
 */
export const useGameTurnoverVsPace = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-turnover-vs-pace', gameId, season],
    queryFn: () => fetchGameTurnoverVsPace(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch assists vs ball-movement defense for both teams in a game
 */
const fetchGameAssistsVsDefense = async (gameId, season) => {
  console.log('[fetchGameAssistsVsDefense] Called with gameId:', gameId, 'season:', season)
  try {
    const response = await api.get('/game-assists-vs-defense', {
      params: { game_id: gameId, season },
      timeout: 10000
    })
    console.log('[fetchGameAssistsVsDefense] Response:', response.data)
    return response.data.data || {}
  } catch (error) {
    console.error('[fetchGameAssistsVsDefense] ERROR:', error)
    console.error('[fetchGameAssistsVsDefense] Error response:', error.response)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch assists vs defense')
  }
}

/**
 * Hook to fetch game assists vs defense for both teams
 * Cache key: ['game-assists-vs-defense', gameId, season]
 * Stale time: 1 hour
 */
export const useGameAssistsVsDefense = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-assists-vs-defense', gameId, season],
    queryFn: () => fetchGameAssistsVsDefense(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch assists vs pace for both teams in a game
 */
const fetchGameAssistsVsPace = async (gameId, season) => {
  console.log('[fetchGameAssistsVsPace] Called with gameId:', gameId, 'season:', season)
  try {
    const response = await api.get('/game-assists-vs-pace', {
      params: { game_id: gameId, season },
      timeout: 10000
    })
    console.log('[fetchGameAssistsVsPace] Response:', response.data)
    return response.data.data || {}
  } catch (error) {
    console.error('[fetchGameAssistsVsPace] ERROR:', error)
    console.error('[fetchGameAssistsVsPace] Error response:', error.response)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch assists vs pace')
  }
}

/**
 * Hook to fetch game assists vs pace for both teams
 * Cache key: ['game-assists-vs-pace', gameId, season]
 * Stale time: 1 hour
 */
export const useGameAssistsVsPace = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-assists-vs-pace', gameId, season],
    queryFn: () => fetchGameAssistsVsPace(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch scoring mix splits for both teams in a game
 */
const fetchGameScoringMix = async (gameId, season = '2025-26') => {
  console.log('[fetchGameScoringMix] Called with gameId:', gameId, 'season:', season)
  try {
    const response = await api.get('/scoring-mix', {
      params: { game_id: gameId, season },
      timeout: 10000
    })
    console.log('[fetchGameScoringMix] Response:', response.data)
    return response.data.data || {}
  } catch (error) {
    console.error('[fetchGameScoringMix] ERROR:', error)
    console.error('[fetchGameScoringMix] Error response:', error.response)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch scoring mix')
  }
}

/**
 * Hook to fetch game scoring mix for both teams
 * Cache key: ['game-scoring-mix', gameId, season]
 * Stale time: 1 hour
 */
export const useGameScoringMix = (gameId, season = '2025-26') => {
  return useQuery({
    queryKey: ['game-scoring-mix', gameId, season],
    queryFn: () => fetchGameScoringMix(gameId, season),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

/**
 * Fetch full matchup summary writeup for a game
 */
const fetchFullMatchupSummaryWriteup = async (gameId) => {
  try {
    const response = await axios.get(`/api/game/${gameId}/full_matchup_summary_writeup`)
    return response.data.writeup || ''
  } catch (error) {
    console.error('Error fetching full matchup summary writeup:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch matchup summary writeup')
  }
}

/**
 * Hook to fetch full matchup summary writeup
 * Cache key: ['full-matchup-summary-writeup', gameId]
 * Stale time: 1 hour
 */
export const useFullMatchupSummaryWriteup = (gameId) => {
  return useQuery({
    queryKey: ['full-matchup-summary-writeup', gameId],
    queryFn: () => fetchFullMatchupSummaryWriteup(gameId),
    enabled: !!gameId,
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

// ============================================================================
// TEAM ARCHETYPES
// ============================================================================

/**
 * Fetch team archetypes
 */
export const fetchTeamArchetypes = async (teamId = null, season = '2025-26') => {
  try {
    const params = { season }
    if (teamId) {
      params.team_id = teamId
    }

    const response = await api.get('/team-archetypes', { params })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data.archetypes
  } catch (error) {
    console.error('[fetchTeamArchetypes] Error:', error)
    throw new Error(error.response?.data?.error || error.message || 'Failed to fetch team archetypes')
  }
}

/**
 * Hook to fetch team archetypes
 * Cache key: ['team-archetypes', teamId, season]
 * Stale time: 1 hour (archetypes don't change frequently)
 */
export const useTeamArchetypes = (teamId = null, season = '2025-26') => {
  return useQuery({
    queryKey: ['team-archetypes', teamId, season],
    queryFn: () => fetchTeamArchetypes(teamId, season),
    staleTime: 3_600_000,     // Fresh for 1 hour
    cacheTime: 7_200_000,     // Keep in memory for 2 hours
    retry: 1,
    refetchOnWindowFocus: false,
  })
}
