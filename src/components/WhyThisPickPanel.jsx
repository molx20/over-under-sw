/**
 * WhyThisPickPanel Component
 *
 * Expandable panel showing reasoning bullets for the decision
 * Displays positive, warning, and neutral signals
 */

function WhyThisPickPanel({ isOpen, onClose, reasoning }) {
  if (!isOpen) return null

  // Icon mapping by type
  const typeStyles = {
    positive: {
      icon: '✓',
      textColor: 'text-green-700 dark:text-green-300',
      bgColor: 'bg-green-50 dark:bg-green-900/20'
    },
    warning: {
      icon: '⚠',
      textColor: 'text-yellow-700 dark:text-yellow-300',
      bgColor: 'bg-yellow-50 dark:bg-yellow-900/20'
    },
    neutral: {
      icon: '⚖',
      textColor: 'text-gray-700 dark:text-gray-300',
      bgColor: 'bg-gray-50 dark:bg-gray-900/20'
    }
  }

  return (
    <div
      className="
        mt-4 rounded-lg border border-blue-200 dark:border-blue-800
        bg-blue-50 dark:bg-blue-900/20
        p-4
        animate-fadeIn
      "
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100">
          Why This Pick?
        </h3>
        <button
          onClick={onClose}
          className="
            text-blue-600 dark:text-blue-400
            hover:text-blue-800 dark:hover:text-blue-200
            transition-colors
          "
          aria-label="Close reasoning panel"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Reasoning bullets */}
      <div className="space-y-2">
        {reasoning && reasoning.length > 0 ? (
          reasoning.map((item, index) => {
            const style = typeStyles[item.type] || typeStyles.neutral

            return (
              <div
                key={index}
                className={`
                  flex items-start gap-3 p-2 rounded
                  ${style.bgColor}
                `}
              >
                {/* Icon */}
                <span className="text-xl flex-shrink-0 mt-0.5">{item.icon}</span>

                {/* Text */}
                <p className={`text-sm ${style.textColor} flex-1`}>
                  {item.text}
                </p>
              </div>
            )
          })
        ) : (
          <p className="text-sm text-gray-600 dark:text-gray-400 italic">
            No detailed reasoning available
          </p>
        )}
      </div>
    </div>
  )
}

export default WhyThisPickPanel
