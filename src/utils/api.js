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
    // Vercel function has 60s max, so we timeout at 60s
    const response = await api.get('/game_detail', {
      params,
      timeout: 60000  // 60 seconds (Vercel function limit)
    })

    if (!response.data || !response.data.success) {
      throw new Error(response.data?.error || 'Invalid response from server')
    }

    return response.data
  } catch (error) {
    console.error('[fetchGameDetail] Error:', error)

    // Provide user-friendly error messages
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timed out after 60 seconds. The NBA Stats API is running slow. Please click "Try Again" to retry - it may work from cache on the second try.')
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
