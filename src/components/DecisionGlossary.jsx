/**
 * DecisionGlossary Component
 *
 * Modal explaining all DecisionCard metrics and terminology
 */

function DecisionGlossary({ isOpen, onClose }) {
  if (!isOpen) return null

  const glossaryItems = [
    {
      category: "Driver Metrics",
      items: [
        {
          term: "FT Points",
          definition: "Combined free throw points per game for both teams. Higher FT volume typically correlates with more total points.",
          target: "38+ = Green (favors Over), 33-37 = Yellow (neutral), <33 = Red (favors Under)"
        },
        {
          term: "Paint Points",
          definition: "Combined points in the paint per game for both teams. High paint scoring drives total scoring up.",
          target: "68+ = Green (favors Over), 60-67 = Yellow (neutral), <60 = Red (favors Under)"
        },
        {
          term: "eFG%",
          definition: "Effective Field Goal Percentage - accounts for 3-pointers being worth more. Formula: (FGM + 0.5 × 3PM) / FGA. Higher efficiency means more scoring.",
          target: "59%+ = Green (favors Over), 53-58% = Yellow (neutral), <53% = Red (favors Under)"
        }
      ]
    },
    {
      category: "Decision Calls",
      items: [
        {
          term: "OVER",
          definition: "Predicted total score will exceed the betting line. 2+ drivers green, favorable archetype/volatility matchup.",
          target: "Confidence based on driver alignment and archetype context"
        },
        {
          term: "UNDER",
          definition: "Predicted total score will fall below the betting line. 2+ drivers red, defensive matchup or low efficiency.",
          target: "Confidence based on driver alignment and defensive context"
        },
        {
          term: "PASS",
          definition: "Mixed signals or unclear prediction. Drivers disagree, or matchup has conflicting indicators. Avoid betting.",
          target: "Often occurs when drivers split 1-1-1 or archetype/volatility create uncertainty"
        }
      ]
    },
    {
      category: "Context Indicators",
      items: [
        {
          term: "Archetype Matchup",
          definition: "Offensive style classification based on team's scoring tendencies (e.g., 'Foul-Pressure Paint Attack', 'Perimeter Spacing Offense'). Shows how team generates points.",
          target: "Confidence indicates sample size and consistency of archetype classification"
        },
        {
          term: "Margin Risk",
          definition: "Predicted game competitiveness. 'Blowout Risk' games may see garbage time reducing total scoring. 'Competitive' games stay close, leading to more possessions.",
          target: "Competitive = more possessions = higher totals | Blowout = fewer possessions = lower totals"
        },
        {
          term: "Volatility",
          definition: "How unpredictable the game total is based on pace, defensive variance, and recent trends. Scale of 0-10.",
          target: "Wild (7-10) = high variance, less predictable | Moderate (4-6) = average variance | Stable (0-3) = predictable"
        }
      ]
    },
    {
      category: "Confidence Levels",
      items: [
        {
          term: "HIGH (70%+)",
          definition: "Strong alignment across all metrics. 3 green drivers, favorable archetype, stable volatility.",
          target: "Most reliable call - all signals pointing same direction"
        },
        {
          term: "MEDIUM (40-69%)",
          definition: "Moderate confidence. 2 drivers favoring call, some conflicting signals from archetype or volatility.",
          target: "Decent call but not all indicators aligned"
        },
        {
          term: "LOW (<40%)",
          definition: "Weak confidence. Mixed drivers (1-1-1 split), conflicting archetype, or high volatility creating uncertainty.",
          target: "Consider passing - too many conflicting signals"
        }
      ]
    }
  ]

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-gradient-to-r from-primary-600 to-primary-700 text-white p-6 rounded-t-lg">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Decision Metrics Glossary</h2>
              <button
                onClick={onClose}
                className="text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
                aria-label="Close"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-white/90 mt-2">
              Understand all metrics used in the decision engine
            </p>
          </div>

          {/* Content */}
          <div className="p-6 space-y-8">
            {glossaryItems.map((category) => (
              <div key={category.category}>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4 pb-2 border-b-2 border-primary-500">
                  {category.category}
                </h3>
                <div className="space-y-4">
                  {category.items.map((item) => (
                    <div
                      key={item.term}
                      className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4"
                    >
                      <h4 className="text-lg font-semibold text-primary-600 dark:text-primary-400 mb-2">
                        {item.term}
                      </h4>
                      <p className="text-gray-700 dark:text-gray-300 mb-3">
                        {item.definition}
                      </p>
                      <div className="bg-white dark:bg-gray-800 rounded border-l-4 border-primary-500 pl-4 py-2">
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          <span className="font-semibold text-gray-900 dark:text-white">Target/Range: </span>
                          {item.target}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-100 dark:bg-gray-900 p-4 rounded-b-lg border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              className="w-full px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-lg transition-colors"
            >
              Got it, close
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

export default DecisionGlossary
