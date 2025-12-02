import { useState } from 'react'

/**
 * GlassTooltip Component
 *
 * A modern frosted glass tooltip with smooth animations
 */
function GlassTooltip({ children, content, position = 'top' }) {
  const [isVisible, setIsVisible] = useState(false)
  const [coords, setCoords] = useState({ x: 0, y: 0 })

  const handleMouseEnter = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setCoords({
      x: rect.left + rect.width / 2,
      y: rect.top
    })
    setIsVisible(true)
  }

  const handleMouseLeave = () => {
    setIsVisible(false)
  }

  // Parse content if it's a string with newlines
  const renderContent = () => {
    if (typeof content === 'string') {
      const lines = content.split('\n').filter(line => line.trim())

      return (
        <div className="space-y-1">
          {lines.map((line, idx) => {
            // First line is title
            if (idx === 0) {
              return (
                <div key={idx} className="font-semibold" style={{ color: 'rgba(0,0,0,0.95)' }}>
                  {line}
                </div>
              )
            }
            // Last line with "Rank:" is sub-details
            else if (line.includes('Rank:')) {
              return (
                <div key={idx} style={{ color: 'rgba(0,0,0,0.70)', fontSize: '13px' }}>
                  {line}
                </div>
              )
            }
            // Middle lines are body text
            else {
              return (
                <div key={idx} style={{ color: 'rgba(0,0,0,0.85)' }}>
                  {line}
                </div>
              )
            }
          })}
        </div>
      )
    }
    return content
  }

  return (
    <div
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {isVisible && (
        <div
          className="glass-tooltip"
          style={{
            position: 'fixed',
            left: `${coords.x}px`,
            top: `${coords.y - 10}px`,
            transform: 'translate(-50%, -100%)',
            zIndex: 9999,
            pointerEvents: 'none'
          }}
        >
          <div className="glass-tooltip-content">
            {renderContent()}
          </div>
          <div className="glass-tooltip-arrow" />
        </div>
      )}
    </div>
  )
}

export default GlassTooltip
