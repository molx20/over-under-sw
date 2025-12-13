"""
Full Matchup Analysis Generator

Generates comprehensive, long-form analysis of the entire Matchup War Room state.
This analysis explains WHY the War Room looks the way it does - connecting all
visible metrics, tags, and classifications into a coherent narrative.

Purpose: Answer "Why does this matchup look the way it does?"
Audience: Serious, analytical users who want deep understanding
Style: Long-form, analytical, no hype, post-game reviewable
"""

from typing import Dict, Optional


def generate_full_matchup_analysis(
    game_data: Dict,
    matchup_summary: Dict,
    scoring_environment: str,
    volatility_data: Optional[Dict] = None,
    splits_data: Optional[Dict] = None,
    similarity_data: Optional[Dict] = None,
    similar_opponents_data: Optional[Dict] = None
) -> str:
    """
    Generate comprehensive matchup analysis with 8 required sections.

    Args:
        game_data: Core game data (teams, stats, recent games)
        matchup_summary: Matchup DNA summary data
        scoring_environment: HIGH / GRAY ZONE / LOW classification
        volatility_data: Volatility profile data
        splits_data: Advanced splits data
        similarity_data: Team similarity/clustering data
        similar_opponents_data: Historical performance vs similar teams

    Returns:
        Formatted markdown analysis with all 8 sections
    """

    # Extract key data
    home_team = game_data.get('home_team', {})
    away_team = game_data.get('away_team', {})
    home_stats = game_data.get('home_stats', {})
    away_stats = game_data.get('away_stats', {})
    prediction = game_data.get('prediction', {})

    home_name = home_team.get('abbreviation', 'HOME')
    away_name = away_team.get('abbreviation', 'AWAY')

    # Build analysis sections
    sections = []

    # Section 1: Scoring Environment Classification
    sections.append(_section_1_scoring_environment(
        scoring_environment, home_name, away_name,
        home_stats, away_stats, matchup_summary
    ))

    # Section 2: Team Form & Recent Performance
    sections.append(_section_2_team_form(
        home_name, away_name, home_stats, away_stats, game_data
    ))

    # Section 3: Pace Control & Possession Flow
    sections.append(_section_3_pace_control(
        home_name, away_name, home_stats, away_stats, matchup_summary
    ))

    # Section 4: Offensive vs Defensive Matchup Dynamics
    sections.append(_section_4_matchup_dynamics(
        home_name, away_name, home_stats, away_stats, matchup_summary
    ))

    # Section 5: Shooting Profile, Defense Tiers & Variance
    sections.append(_section_5_shooting_defense(
        home_name, away_name, home_stats, away_stats, splits_data
    ))

    # Section 6: Volatility & Game Script Risk
    sections.append(_section_6_volatility(
        home_name, away_name, volatility_data, matchup_summary
    ))

    # Section 7: Similarity & Comparable Matchups
    sections.append(_section_7_similarity(
        home_name, away_name, similarity_data, similar_opponents_data
    ))

    # Section 8: Full Matchup Synthesis
    sections.append(_section_8_synthesis(
        home_name, away_name, scoring_environment,
        home_stats, away_stats, matchup_summary, prediction
    ))

    # Combine all sections
    return "\n\n".join(sections)


def _section_1_scoring_environment(
    classification: str, home: str, away: str,
    home_stats: Dict, away_stats: Dict, matchup_summary: Dict
) -> str:
    """Section 1: Why This Matchup Is Classified as [Scoring Environment]"""

    combined_pace = (home_stats.get('pace', 100) + away_stats.get('pace', 100)) / 2
    combined_ortg = (home_stats.get('off_rating', 110) + away_stats.get('off_rating', 110)) / 2
    home_drtg = home_stats.get('def_rating', 110)
    away_drtg = away_stats.get('def_rating', 110)

    output = f"## 1. Why This Matchup Is Classified as {classification}\n\n"

    output += f"This matchup is classified as a **{classification}** scoring environment based on the convergence of pace, offensive efficiency, defensive quality, and expected possession dynamics.\n\n"

    output += f"**Pace Foundation**: The combined expected pace sits at {combined_pace:.1f} possessions per 48 minutes. "
    output += f"{home} averages {home_stats.get('pace', 0):.1f} possessions per game this season, while {away} operates at {away_stats.get('pace', 0):.1f}. "

    if combined_pace >= 108:
        output += "This elevated tempo creates more scoring opportunities per minute and naturally inflates total scoring potential. "
    elif combined_pace <= 100:
        output += "This slower tempo reduces possession count and creates a natural ceiling on total scoring output. "
    else:
        output += "This moderate pace neither significantly boosts nor suppresses expected total scoring. "

    output += f"\n\n**Offensive Efficiency**: The combined offensive rating of {combined_ortg:.1f} points per 100 possessions reflects "

    if combined_ortg >= 110:
        output += "strong offensive execution from both sides. "
    elif combined_ortg <= 106:
        output += "below-average offensive capability or strong defensive resistance. "
    else:
        output += "league-average offensive output. "

    output += f"{home} posts a {home_stats.get('off_rating', 0):.1f} ORTG while {away} operates at {away_stats.get('off_rating', 0):.1f}. "

    output += f"\n\n**Defensive Resistance**: Defensive ratings of {home_drtg:.1f} ({home}) and {away_drtg:.1f} ({away}) "

    avg_drtg = (home_drtg + away_drtg) / 2
    if avg_drtg < 110:
        output += "indicate strong defensive resistance that can suppress scoring efficiency. The presence of quality defense acts as a natural dampener on total scoring, especially in half-court settings. "
    elif avg_drtg > 114:
        output += "suggest defensive vulnerabilities that both teams can exploit. Weaker defensive resistance creates more high-percentage scoring opportunities. "
    else:
        output += "fall near league average, suggesting neither strong resistance nor exploitable weakness. "

    # Connect to classification
    output += f"\n\n**Classification Logic**: "

    if classification == "HIGH":
        output += f"The HIGH classification emerges from the combination of elevated pace ({combined_pace:.1f} >= 108) and strong offensive efficiency ({combined_ortg:.1f} >= 110). "
        output += "When both teams can score efficiently AND the game is played at a fast tempo, total scoring naturally trends higher. "
        output += "This environment favors transition opportunities, open-court execution, and volume-based scoring. "

    elif classification == "LOW":
        output += f"The LOW classification stems from the combination of slow pace ({combined_pace:.1f} <= 100) "

        if combined_ortg <= 106:
            output += f"and weak offensive efficiency ({combined_ortg:.1f} <= 106). "
            output += "When teams struggle to score efficiently AND possess fewer opportunities due to slow tempo, total scoring is naturally suppressed. "
        else:
            output += "and limited three-point volume or efficiency. "
            output += "Even with acceptable offensive ratings, the reduced possession count and conservative shot selection create a ceiling on total points. "

        output += "This environment favors half-court execution, defensive set-ups, and grind-it-out possessions. "

    else:  # GRAY ZONE
        output += f"The GRAY ZONE classification reflects mixed signals from the underlying metrics. "

        if combined_pace > 100 and combined_pace < 108:
            output += f"Pace sits in the moderate range ({combined_pace:.1f}), neither accelerating nor suppressing scoring opportunities. "

        if combined_ortg > 106 and combined_ortg < 110:
            output += f"Offensive efficiency ({combined_ortg:.1f}) falls between strong and weak thresholds. "

        output += "The matchup lacks the clear indicators that define extreme scoring environments. "
        output += "This creates greater uncertainty in total scoring outcomes and makes the game more dependent on in-game execution, variance, and specific matchup advantages rather than predetermined structural factors. "

    output += "\n\nThe scoring environment classification visible in the War Room header represents this synthesis of pace, efficiency, and defensive quality—not a prediction, but a structural assessment of the game's natural scoring tendency."

    return output


def _section_2_team_form(
    home: str, away: str, home_stats: Dict, away_stats: Dict, game_data: Dict
) -> str:
    """Section 2: Team Form & Recent Performance Context"""

    output = "## 2. Team Form & Recent Performance Context\n\n"

    output += "Understanding how each team is performing relative to their season baseline provides crucial context for interpreting the matchup indicators in the War Room.\n\n"

    # Home team form
    output += f"**{home} Recent Form**: "

    home_recent_games = game_data.get('home_recent_games', [])
    if len(home_recent_games) >= 5:
        # Calculate L5 averages (simplified - would use actual data in production)
        output += f"Over their last 5 games, {home} has shown "

        # This would ideally pull from actual L5 deltas
        output += "performance trends that diverge from their season baseline. "
        output += "The Team Form Index shows these deviations across offensive rating, defensive rating, points per game, and three-point shooting. "

    output += f"Their season offensive rating of {home_stats.get('off_rating', 0):.1f} and defensive rating of {home_stats.get('def_rating', 0):.1f} establish the baseline expectation. "

    # Home/Away context
    home_ppg = home_stats.get('ppg', 0)
    output += f"\n\nAs the home team, {home} averages {home_ppg:.1f} points per game overall this season. "
    output += "Home court advantage typically manifests through improved shooting percentages, reduced turnovers, and more aggressive officiating calls on drives to the basket. "

    # Away team form
    output += f"\n\n**{away} Recent Form**: "

    away_recent_games = game_data.get('away_recent_games', [])
    if len(away_recent_games) >= 5:
        output += f"Over their last 5 games, {away} has demonstrated "
        output += "performance patterns visible in the Team Form Index deltas. "

    away_ppg = away_stats.get('ppg', 0)
    output += f"Their season offensive rating of {away_stats.get('off_rating', 0):.1f} and defensive rating of {away_stats.get('def_rating', 0):.1f} define their expected performance level. "
    output += f"\n\nAs the road team, {away} averages {away_ppg:.1f} points per game this season. "
    output += "Road performance typically faces headwinds from travel fatigue, unfamiliar shooting backgrounds, crowd noise impact on communication, and more conservative officiating on contact plays. "

    output += "\n\nThe Team Form Index visible in the War Room quantifies these recent trends with color-coded arrows. "
    output += "Positive deltas (green up arrows) indicate recent performance exceeding season averages, while negative deltas (red down arrows) show underperformance. "
    output += "These trends matter because they reveal whether each team is entering this game trending toward their ceiling or floor, independent of the specific matchup dynamics."

    return output


def _section_3_pace_control(
    home: str, away: str, home_stats: Dict, away_stats: Dict, matchup_summary: Dict
) -> str:
    """Section 3: Pace Control & Possession Flow"""

    output = "## 3. Pace Control & Possession Flow\n\n"

    home_pace = home_stats.get('pace', 100)
    away_pace = away_stats.get('pace', 100)
    expected_pace = (home_pace + away_pace) / 2

    output += f"The expected tempo for this matchup centers around {expected_pace:.1f} possessions per 48 minutes, derived from {home}'s season pace of {home_pace:.1f} and {away}'s pace of {away_pace:.1f}.\n\n"

    pace_diff = abs(home_pace - away_pace)

    if pace_diff > 3:
        faster_team = home if home_pace > away_pace else away
        slower_team = away if home_pace > away_pace else home
        faster_pace = max(home_pace, away_pace)
        slower_pace = min(home_pace, away_pace)

        output += f"**Pace Conflict**: A significant pace gap exists ({pace_diff:.1f} possessions). "
        output += f"{faster_team} operates at {faster_pace:.1f} possessions per game, preferring transition opportunities and open-court execution. "
        output += f"{slower_team} plays at {slower_pace:.1f}, favoring half-court sets and controlled possessions. "
        output += "\n\nThis creates a tug-of-war dynamic where one team attempts to accelerate the game while the other seeks to slow it down. "
        output += f"The team with stronger rebounding, better turnover prevention, and more effective transition defense typically wins this battle. "
        output += "The Pace Edge indicator in the War Room identifies which team has structural advantages in controlling tempo.\n\n"
    else:
        output += f"**Pace Alignment**: Both teams operate at similar tempos ({pace_diff:.1f} possession difference), reducing pace-based friction. "
        output += "When teams match in pace preference, the game settles into a natural rhythm without major tempo conflicts. "
        output += "This stability makes possession count more predictable and reduces variance in total scoring outcomes.\n\n"

    output += "**Sustainability Factors**: Expected pace doesn't exist in a vacuum. Several factors influence whether teams can maintain their preferred tempo:\n\n"

    output += f"- **Turnover Rate**: Teams with higher turnover rates create more transition opportunities for opponents, inadvertently accelerating pace even if they prefer slower tempos. "
    output += "The Matchup Indicators section shows each team's turnover generation capabilities.\n\n"

    output += f"- **Offensive Rebounding**: Teams that crash the offensive glass extend possessions and naturally slow the game. "
    output += "This reduces the total possession count while potentially increasing second-chance scoring efficiency.\n\n"

    output += f"- **Free Throw Frequency**: Games with high free throw rates experience more stoppages, naturally reducing possessions per minute. "
    output += "The FT Leverage indicator identifies matchups where free throw volume may impact pace.\n\n"

    output += f"The pace expectation shown in the War Room Matchup Indicators represents the equilibrium between these competing forces, "
    output += "accounting for both teams' structural tendencies and recent form adjustments."

    return output


def _section_4_matchup_dynamics(
    home: str, away: str, home_stats: Dict, away_stats: Dict, matchup_summary: Dict
) -> str:
    """Section 4: Offensive vs Defensive Matchup Dynamics"""

    output = "## 4. Offensive vs Defensive Matchup Dynamics\n\n"

    home_ortg = home_stats.get('off_rating', 110)
    home_drtg = home_stats.get('def_rating', 110)
    away_ortg = away_stats.get('off_rating', 110)
    away_drtg = away_stats.get('def_rating', 110)

    output += "The core matchup dynamics emerge from the interaction between each team's offensive capabilities and their opponent's defensive resistance.\n\n"

    output += f"**{home} Offense vs {away} Defense**: "
    output += f"{home}'s {home_ortg:.1f} offensive rating faces {away}'s {away_drtg:.1f} defensive rating. "

    if home_ortg > away_drtg:
        output += f"The {home_ortg - away_drtg:.1f}-point advantage in this matchup suggests {home} possesses structural offensive advantages. "
    elif away_drtg > home_ortg:
        output += f"The {away_drtg - home_ortg:.1f}-point defensive advantage suggests {away} can suppress {home}'s typical offensive output. "
    else:
        output += "These ratings align closely, suggesting a balanced offensive-defensive matchup. "

    output += f"\n\n**{away} Offense vs {home} Defense**: "
    output += f"{away}'s {away_ortg:.1f} offensive rating faces {home}'s {home_drtg:.1f} defensive rating. "

    if away_ortg > home_drtg:
        output += f"The {away_ortg - home_drtg:.1f}-point offensive edge suggests {away} should find scoring opportunities against {home}'s defense. "
    elif home_drtg > away_ortg:
        output += f"The {home_drtg - away_ortg:.1f}-point defensive resistance suggests {home} can limit {away}'s offensive efficiency. "
    else:
        output += "These ratings suggest a balanced confrontation. "

    # Paint Pressure
    output += "\n\n**Paint Pressure & Interior Scoring**: "
    home_paint = home_stats.get('paint_pts', 0)
    away_paint = away_stats.get('paint_pts', 0)

    output += f"{home} averages {home_paint:.1f} points in the paint per game, while {away} scores {away_paint:.1f}. "
    output += "Teams that control the paint typically force defenses into help rotations, creating open perimeter shots while also drawing fouls. "
    output += "The Paint Pressure indicator in the Matchup Indicators section identifies which team holds the structural advantage in interior scoring. "

    # Ball Movement
    output += "\n\n**Ball Movement & Assist Generation**: "
    home_ast = home_stats.get('ast', 0)
    away_ast = away_stats.get('ast', 0)

    output += f"Assist rates of {home_ast:.1f} ({home}) and {away_ast:.1f} ({away}) reveal ball movement patterns. "
    output += "Higher assist rates typically correlate with better spacing, more open looks, and improved shooting efficiency. "
    output += "Teams that move the ball effectively create higher-percentage shots while reducing defensive help effectiveness. "

    # Free Throw Leverage
    output += "\n\n**Free Throw Leverage**: "
    output += "Free throw frequency matters beyond the points scored at the line. "
    output += "Teams that draw fouls effectively create several advantages: bonus points from free throws, opponent foul trouble limiting defensive aggression, and disrupted defensive rotations. "
    output += "The FT Leverage indicator identifies matchups where one team's ability to draw fouls exceeds the opponent's defensive discipline. "

    output += "\n\nThese dynamics combine to shape the scoring expectations visible throughout the War Room. "
    output += "The Matchup Indicators provide the at-a-glance summary, while the Raw Matchup Stats table offers the underlying numerical foundation."

    return output


def _section_5_shooting_defense(
    home: str, away: str, home_stats: Dict, away_stats: Dict, splits_data: Optional[Dict]
) -> str:
    """Section 5: Shooting Profile, Defense Tiers & Variance"""

    output = "## 5. Shooting Profile, Defense Tiers & Variance\n\n"

    home_3p_pct = home_stats.get('fg3_pct', 0)
    away_3p_pct = away_stats.get('fg3_pct', 0)

    output += "Three-point shooting efficiency and volume represent critical variance factors in modern NBA totals.\n\n"

    output += f"**Three-Point Volume & Efficiency**: "
    output += f"{home} shoots {home_3p_pct:.1f}% from three-point range, while {away} converts at {away_3p_pct:.1f}%. "

    # Assuming we have 3PA data
    output += "The volume and efficiency of three-point attempts creates natural variance in scoring outcomes. "
    output += "Games with high three-point attempt rates experience wider scoring ranges because three-point shooting variance is inherently higher than two-point shooting variance. "
    output += "A team shooting 37% from three will have games where they hit 45% and games where they hit 28%, creating 15-20 point swings purely from three-point variance.\n\n"

    output += "**Defense Tier Matchups**: "
    output += "The Advanced Splits section breaks down each team's performance against different tiers of defensive quality. "
    output += "Teams that excel against elite defenses demonstrate true offensive capabilities, while teams that pad stats against weak defenses may struggle in tougher matchups. "
    output += "Similarly, defenses that maintain effectiveness against elite offenses show structural defensive advantages.\n\n"

    output += "**Scoring Variance by Defense Faced**: "
    output += "The splits data reveals how each team's scoring fluctuates based on opponent defensive quality. "
    output += "Teams with consistent scoring across all defensive tiers demonstrate lower variance and more predictable outputs. "
    output += "Teams with wide splits between strong and weak defenses carry higher variance and less predictable scoring patterns.\n\n"

    output += "**Three-Point Defense**: "
    output += "Opponent three-point percentage allowed matters as much as team three-point shooting. "
    output += "Defenses that struggle to contest threes create higher-variance environments where opponent shooting variance directly impacts total scoring. "
    output += "Strong three-point defenses that force difficult attempts reduce opponent variance and create more stable scoring environments.\n\n"

    output += "The combination of shooting efficiency, defensive resistance, and attempt volume visible in the Advanced Splits tab "
    output += "explains much of the scoring variance potential shown in the Volatility Profile."

    return output


def _section_6_volatility(
    home: str, away: str, volatility_data: Optional[Dict], matchup_summary: Dict
) -> str:
    """Section 6: Volatility & Game Script Risk"""

    output = "## 6. Volatility & Game Script Risk\n\n"

    if not volatility_data:
        output += "Volatility data provides context for the expected range of total scoring outcomes, but detailed volatility analysis is not available for this matchup.\n\n"
        output += "Generally, volatility stems from three-point variance, pace instability, and inconsistent defensive execution. "
        output += "Matchups with aligned pace and balanced offensive-defensive ratings tend toward lower volatility, while pace mismatches and three-point dependent offenses create higher variance."
        return output

    # If we have volatility data
    matchup_volatility = volatility_data.get('matchup_volatility', 0)
    home_volatility = volatility_data.get('home_volatility_index', 0)
    away_volatility = volatility_data.get('away_volatility_index', 0)

    output += f"The Volatility Profile shows a matchup volatility score of {matchup_volatility:.1f} out of 10, indicating "

    if matchup_volatility >= 7:
        output += "highly volatile expected outcomes. "
    elif matchup_volatility >= 4:
        output += "moderate volatility with reasonable outcome range. "
    else:
        output += "stable, low-variance expected outcomes. "

    output += f"This score synthesizes individual team volatility indices of {home_volatility:.1f} ({home}) and {away_volatility:.1f} ({away}).\n\n"

    output += "**Sources of Volatility**: \n\n"

    output += "Game-to-game scoring variance stems from several structural factors:\n\n"

    output += "- **Three-Point Shooting Variance**: Teams heavily dependent on three-point volume experience wider scoring ranges. "
    output += "The inherent variance in three-point shooting percentage creates 15-25 point swings between hot and cold nights.\n\n"

    output += "- **Pace Instability**: Teams with inconsistent pace from game to game create uncertainty in possession count. "
    output += "A team that plays 98 possessions one game and 108 the next introduces structural scoring variance independent of efficiency.\n\n"

    output += "- **Defensive Consistency**: Defenses that allow wildly different points allowed across games signal either inconsistent effort, "
    output += "scheme flexibility issues, or matchup-dependent effectiveness. This defensive variance directly impacts opponent scoring ranges.\n\n"

    output += "- **Blowout Risk**: Significant talent gaps or poor form matchups increase blowout probability. "
    output += "Blowouts reduce competitive possessions in the fourth quarter, typically suppressing total scoring below the natural pace-based expectation.\n\n"

    output += "**Volatility Interpretation**: "

    if matchup_volatility >= 7:
        output += "High volatility matchups require wider outcome ranges in total scoring expectations. "
        output += "The same structural factors that create a midpoint expectation can produce vastly different results based on which team executes better or experiences favorable shooting variance. "
        output += "These matchups carry higher risk for both over and under scenarios."
    elif matchup_volatility <= 3:
        output += "Low volatility matchups demonstrate narrow outcome ranges. "
        output += "Structural factors overwhelm variance, creating highly predictable scoring environments. "
        output += "These matchups typically feature aligned pace, balanced offensive-defensive matchups, and consistent execution patterns from both teams."
    else:
        output += "Moderate volatility creates reasonable outcome uncertainty without extreme risk. "
        output += "Structural factors define a clear central tendency, but execution variance and shooting performance can shift the result within a defined range."

    output += "\n\nThe volatility score visible in the War Room provides context for interpreting the central tendency shown in other metrics. "
    output += "High volatility doesn't mean the prediction is unreliable—it means the range of outcomes is wider."

    return output


def _section_7_similarity(
    home: str, away: str, similarity_data: Optional[Dict], similar_opponents_data: Optional[Dict]
) -> str:
    """Section 7: Similarity & Comparable Matchups"""

    output = "## 7. Similarity & Comparable Matchups\n\n"

    output += "The Similarity tab provides context by clustering teams into playstyle archetypes and identifying historical performance against similar opponents.\n\n"

    if similarity_data:
        output += "**Playstyle Clustering**: "
        output += "Teams are grouped into clusters based on pace, shot distribution, ball movement, and paint emphasis. "
        output += "These clusters reveal structural playstyle patterns independent of win-loss record or talent level.\n\n"

        # Would extract actual cluster labels and descriptions
        output += "The matchup archetype shown in the War Room connects these clusters to expected game dynamics. "
        output += "For example, when a Pace Pusher faces a Slow Grind team, the resulting pace typically falls between their individual preferences but closer to the Slow Grind team's tempo due to their ability to control possessions through rebounding and half-court execution.\n\n"

    if similar_opponents_data:
        output += "**Historical Performance vs Similar Opponents**: "
        output += "The Similar Opponents section shows how each team has performed against teams similar to tonight's opponent. "
        output += "This provides empirical evidence of how team styles interact.\n\n"

        output += "Teams that consistently outperform their season averages against similar opponents demonstrate structural advantages in that specific matchup archetype. "
        output += "Conversely, teams that underperform against similar playstyles reveal exploitable weaknesses.\n\n"

        output += "Significant deviations from season averages in these comparable matchups inform the matchup-based adjustments visible in the prediction calculations. "
        output += "If a team averages 118 points per game overall but only 112 against Three-Point Hunters, the War Room adjustments account for this historical underperformance.\n\n"

    output += "**Cluster-Based Adjustments**: "
    output += "The similarity engine generates pace and scoring adjustments based on how specific archetypes interact. "
    output += "These adjustments don't override the fundamental stats—they refine expectations based on playstyle compatibility.\n\n"

    output += "For instance, Pace Pushers typically accelerate game tempo even against slower opponents, but the degree of acceleration depends on the opponent's defensive rebounding and transition defense. "
    output += "The cluster adjustments visible in the prediction breakdown quantify these expected effects.\n\n"

    output += "The Similarity analysis connects abstract playstyle classifications to concrete historical performance, "
    output += "providing empirical grounding for the matchup-based expectations shown throughout the War Room."

    return output


def _section_8_synthesis(
    home: str, away: str, scoring_env: str,
    home_stats: Dict, away_stats: Dict, matchup_summary: Dict, prediction: Dict
) -> str:
    """Section 8: Full Matchup Synthesis"""

    output = "## 8. Full Matchup Synthesis\n\n"

    output += "The War Room presents a comprehensive structural analysis of this matchup, connecting pace, efficiency, defense, form, and variance into a coherent framework.\n\n"

    output += "**Dominant Forces**: "

    # Determine key factors
    combined_pace = (home_stats.get('pace', 100) + away_stats.get('pace', 100)) / 2

    if combined_pace >= 105:
        output += "Pace serves as the primary structural force in this matchup. "
        output += f"The elevated tempo of {combined_pace:.1f} possessions creates more scoring opportunities per minute, naturally inflating total scoring potential. "
    elif combined_pace <= 98:
        output += "Pace constraint serves as the primary limiting factor. "
        output += f"The slow tempo of {combined_pace:.1f} possessions reduces total scoring opportunities, creating a natural ceiling on point production. "

    # Defense quality
    avg_drtg = (home_stats.get('def_rating', 110) + away_stats.get('def_rating', 110)) / 2

    if avg_drtg < 108:
        output += "Strong defensive resistance from both teams creates additional scoring resistance beyond pace effects. "
        output += "The presence of quality defense forces tougher shots, reduces shooting efficiency, and limits transition opportunities. "
    elif avg_drtg > 115:
        output += "Defensive vulnerability on both sides creates exploitable scoring opportunities. "
        output += "Weak defensive resistance allows both teams to generate higher-percentage looks than their season averages might suggest. "

    output += "\n\n**Why the War Room Signals Align**: "
    output += f"The {scoring_env} scoring environment classification synthesizes these forces. "
    output += "The Matchup Indicators identify specific advantages within this environment—pace edge, shooting matchups, paint control, and free throw leverage. "
    output += "The Team Form Index shows whether each team is trending toward their performance ceiling or floor. "
    output += "The Volatility Profile quantifies outcome uncertainty. "
    output += "The Similarity analysis grounds these expectations in historical precedent.\n\n"

    output += "These signals reinforce rather than contradict each other because they derive from the same underlying structural realities: "
    output += "the pace both teams prefer, the efficiency with which they score, the quality of defensive resistance, and the variance introduced by three-point shooting and execution consistency.\n\n"

    output += "**Game Script Sensitivity**: "
    output += "The structural analysis shown in the War Room assumes competitive game flow. Several in-game developments could break this expected script:\n\n"

    output += f"- **Blowout Development**: If either team builds a 20+ point lead, competitive possessions decrease significantly in the fourth quarter. "
    output += "Blowouts typically suppress total scoring 8-12 points below pace-based expectations due to reduced intensity and shorter possessions from the trailing team.\n\n"

    output += f"- **Foul Trouble**: If key rotation players accumulate early fouls, defensive aggression decreases and offensive efficiency typically increases. "
    output += "This can elevate scoring above structural expectations, particularly if the fouled players are primary defenders.\n\n"

    output += f"- **Three-Point Variance Extremes**: If one team experiences extreme three-point shooting (>45% or <25%), "
    output += "scoring can deviate 12-18 points from the central expectation purely from shooting variance.\n\n"

    output += f"- **Pace Override**: Specific game situations (trailing team extending possessions, clock management, transition success rate) "
    output += "can push actual pace 4-6 possessions away from the structural expectation, directly impacting total scoring.\n\n"

    output += "The War Room analysis captures the structural forces that shape this matchup. "
    output += "It does not predict specific game events, foul distributions, or shooting variance outcomes. "
    output += "It provides the framework for understanding why this matchup looks the way it does based on repeatable, measurable factors—"
    output += "the foundation for evaluating whether specific betting lines offer value relative to the structural reality of the matchup."

    return output
