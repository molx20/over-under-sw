import { useState } from 'react'
import {
  computeStep1,
  computeStep2,
  getStep3Content,
  getStep1DisplayColor,
  getStep2DisplayColor
} from '../utils/decisionStepsHelpers'

/**
 * Empty Possessions Gauge Component
 *
 * Displays possession efficiency analysis to protect against "fake pace" overs.
 * Shows TO%, OREB%, and FTr metrics with opponent context and a conversion gauge.
 */
function EmptyPossessionsGauge({ homeTeam, awayTeam, emptyPossessionsData }) {
  const [showGlossary, setShowGlossary] = useState(false)
  const [showStep3Modal, setShowStep3Modal] = useState(false)

  // Loading state
  if (!emptyPossessionsData) {
    return (
      <div className="border rounded-lg p-6 bg-white dark:bg-gray-800">
        <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-gray-100">
          Empty Possessions Analysis
        </h3>
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>Loading possession efficiency data...</p>
        </div>
      </div>
    )
  }

  // Extract data
  const homeData = emptyPossessionsData.home_team
  const awayData = emptyPossessionsData.away_team
  const matchupScore = emptyPossessionsData.matchup_score
  const matchupSummary = emptyPossessionsData.matchup_summary

  // Compute decision steps
  const step1Result = computeStep1(
    awayData?.blended_score || 0,
    homeData?.blended_score || 0,
    { abbreviation: awayTeam?.abbreviation, full_name: awayTeam?.full_name },
    { abbreviation: homeTeam?.abbreviation, full_name: homeTeam?.full_name }
  )
  const step2Result = computeStep2(step1Result)
  const step3Content = getStep3Content(step2Result)

  // Determine gauge color based on score
  const getScoreColor = (score) => {
    if (score >= 67) return 'text-green-600 dark:text-green-400'
    if (score >= 33) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  return (
    <div className="border rounded-lg p-6 bg-white dark:bg-gray-800 shadow-sm">
      {/* Header with title + info icon + glossary toggle */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
            Empty Possessions Analysis
          </h3>
          {/* Info icon for Step 3 */}
          <button
            onClick={() => setShowStep3Modal(true)}
            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
            title="View Line Check Instructions"
            aria-label="View Step 3 line check instructions"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <button
          onClick={() => setShowGlossary(!showGlossary)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          {showGlossary ? 'Hide' : 'Show'} Glossary
        </button>
      </div>

      {/* Collapsible Glossary */}
      {showGlossary && <GlossarySection />}

      {/* Main Gauge Bar */}
      <div className="mb-6">
        <div className="relative h-6 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          {/* Red segment (0-33) */}
          <div className="absolute left-0 h-full w-[33%] bg-red-500 dark:bg-red-600" />
          {/* Yellow segment (33-67) */}
          <div className="absolute left-[33%] h-full w-[34%] bg-yellow-500 dark:bg-yellow-600" />
          {/* Green segment (67-100) */}
          <div className="absolute left-[67%] h-full w-[33%] bg-green-500 dark:bg-green-600" />
          {/* Score indicator */}
          <div
            className="absolute top-0 h-full w-1 bg-black dark:bg-white z-10"
            style={{ left: `${Math.max(0, Math.min(100, matchupScore))}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-600 dark:text-gray-400">
          <span>Poor</span>
          <span className={`font-bold text-lg ${getScoreColor(matchupScore)}`}>
            {matchupScore}
          </span>
          <span>Excellent</span>
        </div>
      </div>

      {/* Team Sections + Decision Steps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Team A (Away) - Left column */}
        <TeamSection team={awayTeam} data={awayData} />

        {/* Team B (Home) + Decision Steps - Right column */}
        <div className="space-y-4">
          <TeamSection team={homeTeam} data={homeData} />
          <DecisionStepsPanel
            step1Result={step1Result}
            step2Result={step2Result}
          />
        </div>
      </div>

      {/* Matchup Summary */}
      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900 rounded">
        <p className="text-sm text-center text-gray-800 dark:text-gray-200">
          {matchupSummary}
        </p>
      </div>

      {/* Step 3 Modal */}
      {showStep3Modal && (
        <Step3Modal
          isOpen={showStep3Modal}
          onClose={() => setShowStep3Modal(false)}
          content={step3Content}
          step2Result={step2Result}
        />
      )}
    </div>
  )
}

/**
 * Team Section Component
 * Shows individual team metrics with opponent context
 */
function TeamSection({ team, data }) {
  // Get team name with fallback priority
  const teamName = team?.full_name || team?.name || team?.tricode || team?.abbreviation || 'Team'

  if (!data) {
    return (
      <div className="border rounded p-4 bg-gray-50 dark:bg-gray-700">
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {teamName}
        </h4>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Insufficient data
        </p>
      </div>
    )
  }

  return (
    <div className="border rounded p-4 bg-gray-50 dark:bg-gray-700">
      <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
        {teamName}
      </h4>

      <div className="space-y-3 mb-4">
        <MetricIndicator
          label="TO%"
          season={data.season.to_pct}
          last5={data.last5.to_pct}
          trend={data.opp_context.to_trend}
          inverted={true}
        />
        <MetricIndicator
          label="OREB%"
          season={data.season.oreb_pct}
          last5={data.last5.oreb_pct}
          trend={data.opp_context.oreb_trend}
        />
        <MetricIndicator
          label="FTr"
          season={data.season.ftr}
          last5={data.last5.ftr}
          trend={data.opp_context.ftr_trend}
        />
      </div>

      {/* Blended Score Badge */}
      <div className="mt-4 pt-4 border-t border-gray-300 dark:border-gray-600">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Conversion Score
          </span>
          <span className={`text-2xl font-bold ${getScoreColorClass(data.blended_score)}`}>
            {data.blended_score}
          </span>
        </div>
      </div>
    </div>
  )
}

/**
 * Metric Indicator Component
 * Shows individual metric with season/last5 values and trend arrow
 */
function MetricIndicator({ label, season, last5, trend, inverted = false }) {
  // Determine arrow and color
  const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  const arrowColor = trend === 'up'
    ? (inverted ? 'text-red-500' : 'text-green-500')
    : trend === 'down'
    ? (inverted ? 'text-green-500' : 'text-red-500')
    : 'text-gray-500'

  return (
    <div className="flex justify-between items-center">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </span>
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-600 dark:text-gray-400">
          Season: {season !== null ? `${season}%` : 'N/A'} | L5: {last5 !== null ? `${last5}%` : 'N/A'}
        </span>
        <span className={`text-lg font-bold ${arrowColor}`}>{arrow}</span>
      </div>
    </div>
  )
}

/**
 * Glossary Section Component
 * Explains the metrics
 */
function GlossarySection() {
  return (
    <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-700 rounded text-sm">
      <h4 className="font-bold mb-2 text-gray-900 dark:text-gray-100">
        Metrics Explained
      </h4>
      <ul className="space-y-2 text-gray-700 dark:text-gray-300">
        <li>
          <strong>TO% (Turnover Rate):</strong> Turnovers per possession. Lower is better
          - indicates better ball security and fewer wasted possessions.
        </li>
        <li>
          <strong>OREB% (Offensive Rebound Rate):</strong> Offensive rebounds captured.
          Higher is better - means more second-chance scoring opportunities.
        </li>
        <li>
          <strong>FTr (Free Throw Rate):</strong> Free throw attempts relative to field goals.
          Higher is better - indicates ability to draw fouls and get easy points.
        </li>
        <li>
          <strong>Arrows:</strong> Show if team's Last 5 performance is better (↑),
          worse (↓), or similar (→) compared to season average in this matchup context.
        </li>
        <li>
          <strong>Conversion Score:</strong> Blended 0-100 score combining all three metrics
          with opponent defense context. Accounts for what each team typically does on offense
          and what their opponent typically allows on defense.
        </li>
      </ul>
    </div>
  )
}

/**
 * Decision Steps Panel Component
 * Displays Step 1 (Edge Type) and Step 2 (Market Type) as compact cards
 */
function DecisionStepsPanel({ step1Result, step2Result }) {
  return (
    <div className="space-y-3">
      {/* Step 1 - Edge Type Card */}
      <div className={`border rounded-lg p-4 ${getStep1DisplayColor(step1Result.edgeType)}`}>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
            Step 1 — Edge Type
          </h4>
          <span className={`text-xs font-semibold px-2 py-1 rounded ${getStep1DisplayColor(step1Result.edgeType)}`}>
            {step1Result.edgeType.replace(/-/g, ' ').toUpperCase()}
          </span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          {step1Result.summary}
        </p>
        <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          Gap: {step1Result.gap.toFixed(1)} | Combined: {step1Result.combined.toFixed(1)}
        </div>
      </div>

      {/* Step 2 - Market Type Card */}
      <div className={`border rounded-lg p-4 ${getStep2DisplayColor(step2Result.marketType)}`}>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
            Step 2 — Market Type
          </h4>
          <span className={`text-xs font-semibold px-2 py-1 rounded ${getStep2DisplayColor(step2Result.marketType)}`}>
            {step2Result.marketType.replace(/-/g, ' ').toUpperCase()}
          </span>
        </div>
        <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
          Check: {step2Result.primaryMarket}
        </p>
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
          {step2Result.recommendation}
        </p>
      </div>

      {/* Hint to user */}
      <div className="text-center">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Click the <span className="text-blue-600 dark:text-blue-400 font-semibold">ⓘ</span> icon above for line check instructions
        </p>
      </div>
    </div>
  )
}

/**
 * Step 3 Modal Component
 * Full-screen modal with line check instructions (contextual based on Step 2)
 */
function Step3Modal({ isOpen, onClose, content, step2Result }) {
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[85vh] overflow-hidden">

            {/* Sticky Header */}
            <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 z-10">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  Step 3 — Line Check
                </h2>
                <button
                  onClick={onClose}
                  className="text-white hover:text-gray-200 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Market Badge */}
              <div className="mt-3">
                <span className="inline-block px-3 py-1 bg-white/20 backdrop-blur-sm rounded-full text-sm font-semibold text-white">
                  Market: {step2Result.primaryMarket}
                </span>
              </div>
            </div>

            {/* Scrollable Content */}
            <div className="px-6 py-6 overflow-y-auto max-h-[calc(85vh-140px)]">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                {content.title}
              </h3>

              {/* Instructions Section */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
                  What to do:
                </h4>
                <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                  {content.instructions.map((instruction, idx) => (
                    <li key={idx} className="flex items-start">
                      <span className="mr-2 text-blue-600 dark:text-blue-400 font-bold">
                        {idx + 1}.
                      </span>
                      <span>{instruction}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Examples (if provided) */}
              {content.examples?.length > 0 && (
                <div className="mb-6">
                  <h4 className="font-semibold text-gray-900 dark:text-white mb-3">
                    Examples:
                  </h4>
                  <div className="space-y-3">
                    {content.examples.map((example, idx) => (
                      <div key={idx} className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{example}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Warnings (if provided) */}
              {content.warnings?.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                  <h4 className="font-semibold text-yellow-800 dark:text-yellow-400 mb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    Important Notes:
                  </h4>
                  <ul className="space-y-1 text-sm text-yellow-700 dark:text-yellow-300">
                    {content.warnings.map((warning, idx) => (
                      <li key={idx} className="flex items-start">
                        <span className="mr-2">•</span>
                        <span>{warning}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Sticky Footer */}
            <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-end">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>

          </div>
        </div>
      </div>
    </>
  )
}

/**
 * Helper function to get score color class
 */
function getScoreColorClass(score) {
  if (score >= 67) return 'text-green-600 dark:text-green-400'
  if (score >= 50) return 'text-green-500 dark:text-green-300'
  if (score >= 33) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

export default EmptyPossessionsGauge
