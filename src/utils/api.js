import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const fetchGames = async (date = null) => {
  try {
    const params = date ? { date } : {}
    const response = await axios.get(`${API_BASE_URL}/games`, { params })
    return response.data
  } catch (error) {
    console.error('Error fetching games:', error)
    throw new Error(error.response?.data?.error || 'Failed to fetch games')
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
    const response = await axios.get(`${API_BASE_URL}/game_detail`, { params })
    return response.data
  } catch (error) {
    console.error('Error fetching game detail:', error)
    throw new Error(error.response?.data?.error || 'Failed to fetch game details')
  }
}
