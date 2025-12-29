import React from 'react'

function PointsBarChart({ games, seasonPPG, seasonAPG, selectedStat = 'pts' }) {
  if (!games || games.length === 0) {
    return null
  }

  // Reverse games array so newest is leftmost
  const reversedGames = [...games].reverse()

  // Get values based on selected stat
  const values = reversedGames.map(g => selectedStat === 'pts' ? g.team_pts : g.ast)
  const seasonAvg = selectedStat === 'pts' ? seasonPPG : seasonAPG
  const statLabel = selectedStat === 'pts' ? 'Points' : 'Assists'

  // Chart dimensions
  const width = 280
  const height = 140
  const padding = { top: 30, right: 10, bottom: 30, left: 10 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  // Calculate scale
  const maxY = Math.max(...values, seasonAvg) + 10
  const barWidth = chartWidth / values.length
  const barSpacing = barWidth * 0.15
  const actualBarWidth = barWidth - barSpacing

  // Scaling function
  const scaleY = (value) => (value / maxY) * chartHeight

  // Generate bar positions
  const bars = values.map((val, i) => {
    const x = padding.left + i * barWidth + barSpacing / 2
    const barHeight = scaleY(val)
    const y = height - padding.bottom - barHeight
    const isAboveAverage = val >= seasonAvg

    return {
      x,
      y,
      width: actualBarWidth,
      height: barHeight,
      value: val,
      color: isAboveAverage ? '#22c55e' : '#ef4444', // green-500 : red-500
      darkColor: isAboveAverage ? '#16a34a' : '#dc2626' // green-600 : red-600
    }
  })

  // Generate trend line path (connecting tops of bars)
  const linePoints = bars.map((bar, i) => ({
    x: bar.x + bar.width / 2,
    y: bar.y
  }))

  const linePath = linePoints.map((pt, i) =>
    `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`
  ).join(' ')

  // X-axis labels - use opponent team names
  const xLabels = reversedGames.map(game => game.opponent?.tricode || 'UNK')

  return (
    <div className="mt-4 w-full border-t border-gray-200 dark:border-gray-700 pt-4">
      <h4 className="text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
        {statLabel} by Game
      </h4>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="text-xs"
      >
        {/* Bars */}
        {bars.map((bar, i) => (
          <g key={i}>
            {/* Bar */}
            <rect
              x={bar.x}
              y={bar.y}
              width={bar.width}
              height={bar.height}
              className="dark:hidden"
              fill={bar.color}
              opacity="0.9"
            />
            <rect
              x={bar.x}
              y={bar.y}
              width={bar.width}
              height={bar.height}
              className="hidden dark:block"
              fill={bar.darkColor}
              opacity="0.9"
            />

            {/* Value label on bar */}
            <text
              x={bar.x + bar.width / 2}
              y={bar.y - 5}
              textAnchor="middle"
              className="text-[11px] font-semibold fill-current text-gray-900 dark:text-white"
            >
              {bar.value}
            </text>
          </g>
        ))}

        {/* Trend line (connecting tops of bars) */}
        <path
          d={linePath}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2.5"
          opacity="0.8"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Points on trend line */}
        {linePoints.map((pt, i) => (
          <circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r="3.5"
            fill="#3b82f6"
            opacity="0.9"
          />
        ))}

        {/* X-axis labels */}
        {bars.map((bar, i) => (
          <text
            key={i}
            x={bar.x + bar.width / 2}
            y={height - padding.bottom + 20}
            textAnchor="middle"
            className="text-[10px] fill-current text-gray-600 dark:text-gray-400"
          >
            {xLabels[i]}
          </text>
        ))}

        {/* Season average reference line */}
        <line
          x1={padding.left}
          y1={height - padding.bottom - scaleY(seasonAvg)}
          x2={width - padding.right}
          y2={height - padding.bottom - scaleY(seasonAvg)}
          stroke="#f59e0b"
          strokeWidth="2"
          opacity="0.6"
          strokeDasharray="4 3"
        />
        <text
          x={width - padding.right - 35}
          y={height - padding.bottom - scaleY(seasonAvg) - 3}
          textAnchor="start"
          className="text-[9px] font-semibold fill-current text-orange-500 dark:text-orange-400"
        >
          Avg {seasonAvg > 0 ? seasonAvg.toFixed(1) : '—'}
        </text>
      </svg>

      {/* Legend */}
      <div className="flex justify-center gap-3 mt-2 text-[10px] text-gray-600 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <div className="w-3 h-2 bg-green-500 dark:bg-green-600"></div>
          <span>Above Avg</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-2 bg-red-500 dark:bg-red-600"></div>
          <span>Below Avg</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-blue-500"></div>
          <span>Trend</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-orange-500 opacity-60" style={{ backgroundImage: 'repeating-linear-gradient(to right, #f59e0b 0, #f59e0b 3px, transparent 3px, transparent 6px)' }}></div>
          <span>Season Avg</span>
        </div>
      </div>
    </div>
  )
}

export default PointsBarChart
