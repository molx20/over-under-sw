/**
 * Explanation Text - 5th Grade Reading Level
 *
 * All text written at a 5th grade reading level (Flesch-Kincaid).
 * Simple, conversational language without jargon or analytics terms.
 */

export const EXPLANATION_TEXT = {
  // ========================================================================
  // PREDICTION TAB - "How We Built This Total" Card
  // ========================================================================

  startingScore: {
    title: 'Starting Score',
    description: 'We start by looking at how many points each team usually scores. We blend their season average with their last 5 games to get a smart starting number.'
  },

  gameSpeed: {
    title: 'Game Speed',
    description: 'We use real possessions to estimate how fast this game will be, but we keep that impact small. Fast games get a tiny bump, slow games get a tiny drop.',
    fast: 'This will be a fast-paced game, but we only add a small boost for that.',
    slow: 'This will be a slower game, but we only subtract a little for that.',
    normal: 'This game will move at a normal NBA speed - no adjustment needed.'
  },

  defensePressure: {
    title: 'Defense Pressure',
    description: 'Good defenses make it harder to score points. Bad defenses give up easy buckets.',
    elite: 'This defense is one of the best in the league - very hard to score against.',
    average: 'This is an average NBA defense - not too tough, not too easy.',
    weak: 'This defense struggles - easier to score against them.'
  },

  homeEdge: {
    title: 'Home Edge & Road Trouble',
    description: 'If a team scores much better at home (or struggles much worse on the road), we add a tiny bonus. Most games get zero adjustment here - we\'re being very conservative.'
  },

  shootoutMeter: {
    title: '3-Point Game Meter',
    description: 'When both teams are good at shooting 3-pointers and the defense can\'t stop them, we expect more points from downtown.',
    high: 'Expect lots of 3-pointers in this game!',
    medium: 'Some extra 3-pointers than normal.',
    low: 'Normal amount of 3-point shooting.'
  },

  restStatus: {
    title: 'Tired or Fresh?',
    description: 'Teams playing back-to-back games (yesterday and today) are usually more tired and score fewer points.',
    fresh: 'Both teams are well-rested and ready to go.',
    oneTired: 'One team played yesterday and might be a bit tired.',
    bothTired: 'Both teams played yesterday - expect slower play and fewer points.'
  },

  matchupBonuses: {
    title: 'Little Matchup Bonuses',
    description: 'If a team takes a lot of shots and grabs offensive rebounds, we give them a small scoring bump (usually +1 to +4 points). Lots of free throws usually add some extra points too, so we bump the score a bit in whistle-heavy games.'
  },

  bonuses: {
    title: 'Ball Movement Bonuses',
    description: 'When both teams show exceptional ball movement (lots of assists) and the game pace is fast, we add a small bonus to account for the extra scoring opportunities this creates.',
    details: 'These bonuses apply to the overall game scoring potential based on team playing styles. High-assist fast games create more open shots and scoring chances.'
  },

  totalChange: {
    title: 'Total Change from Starting Score',
    description: 'This is the sum of all the adjustments we made from the starting score.'
  },

  // ========================================================================
  // MATCHUP DNA TAB
  // ========================================================================

  homeRoadEdge: {
    title: 'Home Edge vs Road Trouble',
    description: 'This compares how teams perform at home versus on the road. Home teams get a boost, road teams often get penalized.'
  },

  matchupChips: {
    title: 'What Kind of Game?',
    description: 'These tags show what kind of game to expect based on how the teams play. Fast games with lots of fouls and 3-pointers usually mean more points. Slow games with strong defense and few fouls usually mean fewer points.'
  },

  // ========================================================================
  // LAST 5 GAMES TAB
  // ========================================================================

  heatCheck: {
    title: 'Offense Heat Check',
    description: 'Is this team scoring more or less than usual in their recent games? Hot offenses are on a roll. Cold offenses are struggling.',
    hot: 'On fire lately - scoring way more than normal!',
    cold: 'Struggling lately - scoring way less than normal.',
    normal: 'Scoring at their usual rate - nothing crazy.'
  },

  restInfo: {
    title: 'Rest Status',
    description: 'How much rest did this team get before this game? Teams on back-to-backs (played yesterday) are usually more tired.'
  },

  // ========================================================================
  // ADVANCED SPLITS TAB
  // ========================================================================

  scoring: {
    title: 'About Scoring Breakdown',
    description: 'This shows how each team scores their points - from 2-pointers, 3-pointers, and free throws - against different types of defenses. Teams score different amounts depending on how good the defense is.'
  },

  threePt: {
    title: 'About 3-Point Shooting',
    description: 'This shows how good each team is at shooting 3-pointers and how well their opponent defends the 3-point line. Some teams shoot way more threes when the game is fast.'
  },

  shootoutMeterAdvanced: {
    description: 'We check five things: How well each team shoots 3s, how many 3s they give up on defense, how hot they\'ve been shooting lately, how fast the game will be, and if they\'re tired from playing yesterday. If all these point to lots of threes, we add extra points!'
  },

  turnovers: {
    title: 'About Turnovers',
    description: 'Turnovers are when you lose the ball to the other team. More turnovers mean the other team gets easy fast-break points, and you score fewer points because you wasted possessions. Good defenses force more turnovers.'
  },

  assists: {
    title: 'About Assists',
    description: 'Assists show how well teams share the ball and create good shots for each other. Teams with more assists usually have better ball movement and shot creation. Good ball-movement defenses limit assists by disrupting passing lanes.'
  },

  defenseTiers: {
    title: 'About Defense Tiers',
    description: 'We group defenses into three levels: Elite (really hard to score on), Average (middle of the pack), and Weak (easier to score on). Teams score different amounts against each type. We also look at if the offense is hot or cold - hot offenses do better even against good defenses.'
  },

  ballMovementTiers: {
    title: 'About Ball-Movement Defense Tiers',
    description: 'We group ball-movement defenses into three levels based on how many assists they allow: Elite (ranks 1-10, limit assists by disrupting passing lanes), Average (ranks 11-20, middle of the pack), and Weak (ranks 21-30, allow more passing and easier shot creation). Teams usually get more assists against weaker ball-movement defenses.'
  },

  paceBuckets: {
    title: 'About Game Speed',
    description: 'Game speed matters, but we keep the impact small. Fast games mean a few more possessions and shots. Slow games mean a bit fewer. We calculate real possessions (not just estimates) but only let it change the total by a tiny amount to avoid over-predicting.'
  },

  turnoversRemoved: {
    title: 'About Turnovers in the Model',
    description: 'Turnovers are already counted in our possessions formula (more turnovers = more possessions for the other team). We don\'t add extra bonuses for turnovers anymore because that would be counting them twice.'
  }
}
