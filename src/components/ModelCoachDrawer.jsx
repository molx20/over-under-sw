import React, { useState, useEffect } from 'react';

/**
 * ModelCoachDrawer - Sliding drawer showing daily model performance
 *
 * Features:
 * - Slides in from right
 * - Shows aggregate stats for today's games
 * - AI-generated coaching summary
 * - Biggest miss and biggest win
 * - Actionable improvement suggestions
 *
 * Props:
 * - isOpen: boolean
 * - onClose: function
 */
export default function ModelCoachDrawer({ isOpen, onClose }) {
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    if (isOpen) {
      fetchSummary(selectedDate);
    }
  }, [isOpen, selectedDate]);

  const fetchSummary = async (date) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/model-review/summary?date=${date}`);
      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to load summary');
      }

      setSummary(data.summary);
    } catch (err) {
      console.error('[Model Coach] Error fetching summary:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-full sm:w-96 bg-white dark:bg-gray-800 shadow-xl z-50 overflow-y-auto transform transition-transform">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-4 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Today's Model Coach
              </h2>
              <p className="text-sm opacity-90 mt-1">AI-powered performance review</p>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:bg-white/20 rounded-full p-2 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Date Selector */}
          <div className="mt-4">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 rounded-lg bg-white/20 text-white placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-white/50"
            />
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {isLoading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">Loading summary...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
            </div>
          )}

          {!isLoading && !error && summary && (
            <>
              {summary.total_games === 0 ? (
                <div className="text-center py-12">
                  <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-gray-600 dark:text-gray-400">No reviews available for this date yet.</p>
                  <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">Upload final scores to see analysis here!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Aggregate Stats */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Performance Stats</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Games Reviewed</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.total_games}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg Error</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.avg_error} pts</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Within 3 pts</p>
                        <p className="text-xl font-bold text-green-600">{summary.games_within_3}/{summary.total_games}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Within 7 pts</p>
                        <p className="text-xl font-bold text-blue-600">{summary.games_within_7}/{summary.total_games}</p>
                      </div>
                    </div>
                  </div>

                  {/* Overall Performance */}
                  {summary.overall_performance && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                      <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-2 flex items-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        Overall Performance
                      </h4>
                      <p className="text-sm text-gray-700 dark:text-gray-300">{summary.overall_performance}</p>
                    </div>
                  )}

                  {/* Biggest Miss */}
                  {summary.biggest_miss && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                      <h4 className="font-semibold text-red-900 dark:text-red-300 mb-2">Biggest Miss</h4>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-1">{summary.biggest_miss.game}</p>
                      <p className="text-lg font-bold text-red-600">Error: {summary.biggest_miss.error > 0 ? '+' : ''}{summary.biggest_miss.error} pts</p>
                    </div>
                  )}

                  {/* Biggest Win */}
                  {summary.biggest_win && (
                    <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                      <h4 className="font-semibold text-green-900 dark:text-green-300 mb-2">Most Accurate</h4>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-1">{summary.biggest_win.game}</p>
                      <p className="text-lg font-bold text-green-600">Error: {summary.biggest_win.error > 0 ? '+' : ''}{summary.biggest_win.error} pts</p>
                    </div>
                  )}

                  {/* Patterns */}
                  {summary.patterns && summary.patterns.length > 0 && (
                    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                      <h4 className="font-semibold text-amber-900 dark:text-amber-300 mb-2">Patterns Detected</h4>
                      <ul className="space-y-1">
                        {summary.patterns.map((pattern, index) => (
                          <li key={index} className="text-sm text-gray-700 dark:text-gray-300 flex items-start">
                            <span className="text-amber-600 dark:text-amber-400 mr-2">•</span>
                            <span>{pattern}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Action Items */}
                  {summary.action_items && summary.action_items.length > 0 && (
                    <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
                      <h4 className="font-semibold text-purple-900 dark:text-purple-300 mb-2 flex items-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                        </svg>
                        Action Items
                      </h4>
                      <ul className="space-y-1">
                        {summary.action_items.map((item, index) => (
                          <li key={index} className="text-sm text-gray-700 dark:text-gray-300 flex items-start">
                            <span className="text-purple-600 dark:text-purple-400 mr-2">→</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Powered by OpenAI */}
                  <div className="text-center pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Powered by OpenAI GPT-4.1</p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
