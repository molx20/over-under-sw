import { useState, useRef, useCallback } from 'react'

/**
 * GlassTooltip Component
 *
 * A modern frosted glass tooltip with smooth animations
 * Now with viewport boundary detection to prevent overflow on mobile
 */
function GlassTooltip({ children, content, position = 'top' }) {
  const [isVisible, setIsVisible] = useState(false)
  const [tooltipStyle, setTooltipStyle] = useState({})
  const triggerRef = useRef(null)

  // Callback ref to measure tooltip and calculate position
  const tooltipRef = useCallback((node) => {
    if (node && triggerRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect()
      const tooltipRect = node.getBoundingClientRect()
      const viewportWidth = window.innerWidth
      const EDGE_PADDING = 12 // pixels from edge

      // Calculate ideal centered position (relative to trigger element)
      const triggerCenterX = triggerRect.left + triggerRect.width / 2
      const tooltipWidth = tooltipRect.width
      const tooltipHalfWidth = tooltipWidth / 2

      // Calculate where the tooltip edges would be if centered
      let idealLeft = triggerCenterX - tooltipHalfWidth
      let idealRight = triggerCenterX + tooltipHalfWidth

      // Clamp to viewport bounds with padding
      const minLeft = EDGE_PADDING
      const maxRight = viewportWidth - EDGE_PADDING

      // Calculate final position by clamping
      let finalLeft = idealLeft
      if (idealLeft < minLeft) {
        finalLeft = minLeft
      } else if (idealRight > maxRight) {
        finalLeft = maxRight - tooltipWidth
      }

      // Use left positioning instead of transform for more control
      setTooltipStyle({
        position: 'fixed',
        left: `${finalLeft}px`,
        top: `${triggerRect.top - 10}px`,
        transform: 'translateY(-100%)',
        zIndex: 9999,
        pointerEvents: 'none'
      })
    }
  }, [])

  const handleMouseEnter = () => {
    setIsVisible(true)
  }

  const handleMouseLeave = () => {
    setIsVisible(false)
  }

  // Touch event handlers for mobile
  const handleTouchStart = () => {
    setIsVisible(true)
  }

  const handleTouchEnd = () => {
    // Delay hiding to allow user to see tooltip
    setTimeout(() => setIsVisible(false), 1500)
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
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {children}

      {isVisible && (
        <div
          ref={tooltipRef}
          className="glass-tooltip"
          style={tooltipStyle}
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
