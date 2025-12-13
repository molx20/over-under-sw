/**
 * MatchupIndicators Component
 *
 * Displays 4-5 key matchup indicator tiles with numbers and explanations
 * - Pace Edge
 * - 3PT Advantage
 * - Paint & Rim Pressure
 * - Ball Movement & Turnovers
 * - Free Throw Leverage
 */
function MatchupIndicators({ homeTeam, awayTeam, homeStats, awayStats }) {
  // Calculate projected combined pace
  const getProjectedPace = () => {
    const homePace = parseFloat(homeStats?.pace) || 0
    const awayPace = parseFloat(awayStats?.pace) || 0
    return ((homePace + awayPace) / 2).toFixed(1)
  }

  const getPaceTag = (pace) => {
    if (pace < 97) return 'Slow'
    if (pace < 99) return 'Neutral'
    if (pace < 101) return 'Slightly Fast'
    return 'Fast'
  }

  // Calculate 3PT advantage
  const get3PTAdvantage = () => {
    const home3PA = parseFloat(homeStats?.fg3a_per_game) || 0
    const away3PA = parseFloat(awayStats?.fg3a_per_game) || 0
    const home3PPct = parseFloat(homeStats?.fg3_pct) || 0
    const away3PPct = parseFloat(awayStats?.fg3_pct) || 0

    const attemptDiff = home3PA - away3PA
    const accDiff = home3PPct - away3PPct

    const leader = attemptDiff > 0 ? homeTeam?.abbreviation : awayTeam?.abbreviation
    return {
      leader,
      attemptDiff: Math.abs(attemptDiff).toFixed(1),
      accDiff: Math.abs(accDiff).toFixed(1),
      homeFavored: attemptDiff > 0
    }
  }

  // Calculate paint pressure
  const getPaintAdvantage = () => {
    const homePaint = parseFloat(homeStats?.paint_pts_per_game) || 0
    const awayPaint = parseFloat(awayStats?.paint_pts_per_game) || 0
    const homeOppPaint = parseFloat(homeStats?.opp_paint_pts_per_game) || 0
    const awayOppPaint = parseFloat(awayStats?.opp_paint_pts_per_game) || 0

    const homeDiff = homePaint - awayOppPaint
    const awayDiff = awayPaint - homeOppPaint

    return {
      homePaint: homePaint.toFixed(1),
      awayPaint: awayPaint.toFixed(1),
      homeOppPaint: homeOppPaint.toFixed(1),
      awayOppPaint: awayOppPaint.toFixed(1),
      homeEdge: homeDiff > awayDiff,
      edgeDiff: Math.abs(homeDiff - awayDiff).toFixed(1)
    }
  }

  // Calculate ball movement and turnovers
  const getBallMovement = () => {
    const homeAst = parseFloat(homeStats?.ast_pct) || 0
    const awayAst = parseFloat(awayStats?.ast_pct) || 0
    const homeTo = parseFloat(homeStats?.tov_pct) || 0
    const awayTo = parseFloat(awayStats?.tov_pct) || 0

    return {
      homeAst: homeAst.toFixed(1),
      awayAst: awayAst.toFixed(1),
      homeTo: homeTo.toFixed(1),
      awayTo: awayTo.toFixed(1),
      betterBallMovement: homeAst > awayAst ? homeTeam?.abbreviation : awayTeam?.abbreviation,
      betterProtection: homeTo < awayTo ? homeTeam?.abbreviation : awayTeam?.abbreviation
    }
  }

  // Calculate FT leverage
  const getFTLeverage = () => {
    const homeFTA = parseFloat(homeStats?.fta_per_game) || 0
    const awayFTA = parseFloat(awayStats?.fta_per_game) || 0
    const homeFTPct = parseFloat(homeStats?.ft_pct) || 0
    const awayFTPct = parseFloat(awayStats?.ft_pct) || 0

    return {
      homeFTA: homeFTA.toFixed(1),
      awayFTA: awayFTA.toFixed(1),
      homeFTPct: homeFTPct.toFixed(1),
      awayFTPct: awayFTPct.toFixed(1),
      moreAttempts: homeFTA > awayFTA ? homeTeam?.abbreviation : awayTeam?.abbreviation,
      betterShooter: homeFTPct > awayFTPct ? homeTeam?.abbreviation : awayTeam?.abbreviation
    }
  }

  const projectedPace = getProjectedPace()
  const paceTag = getPaceTag(projectedPace)
  const threePoint = get3PTAdvantage()
  const paint = getPaintAdvantage()
  const ballMovement = getBallMovement()
  const ftData = getFTLeverage()

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
        Matchup Indicators
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Pace Edge */}
        <IndicatorTile
          title="Pace Edge"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          }
        >
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-gray-500 dark:text-gray-400">{awayTeam?.abbreviation}</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">{awayStats?.pace || '-'}</div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{homeTeam?.abbreviation}</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">{homeStats?.pace || '-'}</div>
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-500 dark:text-gray-400">Projected</div>
              <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">{projectedPace}</div>
            </div>
            <div className="text-xs text-gray-700 dark:text-gray-300 text-center">
              <span className="inline-block px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded font-semibold">
                {paceTag}
              </span>
            </div>
          </div>
        </IndicatorTile>

        {/* 3PT Advantage */}
        <IndicatorTile
          title="3PT Advantage"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
            </svg>
          }
        >
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-gray-500 dark:text-gray-400">{awayTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {awayStats?.fg3a_per_game || '-'} 3PA
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {awayStats?.fg3_pct || '-'}%
                </div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{homeTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {homeStats?.fg3a_per_game || '-'} 3PA
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {homeStats?.fg3_pct || '-'}%
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-700 dark:text-gray-300 leading-tight">
              {threePoint.leader} +{threePoint.attemptDiff} 3PA and {threePoint.homeFavored ? '+' : '-'}{threePoint.accDiff}% accuracy
            </p>
          </div>
        </IndicatorTile>

        {/* Paint & Rim Pressure */}
        <IndicatorTile
          title="Paint Pressure"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          }
        >
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-gray-500 dark:text-gray-400">{awayTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {paint.awayPaint} pts
                </div>
                <div className="text-xs text-gray-500">vs {paint.homeOppPaint} allowed</div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{homeTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {paint.homePaint} pts
                </div>
                <div className="text-xs text-gray-500">vs {paint.awayOppPaint} allowed</div>
              </div>
            </div>
            <p className="text-xs text-gray-700 dark:text-gray-300 leading-tight">
              {paint.homeEdge ? homeTeam?.abbreviation : awayTeam?.abbreviation} has {paint.edgeDiff} pt edge in paint matchup
            </p>
          </div>
        </IndicatorTile>

        {/* Ball Movement & Turnovers */}
        <IndicatorTile
          title="Ball Movement"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          }
        >
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-gray-500 dark:text-gray-400">{awayTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ballMovement.awayAst}% AST
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ballMovement.awayTo}% TO
                </div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{homeTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ballMovement.homeAst}% AST
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ballMovement.homeTo}% TO
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-700 dark:text-gray-300 leading-tight">
              {ballMovement.betterBallMovement} moves ball better, {ballMovement.betterProtection} protects it more
            </p>
          </div>
        </IndicatorTile>

        {/* Free Throw Leverage */}
        <IndicatorTile
          title="FT Leverage"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        >
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-gray-500 dark:text-gray-400">{awayTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ftData.awayFTA} FTA
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ftData.awayFTPct}%
                </div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{homeTeam?.abbreviation}</div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ftData.homeFTA} FTA
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-white">
                  {ftData.homeFTPct}%
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-700 dark:text-gray-300 leading-tight">
              {ftData.moreAttempts} gets to line more, {ftData.betterShooter} shoots better there
            </p>
          </div>
        </IndicatorTile>
      </div>
    </div>
  )
}

function IndicatorTile({ title, icon, children }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center space-x-2 mb-3">
        <div className="text-primary-600 dark:text-primary-400">
          {icon}
        </div>
        <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
          {title}
        </h4>
      </div>
      {children}
    </div>
  )
}

export default MatchupIndicators
