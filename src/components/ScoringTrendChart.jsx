import React from 'react'

function ScoringTrendChart({ games, seasonPPG }) {
  if (!games || games.length === 0) {
    return null
  }

  // Reverse games array so newest is leftmost (backend sends oldest→newest)
  const reversedGames = [...games].reverse()
  const points = reversedGames.map(g => g.team_pts)

  // Calculate linear regression for trend line
  const calculateTrendLine = (values) => {
    const n = values.length
    const xValues = Array.from({ length: n }, (_, i) => i)
    const xSum = xValues.reduce((a, b) => a + b, 0)
    const ySum = values.reduce((a, b) => a + b, 0)
    const xxSum = xValues.reduce((sum, x) => sum + x * x, 0)
    const xySum = xValues.reduce((sum, x, i) => sum + x * values[i], 0)

    const slope = (n * xySum - xSum * ySum) / (n * xxSum - xSum * xSum)
    const intercept = (ySum - slope * xSum) / n

    return xValues.map(x => slope * x + intercept)
  }

  const trendLine = calculateTrendLine(points)

  // Chart dimensions
  const width = 280
  const height = 120
  const padding = { top: 10, right: 10, bottom: 25, left: 35 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  // Calculate Y-axis scale (auto-scaled, not zero-based)
  const allValues = [...points, seasonPPG]
  const minY = Math.floor(Math.min(...allValues) - 5)
  const maxY = Math.ceil(Math.max(...allValues) + 5)
  const yRange = maxY - minY

  // Scaling functions
  const scaleX = (index) => padding.left + (index / (points.length - 1)) * chartWidth
  const scaleY = (value) => padding.top + chartHeight - ((value - minY) / yRange) * chartHeight

  // Generate path strings
  const pointsPath = points.map((pt, i) =>
    `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(pt)}`
  ).join(' ')

  const trendPath = trendLine.map((pt, i) =>
    `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(pt)}`
  ).join(' ')

  // X-axis labels
  const xLabels = ['Last', 'G-1', 'G-2', 'G-3', 'G-4']

  // Y-axis ticks (3 ticks)
  const yTicks = [
    minY,
    Math.round((minY + maxY) / 2),
    maxY
  ]

  return (
    <div className="mt-3 w-full">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="text-xs"
      >
        {/* Grid lines */}
        {yTicks.map((tick) => (
          <line
            key={tick}
            x1={padding.left}
            y1={scaleY(tick)}
            x2={width - padding.right}
            y2={scaleY(tick)}
            stroke="currentColor"
            strokeWidth="0.5"
            opacity="0.1"
          />
        ))}

        {/* Season average line (horizontal baseline) */}
        <line
          x1={padding.left}
          y1={scaleY(seasonPPG)}
          x2={width - padding.right}
          y2={scaleY(seasonPPG)}
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.3"
          strokeDasharray="4 2"
        />

        {/* Trend line (linear regression, dashed) */}
        <path
          d={trendPath}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.4"
          strokeDasharray="3 3"
        />

        {/* Points scored line (solid, primary) */}
        <path
          d={pointsPath}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          opacity="0.8"
          className="text-blue-600 dark:text-blue-400"
        />

        {/* Data point markers */}
        {points.map((pt, i) => (
          <circle
            key={i}
            cx={scaleX(i)}
            cy={scaleY(pt)}
            r="3"
            fill="currentColor"
            className="text-blue-600 dark:text-blue-400"
          />
        ))}

        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={height - padding.bottom}
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.2"
        />

        {/* Y-axis labels */}
        {yTicks.map((tick) => (
          <text
            key={tick}
            x={padding.left - 5}
            y={scaleY(tick)}
            textAnchor="end"
            alignmentBaseline="middle"
            className="text-[10px] fill-current text-gray-600 dark:text-gray-400"
          >
            {tick}
          </text>
        ))}

        {/* X-axis */}
        <line
          x1={padding.left}
          y1={height - padding.bottom}
          x2={width - padding.right}
          y2={height - padding.bottom}
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.2"
        />

        {/* X-axis labels */}
        {xLabels.slice(0, points.length).map((label, i) => (
          <text
            key={i}
            x={scaleX(i)}
            y={height - padding.bottom + 15}
            textAnchor="middle"
            className="text-[10px] fill-current text-gray-600 dark:text-gray-400"
          >
            {label}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex justify-center gap-4 mt-2 text-[10px] text-gray-600 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-blue-600 dark:bg-blue-400"></div>
          <span>Points</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-gray-400 opacity-40" style={{ backgroundImage: 'repeating-linear-gradient(to right, currentColor 0, currentColor 2px, transparent 2px, transparent 5px)' }}></div>
          <span>Trend</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-gray-400 opacity-30" style={{ backgroundImage: 'repeating-linear-gradient(to right, currentColor 0, currentColor 3px, transparent 3px, transparent 6px)' }}></div>
          <span>Season Avg</span>
        </div>
      </div>
    </div>
  )
}

export default ScoringTrendChart
