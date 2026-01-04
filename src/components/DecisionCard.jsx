/**
 * DecisionCard Component
 *
 * Main decision display card showing Over/Under/Pass recommendation
 * with 3 driver metrics, archetype matchup, margin risk, and volatility
 */

import { useState } from 'react'
import DriverCard from './DriverCard'
import WhyThisPickPanel from './WhyThisPickPanel'
import DecisionGlossary from './DecisionGlossary'

function DecisionCard({
  decision,
  drivers,
  archetype,
  marginRisk,
  volatility
}) {
  const [showWhy, setShowWhy] = useState(false)
  const [showGlossary, setShowGlossary] = useState(false)

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

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Call Badge (Large Header) */}
      <div className={`${callStyle.bg} ${callStyle.shadow} p-6 text-center relative`}>
        {/* Glossary button (top-right) */}
        <button
          onClick={() => setShowGlossary(true)}
          className="absolute top-4 right-4 text-white/80 hover:text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
          title="View metrics glossary"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>

        <h2 className={`text-3xl sm:text-4xl font-bold ${callStyle.text}`}>
          {decision.call}
        </h2>
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
                <h3 className="text-sm font-semibold text-primary-900 dark:text-primary-100">
                  Archetype Matchup
                </h3>
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

      {/* Decision Glossary Modal */}
      <DecisionGlossary
        isOpen={showGlossary}
        onClose={() => setShowGlossary(false)}
      />
    </div>
  )
}

export default DecisionCard
