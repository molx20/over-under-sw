import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Header from './components/Header'
import Home from './pages/Home'
import GamePage from './pages/GamePage'
import MatchupSummary from './pages/MatchupSummary'

// LocalStorage keys for persistent settings
export const STORAGE_KEYS = {
  DARK_MODE: 'nba_ou_dark_mode',
  LAST_SELECTED_DATE: 'nba_ou_last_selected_date',
}

function App() {
  // Initialize dark mode from localStorage
  const [darkMode, setDarkMode] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEYS.DARK_MODE)
    return stored === 'true'
  })

  // Persist dark mode to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.DARK_MODE, darkMode.toString())
    console.log('[App] Dark mode persisted:', darkMode)
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  return (
    <Router>
      <div className={darkMode ? 'dark' : ''}>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
          <Header
            darkMode={darkMode}
            toggleDarkMode={toggleDarkMode}
          />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/game/:gameId" element={<GamePage />} />
            <Route path="/game/:gameId/summary" element={<MatchupSummary />} />
          </Routes>
        </div>
      </div>
    </Router>
  )
}

export default App
