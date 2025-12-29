/**
 * DecisionCard Component
 *
 * Main decision display card showing Over/Under/Pass recommendation
 * with 3 driver metrics, archetype matchup, margin risk, and volatility
 */

import { useState } from 'react'
import DriverCard from './DriverCard'
import WhyThisPickPanel from './WhyThisPickPanel'

function DecisionCard({
  decision,
  drivers,
  archetype,
  marginRisk,
  volatility
}) {
  const [showWhy, setShowWhy] = useState(false)

  // Call badge styling based on decision
  const callStyles = {
    OVER: {
      bg: 'bg-gradient-to-r from-green-600 to-green-500',
      text: 'text-white',
      shadow: 'shadow-lg shadow-green-500/50'
    },
    UNDER: {
      bg: 'bg-gradient-to-r from-red-600 to-red-500',
      text: 'text-white',
      shadow: 'shadow-lg shadow-red-500/50'
    },
    PASS: {
      bg: 'bg-gradient-to-r from-gray-600 to-gray-500',
      text: 'text-white',
      shadow: 'shadow-lg shadow-gray-500/50'
    }
  }

  const callStyle = callStyles[decision.call] || callStyles.PASS

  // Confidence badge color
  const confidenceColors = {
    HIGH: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    LOW: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Call Badge (Large Header) */}
      <div className={`${callStyle.bg} ${callStyle.shadow} p-6 text-center`}>
        <div className="flex flex-col items-center gap-2">
          <h2 className={`text-3xl sm:text-4xl font-bold ${callStyle.text}`}>
            {decision.call}
          </h2>
          <div className={`
            px-4 py-2 rounded-full text-sm font-semibold
            ${confidenceColors[decision.confidenceLabel]}
          `}>
            {decision.confidenceLabel} CONFIDENCE ({decision.confidence}%)
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* 3 Driver Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <DriverCard
            label="FT Points"
            value={drivers.ftPoints.value}
            target={drivers.ftPoints.target}
            status={drivers.ftPoints.status}
          />
          <DriverCard
            label="Paint Points"
            value={drivers.paintPoints.value}
            target={drivers.paintPoints.target}
            status={drivers.paintPoints.status}
          />
          <DriverCard
            label="eFG%"
            value={drivers.efg.value}
            target={drivers.efg.target}
            status={drivers.efg.status}
            subtitle="%"
          />
        </div>

        {/* Archetype Matchup Badge */}
        {archetype && archetype.cluster_name && (
          <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-2xl">🎯</span>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-semibold text-primary-900 dark:text-primary-100">
                    Archetype Matchup
                  </h3>
                  <span className={`
                    px-2 py-0.5 rounded text-xs font-medium
                    ${archetype.confidence === 'high' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : ''}
                    ${archetype.confidence === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' : ''}
                    ${archetype.confidence === 'low' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' : ''}
                  `}>
                    {archetype.confidence} ({archetype.sample_size || 0} games)
                  </span>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                  {archetype.cluster_name}
                </p>
                {archetype.cluster_description && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {archetype.cluster_description}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Margin Risk & Volatility */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Margin Risk */}
          {marginRisk && marginRisk.label && (
            <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <span className="text-2xl">⚖️</span>
              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Margin Risk</div>
                <div className={`text-sm font-semibold ${
                  marginRisk.label === 'Blowout Risk'
                    ? 'text-red-700 dark:text-red-300'
                    : 'text-green-700 dark:text-green-300'
                }`}>
                  {marginRisk.label}
                </div>
              </div>
            </div>
          )}

          {/* Volatility */}
          {volatility && volatility.label && (
            <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <span className="text-2xl">📊</span>
              <div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Volatility</div>
                <div className={`text-sm font-semibold ${
                  volatility.label === 'Stable'
                    ? 'text-green-700 dark:text-green-300'
                    : volatility.label === 'Swingy'
                    ? 'text-yellow-700 dark:text-yellow-300'
                    : 'text-red-700 dark:text-red-300'
                }`}>
                  {volatility.label} ({volatility.index?.toFixed(1) || '5.0'}/10)
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Why This Pick Button */}
        <button
          onClick={() => setShowWhy(!showWhy)}
          className="
            w-full py-3 px-4 rounded-lg
            bg-blue-100 dark:bg-blue-900/30
            hover:bg-blue-200 dark:hover:bg-blue-900/50
            border border-blue-300 dark:border-blue-700
            text-blue-900 dark:text-blue-100
            font-semibold text-sm
            transition-colors
            flex items-center justify-center gap-2
          "
        >
          <span>{showWhy ? '▲' : '▼'}</span>
          <span>Why This Pick?</span>
        </button>

        {/* Why This Pick Panel (Expandable) */}
        <WhyThisPickPanel
          isOpen={showWhy}
          onClose={() => setShowWhy(false)}
          reasoning={decision.reasoning}
        />
      </div>
    </div>
  )
}

export default DecisionCard
