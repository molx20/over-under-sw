import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './styles/mobile-first.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create QueryClient with aggressive caching for instant loads
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // Consider data fresh for 30 seconds
      cacheTime: 300_000,       // Keep unused data in cache for 5 minutes
      retry: 1,                 // Only retry once on failure
      refetchOnWindowFocus: false, // Don't refetch when user returns to tab
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
