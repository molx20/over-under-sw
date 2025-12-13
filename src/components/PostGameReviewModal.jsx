import React, { useState, useEffect } from 'react';

/**
 * PostGameReviewModal - Modal for uploading final score screenshot
 *
 * Features:
 * - File upload (drag & drop + click)
 * - Image preview
 * - OpenAI Vision extraction
 * - AI coaching review display
 * - Load and display existing reviews
 *
 * Props:
 * - isOpen: boolean
 * - onClose: function
 * - gameData: { game_id, home_team, away_team, game_date, prediction }
 */
export default function PostGameReviewModal({ isOpen, onClose, gameData }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [reviewResult, setReviewResult] = useState(null);
  const [isLoadingExisting, setIsLoadingExisting] = useState(false);
  const [hasExistingReview, setHasExistingReview] = useState(false);

  // Load existing review when modal opens
  useEffect(() => {
    if (isOpen && gameData?.game_id) {
      loadExistingReview();
    } else {
      // Reset state when modal closes
      setReviewResult(null);
      setHasExistingReview(false);
      setSelectedFile(null);
      setPreviewUrl(null);
      setUploadError(null);
    }
  }, [isOpen, gameData?.game_id]);

  const loadExistingReview = async () => {
    setIsLoadingExisting(true);
    try {
      const response = await fetch(`/api/games/${gameData.game_id}/review`);
      const data = await response.json();

      if (data.success && data.review) {
        setReviewResult(data.review);
        setHasExistingReview(true);
        console.log('[PostGameReview] Loaded existing review:', data.review);
      } else {
        setHasExistingReview(false);
      }
    } catch (error) {
      console.error('[PostGameReview] Error loading existing review:', error);
      setHasExistingReview(false);
    } finally {
      setIsLoadingExisting(false);
    }
  };

  if (!isOpen) return null;

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const processFile = (file) => {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      setUploadError('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('Image must be smaller than 10MB');
      return;
    }

    setSelectedFile(file);
    setUploadError(null);
    setReviewResult(null);

    // Create preview URL
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleUpload = async () => {
    if (!selectedFile || !gameData) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      // Create FormData for multipart/form-data upload
      const formData = new FormData();
      formData.append('screenshot', selectedFile);
      formData.append('home_team', gameData.home_team);
      formData.append('away_team', gameData.away_team);
      formData.append('game_date', gameData.game_date);
      formData.append('predicted_home', gameData.prediction.breakdown.home_projected);
      formData.append('predicted_away', gameData.prediction.breakdown.away_projected);
      formData.append('predicted_total', gameData.prediction.predicted_total);
      formData.append('sportsbook_line', gameData.prediction.betting_line); // Add sportsbook line for WIN/LOSS determination

      const response = await fetch(`/api/games/${gameData.game_id}/result-screenshot`, {
        method: 'POST',
        body: formData
        // Don't set Content-Type header - browser will set it with boundary for multipart
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        // Check for specific error codes from backend
        if (data.code === 'OPENAI_KEY_MISSING') {
          throw new Error('The AI key is not set on the server. Add your OpenAI key in Railway, then reload and try again.');
        }
        throw new Error(data.error || 'I could not analyze this screenshot. Please try again.');
      }

      console.log('[PostGameReview] AI review response:', data.review);
      setReviewResult(data.review);
      setHasExistingReview(true); // Mark as saved after successful upload

    } catch (error) {
      console.error('[Review] Upload error:', error);
      setUploadError(error.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    // Clean up preview URL
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadError(null);
    setReviewResult(null);
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal Container */}
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">

            {/* Header */}
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 z-10">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {hasExistingReview ? 'Post-Game Analysis' : 'Upload Final Score'}
                </h2>
                <button
                  onClick={handleClose}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {hasExistingReview
                  ? 'Viewing previously saved AI Model Coach analysis'
                  : 'Upload a screenshot of the final box score to get AI analysis'}
              </p>
              {hasExistingReview && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Saved Review
                  </div>
                  <button
                    onClick={() => {
                      setHasExistingReview(false);
                      setReviewResult(null);
                    }}
                    className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-300 border border-primary-200 dark:border-primary-800 hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
                  >
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Upload New Screenshot
                  </button>
                </div>
              )}
            </div>

            {/* Content */}
            <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-140px)]">

              {/* Loading existing review */}
              {isLoadingExisting ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                  <p className="text-gray-600 dark:text-gray-400">Loading saved analysis...</p>
                </div>
              ) : reviewResult ? (
                <div className="space-y-4">
                  {/* Scores Comparison */}
                  <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Final Scores</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{reviewResult.home_team}</p>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-gray-900 dark:text-white">{reviewResult.actual_home}</span>
                          <span className="text-sm text-gray-500">(predicted {reviewResult.predicted_home.toFixed(1)})</span>
                        </div>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{reviewResult.away_team}</p>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-gray-900 dark:text-white">{reviewResult.actual_away}</span>
                          <span className="text-sm text-gray-500">(predicted {reviewResult.predicted_away.toFixed(1)})</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total</p>
                      <div className="flex items-baseline gap-3">
                        <span className="text-3xl font-bold text-gray-900 dark:text-white">{reviewResult.actual_total}</span>
                        <span className="text-sm text-gray-500">(predicted {reviewResult.predicted_total.toFixed(1)})</span>
                        <span className={`text-lg font-semibold ${reviewResult.error_total > 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {reviewResult.error_total > 0 ? '+' : ''}{reviewResult.error_total}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Detailed Style Stats Comparison */}
                  {reviewResult.expected_style_stats_json && reviewResult.actual_style_stats_json && (() => {
                    try {
                      const expected = JSON.parse(reviewResult.expected_style_stats_json);
                      const actual = JSON.parse(reviewResult.actual_style_stats_json);

                      if (!expected.home || !expected.away || !actual.home || !actual.away) {
                        return null;
                      }

                      // Helper to format numbers and calculate difference
                      const formatStat = (val) => val !== null && val !== undefined ? val : '—';
                      const calcDiff = (exp, act) => {
                        if (exp === null || act === null || exp === undefined || act === undefined) return null;
                        const diff = act - exp;
                        return diff > 0 ? `+${diff.toFixed(1)}` : diff.toFixed(1);
                      };

                      // Helper to color code differences
                      const getDiffColor = (diff) => {
                        if (!diff || diff === '—') return 'text-gray-500';
                        const val = parseFloat(diff);
                        if (val > 0) return 'text-green-600 dark:text-green-400';
                        if (val < 0) return 'text-red-600 dark:text-red-400';
                        return 'text-gray-500';
                      };

                      return (
                        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
                          <h3 className="font-semibold text-purple-900 dark:text-purple-300 mb-3">Detailed Style Stats Comparison</h3>

                          {/* Home Team Stats */}
                          <div className="mb-4">
                            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                              {reviewResult.home_team}
                            </h4>
                            <div className="overflow-x-auto">
                              <table className="min-w-full text-xs">
                                <thead>
                                  <tr className="border-b border-purple-200 dark:border-purple-700">
                                    <th className="text-left py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Stat</th>
                                    <th className="text-right py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Expected</th>
                                    <th className="text-right py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Actual</th>
                                    <th className="text-right py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Diff</th>
                                  </tr>
                                </thead>
                                <tbody className="text-gray-700 dark:text-gray-300">
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Pace</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.pace)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.pace)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.pace, actual.home.pace))}`}>
                                      {calcDiff(expected.home.pace, actual.home.pace) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">FG%</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.fg_pct)}%</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.fg_pct)}%</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.fg_pct, actual.home.fg_pct))}`}>
                                      {calcDiff(expected.home.fg_pct, actual.home.fg_pct) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">3PA</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.fg3a)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.fg3a)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.fg3a, actual.home.fg3a))}`}>
                                      {calcDiff(expected.home.fg3a, actual.home.fg3a) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">3P%</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.fg3_pct)}%</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.fg3_pct)}%</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.fg3_pct, actual.home.fg3_pct))}`}>
                                      {calcDiff(expected.home.fg3_pct, actual.home.fg3_pct) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">FTA</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.fta)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.fta)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.fta, actual.home.fta))}`}>
                                      {calcDiff(expected.home.fta, actual.home.fta) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Rebounds</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.reb)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.reb)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.reb, actual.home.reb))}`}>
                                      {calcDiff(expected.home.reb, actual.home.reb) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Assists</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.assists)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.assists)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.assists, actual.home.assists))}`}>
                                      {calcDiff(expected.home.assists, actual.home.assists) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Turnovers</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.turnovers)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.turnovers)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.turnovers, actual.home.turnovers))}`}>
                                      {calcDiff(expected.home.turnovers, actual.home.turnovers) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Paint Pts</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.paint_points)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.paint_points)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.paint_points, actual.home.paint_points))}`}>
                                      {calcDiff(expected.home.paint_points, actual.home.paint_points) || '—'}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td className="py-1 px-2">Fastbreak Pts</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.home.fastbreak_points)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.home.fastbreak_points)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.home.fastbreak_points, actual.home.fastbreak_points))}`}>
                                      {calcDiff(expected.home.fastbreak_points, actual.home.fastbreak_points) || '—'}
                                    </td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Away Team Stats */}
                          <div>
                            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                              {reviewResult.away_team}
                            </h4>
                            <div className="overflow-x-auto">
                              <table className="min-w-full text-xs">
                                <thead>
                                  <tr className="border-b border-purple-200 dark:border-purple-700">
                                    <th className="text-left py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Stat</th>
                                    <th className="text-right py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Expected</th>
                                    <th className="text-right py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Actual</th>
                                    <th className="text-right py-1 px-2 font-medium text-gray-600 dark:text-gray-400">Diff</th>
                                  </tr>
                                </thead>
                                <tbody className="text-gray-700 dark:text-gray-300">
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Pace</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.pace)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.pace)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.pace, actual.away.pace))}`}>
                                      {calcDiff(expected.away.pace, actual.away.pace) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">FG%</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.fg_pct)}%</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.fg_pct)}%</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.fg_pct, actual.away.fg_pct))}`}>
                                      {calcDiff(expected.away.fg_pct, actual.away.fg_pct) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">3PA</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.fg3a)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.fg3a)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.fg3a, actual.away.fg3a))}`}>
                                      {calcDiff(expected.away.fg3a, actual.away.fg3a) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">3P%</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.fg3_pct)}%</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.fg3_pct)}%</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.fg3_pct, actual.away.fg3_pct))}`}>
                                      {calcDiff(expected.away.fg3_pct, actual.away.fg3_pct) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">FTA</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.fta)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.fta)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.fta, actual.away.fta))}`}>
                                      {calcDiff(expected.away.fta, actual.away.fta) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Rebounds</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.reb)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.reb)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.reb, actual.away.reb))}`}>
                                      {calcDiff(expected.away.reb, actual.away.reb) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Assists</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.assists)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.assists)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.assists, actual.away.assists))}`}>
                                      {calcDiff(expected.away.assists, actual.away.assists) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Turnovers</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.turnovers)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.turnovers)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.turnovers, actual.away.turnovers))}`}>
                                      {calcDiff(expected.away.turnovers, actual.away.turnovers) || '—'}
                                    </td>
                                  </tr>
                                  <tr className="border-b border-purple-100 dark:border-purple-800/50">
                                    <td className="py-1 px-2">Paint Pts</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.paint_points)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.paint_points)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.paint_points, actual.away.paint_points))}`}>
                                      {calcDiff(expected.away.paint_points, actual.away.paint_points) || '—'}
                                    </td>
                                  </tr>
                                  <tr>
                                    <td className="py-1 px-2">Fastbreak Pts</td>
                                    <td className="text-right py-1 px-2">{formatStat(expected.away.fastbreak_points)}</td>
                                    <td className="text-right py-1 px-2 font-medium">{formatStat(actual.away.fastbreak_points)}</td>
                                    <td className={`text-right py-1 px-2 font-medium ${getDiffColor(calcDiff(expected.away.fastbreak_points, actual.away.fastbreak_points))}`}>
                                      {calcDiff(expected.away.fastbreak_points, actual.away.fastbreak_points) || '—'}
                                    </td>
                                  </tr>
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>
                      );
                    } catch (error) {
                      console.error('[PostGameReview] Error parsing style stats:', error);
                      return null;
                    }
                  })()}

                  {/* AI Model Coach v2 Review */}
                  {reviewResult.ai_review && (
                    <div className="space-y-3">
                      {/* Verdict & Headline (v2) */}
                      {reviewResult.ai_review.verdict && (
                        <div className={`rounded-lg p-4 border ${
                          reviewResult.ai_review.verdict === 'WIN'
                            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                            : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`text-2xl ${
                              reviewResult.ai_review.verdict === 'WIN' ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {reviewResult.ai_review.verdict === 'WIN' ? '✓' : '✗'}
                            </span>
                            <h4 className={`font-bold text-lg ${
                              reviewResult.ai_review.verdict === 'WIN'
                                ? 'text-green-900 dark:text-green-300'
                                : 'text-red-900 dark:text-red-300'
                            }`}>
                              {reviewResult.ai_review.verdict}
                            </h4>
                          </div>
                          <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                            {reviewResult.ai_review.headline}
                          </p>
                        </div>
                      )}

                      {/* Game Summary (v2) */}
                      {reviewResult.ai_review.game_summary && (
                        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                          <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">What Happened</h4>
                          <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.game_summary}</p>
                        </div>
                      )}

                      {/* Game Style (v2) */}
                      {reviewResult.ai_review.game_style && (
                        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4">
                          <h4 className="font-semibold text-indigo-900 dark:text-indigo-300 mb-2">Game Style</h4>
                          <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.game_style}</p>
                        </div>
                      )}

                      {/* Expected vs Actual (v2) */}
                      {reviewResult.ai_review.expected_vs_actual && (
                        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
                          <h4 className="font-semibold text-gray-900 dark:text-white mb-3">Expected vs Actual</h4>
                          <div className="space-y-2">
                            {reviewResult.ai_review.expected_vs_actual.pace && (
                              <div>
                                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase">Pace:</span>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.expected_vs_actual.pace}</p>
                              </div>
                            )}
                            {reviewResult.ai_review.expected_vs_actual.shooting && (
                              <div>
                                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase">Shooting:</span>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.expected_vs_actual.shooting}</p>
                              </div>
                            )}
                            {reviewResult.ai_review.expected_vs_actual.free_throws && (
                              <div>
                                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase">Free Throws:</span>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.expected_vs_actual.free_throws}</p>
                              </div>
                            )}
                            {reviewResult.ai_review.expected_vs_actual.turnovers && (
                              <div>
                                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase">Turnovers:</span>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.expected_vs_actual.turnovers}</p>
                              </div>
                            )}
                            {reviewResult.ai_review.expected_vs_actual.three_point_volume && (
                              <div>
                                <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase">3PT Volume:</span>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.expected_vs_actual.three_point_volume}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Trend Notes (v2) */}
                      {reviewResult.ai_review.trend_notes && (
                        <div className="bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded-lg p-4">
                          <h4 className="font-semibold text-cyan-900 dark:text-cyan-300 mb-2">Recent Trends</h4>
                          <p className="text-sm text-gray-700 dark:text-gray-300">{reviewResult.ai_review.trend_notes}</p>
                        </div>
                      )}

                      {/* Pipeline Analysis (v2) */}
                      {reviewResult.ai_review.pipeline_analysis && (
                        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                          <h4 className="font-semibold text-amber-900 dark:text-amber-300 mb-3">Pipeline Analysis</h4>
                          <div className="space-y-2 text-sm">
                            {reviewResult.ai_review.pipeline_analysis.baseline && (
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">Baseline: </span>
                                <span className="text-gray-600 dark:text-gray-400">{reviewResult.ai_review.pipeline_analysis.baseline}</span>
                              </div>
                            )}
                            {reviewResult.ai_review.pipeline_analysis.defense_adjustment && (
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">Defense: </span>
                                <span className="text-gray-600 dark:text-gray-400">{reviewResult.ai_review.pipeline_analysis.defense_adjustment}</span>
                              </div>
                            )}
                            {reviewResult.ai_review.pipeline_analysis.pace_adjustment && (
                              <div>
                                <span className="font-medium text-gray-700 dark:text-gray-300">Pace: </span>
                                <span className="text-gray-600 dark:text-gray-400">{reviewResult.ai_review.pipeline_analysis.pace_adjustment}</span>
                              </div>
                            )}
                            {reviewResult.ai_review.pipeline_analysis.overall && (
                              <div className="mt-2 pt-2 border-t border-amber-200 dark:border-amber-700">
                                <span className="font-medium text-gray-700 dark:text-gray-300">Overall: </span>
                                <span className="text-gray-600 dark:text-gray-400">{reviewResult.ai_review.pipeline_analysis.overall}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Key Drivers (v2) */}
                      {reviewResult.ai_review.key_drivers && reviewResult.ai_review.key_drivers.length > 0 && (
                        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
                          <h4 className="font-semibold text-orange-900 dark:text-orange-300 mb-2">Key Drivers</h4>
                          <ul className="space-y-1">
                            {reviewResult.ai_review.key_drivers.map((driver, index) => (
                              <li key={index} className="text-sm text-gray-700 dark:text-gray-300 flex items-start">
                                <span className="text-orange-600 dark:text-orange-400 mr-2">•</span>
                                <span>{driver}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Model Lessons (v2) */}
                      {reviewResult.ai_review.model_lessons && reviewResult.ai_review.model_lessons.length > 0 && (
                        <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
                          <h4 className="font-semibold text-purple-900 dark:text-purple-300 mb-2">Model Lessons</h4>
                          <ul className="space-y-1">
                            {reviewResult.ai_review.model_lessons.map((lesson, index) => (
                              <li key={index} className="text-sm text-gray-700 dark:text-gray-300 flex items-start">
                                <span className="text-purple-600 dark:text-purple-400 mr-2">→</span>
                                <span>{lesson}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Vision Confidence */}
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>Vision confidence: {reviewResult.vision_confidence}</span>
                    <span>Powered by OpenAI</span>
                  </div>
                </div>
              ) : (
                <>
                  {/* File Upload Area */}
                  {!selectedFile ? (
                    <div
                      onDrop={handleDrop}
                      onDragOver={handleDragOver}
                      className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center hover:border-primary-500 transition-colors cursor-pointer"
                    >
                      <input
                        type="file"
                        id="screenshot-upload"
                        accept="image/*"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                      <label htmlFor="screenshot-upload" className="cursor-pointer">
                        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                          Drag and drop your screenshot here, or click to browse
                        </p>
                        <p className="mt-1 text-xs text-gray-500">PNG, JPG, or WEBP (max 10MB)</p>
                      </label>
                    </div>
                  ) : (
                    /* Preview & Upload */
                    <div className="space-y-4">
                      <div className="relative">
                        <img
                          src={previewUrl}
                          alt="Preview"
                          className="w-full rounded-lg border border-gray-200 dark:border-gray-700"
                        />
                        {!isUploading && (
                          <button
                            onClick={() => {
                              URL.revokeObjectURL(previewUrl);
                              setSelectedFile(null);
                              setPreviewUrl(null);
                            }}
                            className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full p-1 transition-colors"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>

                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                      </p>

                      {uploadError && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                          <p className="text-sm text-red-800 dark:text-red-300">{uploadError}</p>
                        </div>
                      )}

                      <button
                        onClick={handleUpload}
                        disabled={isUploading}
                        className="w-full px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center space-x-2"
                      >
                        {isUploading ? (
                          <>
                            <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                            <span>Processing with AI...</span>
                          </>
                        ) : (
                          <>
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <span>Analyze with AI</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
              <button
                onClick={handleClose}
                className="w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-medium rounded-lg transition-colors"
              >
                {reviewResult ? 'Done' : 'Cancel'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
