/**
 * DriverCard Component
 *
 * Displays a single driver metric (FT Points, Paint Points, or eFG%)
 * with color-coded status indicator
 */

function DriverCard({ label, value, target, status, subtitle }) {
  // Color classes based on status
  const statusColors = {
    green: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-300',
      border: 'border-green-300 dark:border-green-700',
      indicator: 'bg-green-500'
    },
    yellow: {
      bg: 'bg-yellow-100 dark:bg-yellow-900/30',
      text: 'text-yellow-700 dark:text-yellow-300',
      border: 'border-yellow-300 dark:border-yellow-700',
      indicator: 'bg-yellow-500'
    },
    red: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-700 dark:text-red-300',
      border: 'border-red-300 dark:border-red-700',
      indicator: 'bg-red-500'
    }
  }

  const colors = statusColors[status] || statusColors.yellow

  // Status icons
  const statusIcons = {
    green: '🟢',
    yellow: '🟡',
    red: '🔴'
  }

  return (
    <div
      className={`
        relative rounded-lg border-2 p-4
        ${colors.bg} ${colors.border}
        transition-all duration-200 hover:shadow-md
      `}
    >
      {/* Status indicator dot (top-right) */}
      <div className={`absolute top-3 right-3 w-3 h-3 rounded-full ${colors.indicator}`} />

      {/* Label */}
      <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
        {label}
      </div>

      {/* Value (large display) */}
      <div className={`text-3xl font-bold mb-2 ${colors.text}`}>
        {value}
        {subtitle && (
          <span className="text-lg ml-1 opacity-75">{subtitle}</span>
        )}
      </div>

      {/* Target threshold */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 dark:text-gray-400">Target:</span>
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {target}
        </span>
        <span className="text-lg">{statusIcons[status]}</span>
      </div>
    </div>
  )
}

export default DriverCard
