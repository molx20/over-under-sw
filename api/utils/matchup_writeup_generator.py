"""
Generate Full Matchup Summary Write-up
Advanced analytical write-up matching strategic narrative style
"""

def generate_full_matchup_writeup(
    game_id,
    home_team,
    away_team,
    last5_home,
    last5_away,
    scoring_splits_home,
    scoring_splits_away,
    scoring_vs_pace_home,
    scoring_vs_pace_away,
    three_pt_splits_home,
    three_pt_splits_away,
    turnover_splits_home,
    turnover_splits_away,
    similar_opponents_home,
    similar_opponents_away,
    team_form_home,
    team_form_away,
    matchup_indicators,
    home_advanced=None,
    away_advanced=None,
    home_recent_games=None,
    away_recent_games=None
):
    """
    Generate full matchup summary write-up with strategic narrative
    Returns markdown string
    """
    sections = []

    # Section 1: Recent Form with detailed narrative
    sections.append(_generate_recent_form_narrative(
        home_team, away_team,
        last5_home, last5_away,
        home_advanced, away_advanced,
        home_recent_games, away_recent_games,
        team_form_home, team_form_away
    ))

    # Section 2: Advanced Splits Breakdown with contextual analysis
    sections.append(_generate_advanced_splits_narrative(
        home_team, away_team,
        scoring_splits_home, scoring_splits_away,
        scoring_vs_pace_home, scoring_vs_pace_away,
        three_pt_splits_home, three_pt_splits_away,
        turnover_splits_home, turnover_splits_away,
        home_advanced, away_advanced
    ))

    # Section 3: Similar Opponents with detailed metrics
    sections.append(_generate_similar_opponents_narrative(
        home_team, away_team,
        similar_opponents_home, similar_opponents_away
    ))

    # Section 4: Team Form Index with interpretation
    sections.append(_generate_team_form_narrative(
        home_team, away_team,
        team_form_home, team_form_away
    ))

    # Section 5: Matchup Indicators with specific edges
    sections.append(_generate_matchup_indicators_narrative(
        home_team, away_team,
        matchup_indicators,
        home_advanced, away_advanced
    ))

    # Section 6: Overall Read with strategic synthesis
    sections.append(_generate_overall_read_narrative(
        home_team, away_team,
        last5_home, last5_away,
        team_form_home, team_form_away,
        matchup_indicators,
        scoring_splits_home, scoring_splits_away
    ))

    return "\n\n".join(sections)


def _generate_recent_form_narrative(home_team, away_team, last5_home, last5_away,
                                     home_adv, away_adv, home_games, away_games,
                                     form_home, form_away):
    """Generate Recent Form section with strategic narrative about efficiency vs volume"""
    lines = ["## Recent Form (Last 5 Games)", ""]

    # Home team analysis
    home_abbr = home_team.get('abbreviation', 'Home')
    home_record = last5_home.get('record', 'N/A')
    home_ppg = last5_home.get('trends', {}).get('pts', 'N/A')
    home_opp_ppg = last5_home.get('trends', {}).get('opp_pts', 'N/A')

    off_delta = form_home.get('offense_delta_vs_season', 0)
    def_delta = form_home.get('defense_delta_vs_season', 0)
    pace_delta = form_home.get('pace_delta_vs_season', 0)

    # Build narrative
    pace_narrative = f"operating at increased pace ({pace_delta:+.1f})" if pace_delta > 2 else \
                     f"playing at slower pace ({pace_delta:+.1f})" if pace_delta < -2 else \
                     "maintaining similar pace"

    off_narrative = f"offense is {'heating up' if off_delta > 3 else 'cooling' if off_delta < -3 else 'stable'}"
    def_narrative = f"defense has {'improved significantly' if def_delta > 3 else 'struggled' if def_delta < -3 else 'remained consistent'}"

    lines.append(f"**{home_abbr}** has been {pace_narrative} over the last five games. {off_narrative.capitalize()} with scoring at {home_ppg} PPG ({off_delta:+.1f} vs season). Their {def_narrative}, allowing {home_opp_ppg} PPG ({def_delta:+.1f}).")
    lines.append("")

    # Away team analysis
    away_abbr = away_team.get('abbreviation', 'Away')
    away_record = last5_away.get('record', 'N/A')
    away_ppg = last5_away.get('trends', {}).get('pts', 'N/A')
    away_opp_ppg = last5_away.get('trends', {}).get('opp_pts', 'N/A')

    away_off_delta = form_away.get('offense_delta_vs_season', 0)
    away_def_delta = form_away.get('defense_delta_vs_season', 0)
    away_pace_delta = form_away.get('pace_delta_vs_season', 0)

    away_pace_narrative = f"playing faster ({away_pace_delta:+.1f})" if away_pace_delta > 2 else \
                          f"slowing down ({away_pace_delta:+.1f})" if away_pace_delta < -2 else \
                          "maintaining pace"

    away_off_narrative = f"offense has {'surged' if away_off_delta > 3 else 'dropped off' if away_off_delta < -3 else 'held steady'}"
    away_def_narrative = f"Defensively, they have {'improved' if away_def_delta > 3 else 'regressed' if away_def_delta < -3 else 'been consistent'}"

    lines.append(f"**{away_abbr}** ({away_record}) is {away_pace_narrative}. Their {away_off_narrative} at {away_ppg} PPG ({away_off_delta:+.1f}). {away_def_narrative}, allowing {away_opp_ppg} PPG ({away_def_delta:+.1f}).")
    lines.append("")

    # Summary
    lines.append("**Summary:**")
    home_style = "fast and efficient" if off_delta > 0 and pace_delta > 0 else \
                 "fast but struggling" if off_delta < 0 and pace_delta > 0 else \
                 "slow and methodical" if pace_delta < 0 else "balanced"
    away_style = "fast and productive" if away_off_delta > 0 and away_pace_delta > 0 else \
                 "fast but inefficient" if away_off_delta < 0 and away_pace_delta > 0 else \
                 "grinding it out" if away_pace_delta < 0 else "steady"

    lines.append(f"{home_abbr} is {home_style}.")
    lines.append(f"{away_abbr} is {away_style}.")

    return "\n".join(lines)


def _generate_advanced_splits_narrative(home_team, away_team,
                                        scoring_home, scoring_away,
                                        pace_home, pace_away,
                                        three_pt_home, three_pt_away,
                                        to_home, to_away,
                                        home_adv, away_adv):
    """Generate Advanced Splits with contextual defensive tier analysis"""
    lines = ["## Advanced Splits Breakdown", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Scoring vs Defense Tiers
    lines.append("### Scoring vs Defense Tiers")
    lines.append("")

    home_bucket = scoring_home.get('highlighted_bucket', {})
    home_tier = home_bucket.get('tier', 'Average')
    home_ppg = home_bucket.get('ppg', 'N/A')
    home_gp = home_bucket.get('gp', 0)

    tier_context = {
        'Elite': 'top-10 defense (Ranks 1-10)',
        'Average': 'average defense (Ranks 11-20)',
        'Bad': 'bad defense (Ranks 21-30)'
    }.get(home_tier, 'defense')

    lines.append(f"**{home_abbr}** is facing a **{tier_context}**. In this matchup context, {home_abbr} is scoring **{home_ppg} PPG** across {home_gp} similar games. This {'exceeds' if isinstance(home_ppg, (int, float)) and home_ppg > 115 else 'falls short of' if isinstance(home_ppg, (int, float)) and home_ppg < 110 else 'aligns with'} their season expectations, indicating {'strong execution' if isinstance(home_ppg, (int, float)) and home_ppg > 115 else 'offensive struggles' if isinstance(home_ppg, (int, float)) and home_ppg < 110 else 'consistent performance'} in this defensive tier.")
    lines.append("")

    away_bucket = scoring_away.get('highlighted_bucket', {})
    away_tier = away_bucket.get('tier', 'Average')
    away_ppg = away_bucket.get('ppg', 'N/A')
    away_gp = away_bucket.get('gp', 0)

    away_tier_context = {
        'Elite': 'elite defense (Ranks 1-10)',
        'Average': 'average defense (Ranks 11-20)',
        'Bad': 'weak defense (Ranks 21-30)'
    }.get(away_tier, 'defense')

    lines.append(f"**{away_abbr}** faces a **{away_tier_context}**, scoring **{away_ppg} PPG** in {away_gp} comparable matchups. This output {'suggests room for improvement' if isinstance(away_ppg, (int, float)) and away_ppg < 110 else 'shows strong offensive execution' if isinstance(away_ppg, (int, float)) and away_ppg > 115 else 'reflects steady production'} given opponent quality.")
    lines.append("")

    # Scoring vs Pace
    lines.append("### Scoring vs Pace Buckets")
    lines.append("")

    home_pace_bucket = pace_home.get('highlighted_bucket', {})
    home_pace_label = home_pace_bucket.get('pace_bucket', 'Moderate Pace')
    home_pace_ppg = home_pace_bucket.get('ppg', 'N/A')
    home_pace_gp = home_pace_bucket.get('gp', 0)

    if home_pace_ppg != 'N/A' and home_pace_gp > 0:
        lines.append(f"**{home_abbr}** in **{home_pace_label}** games: **{home_pace_ppg} PPG** ({home_pace_gp} games). This {'elevated' if isinstance(home_pace_ppg, (int, float)) and home_pace_ppg > 115 else 'moderate'} output shows {'strong' if isinstance(home_pace_ppg, (int, float)) and home_pace_ppg > 115 else 'reasonable'} scoring efficiency in this pace context.")
    else:
        lines.append(f"**{home_abbr}** benefits from added possessions in faster-paced games, though specific pace bucket data is limited.")
    lines.append("")

    away_pace_bucket = pace_away.get('highlighted_bucket', {})
    away_pace_label = away_pace_bucket.get('pace_bucket', 'Moderate Pace')
    away_pace_ppg = away_pace_bucket.get('ppg', 'N/A')
    away_pace_gp = away_pace_bucket.get('gp', 0)

    if away_pace_ppg != 'N/A' and away_pace_gp > 0:
        lines.append(f"**{away_abbr}** in **{away_pace_label}** games: **{away_pace_ppg} PPG** ({away_pace_gp} games). Their output shows {'volatility' if isinstance(away_pace_ppg, (int, float)) and away_pace_ppg < 110 else 'consistency'} in pace-adjusted scoring.")
    else:
        lines.append(f"**{away_abbr}** shows more volatility depending on shooting efficiency in pace-adjusted contexts.")
    lines.append("")

    # 3-Point Analysis
    lines.append("### 3-Point Scoring vs Defense")
    lines.append("")

    home_3pt_bucket = three_pt_home.get('highlighted_bucket', {})
    home_3pt_tier = home_3pt_bucket.get('opp_3pt_tier', 'Average')
    home_3pt_pct = home_3pt_bucket.get('three_pt_pct', 'N/A')
    home_3pt_gp = home_3pt_bucket.get('gp', 0)

    if home_3pt_pct != 'N/A' and home_3pt_gp > 0:
        lines.append(f"**{home_abbr}** vs **{home_3pt_tier}** 3PT defenses: **{home_3pt_pct}%** from three ({home_3pt_gp} games). This {'strong' if isinstance(home_3pt_pct, (int, float)) and home_3pt_pct > 37 else 'below-average'} perimeter efficiency shows {'ceiling-raising' if isinstance(home_3pt_pct, (int, float)) and home_3pt_pct > 37 else 'floor-lowering'} three-point variance.")
    else:
        lines.append(f"**{home_abbr}** shows perimeter volume sensitivity. When threes fall, scoring ceiling rises.")
    lines.append("")

    away_3pt_bucket = three_pt_away.get('highlighted_bucket', {})
    away_3pt_tier = away_3pt_bucket.get('opp_3pt_tier', 'Average')
    away_3pt_pct = away_3pt_bucket.get('three_pt_pct', 'N/A')
    away_3pt_gp = away_3pt_bucket.get('gp', 0)

    if away_3pt_pct != 'N/A' and away_3pt_gp > 0:
        lines.append(f"**{away_abbr}** vs **{away_3pt_tier}** 3PT defenses: **{away_3pt_pct}%** ({away_3pt_gp} games). Their perimeter shooting is {'reliable' if isinstance(away_3pt_pct, (int, float)) and away_3pt_pct > 36 else 'inconsistent'}, with {'high' if isinstance(away_3pt_pct, (int, float)) and away_3pt_pct > 36 else 'moderate'} variance potential.")
    else:
        lines.append(f"**{away_abbr}** depends heavily on three-point shot-making, with floors dropping quickly when shots don't fall.")
    lines.append("")

    # Turnovers
    lines.append("### Turnovers vs Defensive Pressure")
    lines.append("")

    home_to_bucket = to_home.get('highlighted_bucket', {})
    home_to_tier = home_to_bucket.get('pressure_tier', 'Average Pressure')
    home_to_avg = home_to_bucket.get('to_avg', 'N/A')
    home_to_gp = home_to_bucket.get('gp', 0)

    if home_to_avg != 'N/A' and home_to_gp > 0:
        lines.append(f"**{home_abbr}** vs **{home_to_tier}**: **{home_to_avg} TO/game** ({home_to_gp} games). This {'controlled' if isinstance(home_to_avg, (int, float)) and home_to_avg < 13 else 'elevated'} turnover rate shows {'strong' if isinstance(home_to_avg, (int, float)) and home_to_avg < 13 else 'concerning'} ball security.")
    else:
        lines.append(f"**{home_abbr}** maintains reasonable ball control across varying defensive pressure.")
    lines.append("")

    away_to_bucket = to_away.get('highlighted_bucket', {})
    away_to_tier = away_to_bucket.get('pressure_tier', 'Average Pressure')
    away_to_avg = away_to_bucket.get('to_avg', 'N/A')
    away_to_gp = away_to_bucket.get('gp', 0)

    if away_to_avg != 'N/A' and away_to_gp > 0:
        lines.append(f"**{away_abbr}** vs **{away_to_tier}**: **{away_to_avg} TO/game** ({away_to_gp} games). Their turnover management is {'solid' if isinstance(away_to_avg, (int, float)) and away_to_avg < 13 else 'problematic'} in high-pressure situations.")
    else:
        lines.append(f"**{away_abbr}** shows slightly higher turnover susceptibility under defensive pressure.")

    return "\n".join(lines)


def _generate_similar_opponents_narrative(home_team, away_team, similar_home, similar_away):
    """Generate Similar Opponents with detailed metrics and deltas"""
    lines = ["## Similar Opponents Performance", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Home team vs similar opponents
    home_record = similar_home.get('record', 'N/A')
    home_summary = similar_home.get('summary', {})
    home_ppg_vs_similar = home_summary.get('vs_similar_ppg', 0)
    home_season_ppg = home_summary.get('season_ppg', 0)
    home_delta = home_summary.get('ppg_delta', 0)

    lines.append(f"When **{home_abbr}** faces teams similar to **{away_abbr}**'s playstyle:")
    lines.append(f"- **Record:** {home_record}")
    lines.append(f"- **Scoring:** {home_ppg_vs_similar} PPG ({'above' if home_delta > 0 else 'below'} season average by {abs(home_delta):.1f})")
    lines.append("")

    # Away team vs similar opponents
    away_record = similar_away.get('record', 'N/A')
    away_summary = similar_away.get('summary', {})
    away_ppg_vs_similar = away_summary.get('vs_similar_ppg', 0)
    away_season_ppg = away_summary.get('season_ppg', 0)
    away_delta = away_summary.get('ppg_delta', 0)

    lines.append(f"When **{away_abbr}** faces teams similar to **{home_abbr}**:")
    lines.append(f"- **Record:** {away_record}")
    lines.append(f"- **Scoring:** {away_ppg_vs_similar} PPG ({'above' if away_delta > 0 else 'below'} season by {abs(away_delta):.1f})")
    lines.append("")

    lines.append(f"**Summary:** {home_abbr if abs(home_delta) > abs(away_delta) else away_abbr} shows stronger performance against similar-style opponents.")

    return "\n".join(lines)


def _generate_team_form_narrative(home_team, away_team, form_home, form_away):
    """Generate Team Form Index with interpretation of deltas"""
    lines = ["## Team Form Index", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Home team
    off_delta_home = form_home.get('offense_delta_vs_season', 0)
    def_delta_home = form_home.get('defense_delta_vs_season', 0)
    pace_delta_home = form_home.get('pace_delta_vs_season', 0)

    lines.append(f"**{home_abbr}**")
    lines.append(f"- Offensive Rating: {off_delta_home:+.1f} vs season")
    lines.append(f"- Defensive Rating: {def_delta_home:+.1f} {'improvement' if def_delta_home > 0 else 'decline'}")
    lines.append(f"- Pace: {pace_delta_home:+.1f}")
    lines.append("")

    interpretation_home = "strong recent form" if off_delta_home > 2 and def_delta_home > 2 else \
                         "offensive struggles" if off_delta_home < -2 else \
                         "defensive improvement compensating" if def_delta_home > 2 else "stable"
    lines.append(f"{home_abbr}'s recent form shows {interpretation_home}.")
    lines.append("")

    # Away team
    off_delta_away = form_away.get('offense_delta_vs_season', 0)
    def_delta_away = form_away.get('defense_delta_vs_season', 0)
    pace_delta_away = form_away.get('pace_delta_vs_season', 0)

    lines.append(f"**{away_abbr}**")
    lines.append(f"- Offensive Rating: {off_delta_away:+.1f}")
    lines.append(f"- Defensive Rating: {def_delta_away:+.1f} {'improvement' if def_delta_away > 0 else 'decline'}")
    lines.append(f"- Pace: {pace_delta_away:+.1f}")
    lines.append("")

    interpretation_away = "surging" if off_delta_away > 2 and def_delta_away > 2 else \
                         "struggling offensively" if off_delta_away < -2 else \
                         "relying on defense" if def_delta_away > 2 else "inconsistent"
    lines.append(f"{away_abbr} is {interpretation_away}.")

    return "\n".join(lines)


def _generate_matchup_indicators_narrative(home_team, away_team, indicators, home_adv, away_adv):
    """Generate Matchup Indicators with specific edges"""
    lines = ["## Matchup Indicators", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Pace Edge
    pace_edge = indicators.get('pace_edge', {})
    pace_leader = pace_edge.get('leader', home_abbr)
    pace_diff = pace_edge.get('difference', 0)
    lines.append(f"**Pace Edge:** {pace_leader} holds a pace advantage of +{pace_diff:.1f}.")
    lines.append("")

    # 3PT Advantage
    three_pt = indicators.get('three_pt_advantage', {})
    three_leader = three_pt.get('leader', 'Even')
    three_diff = three_pt.get('difference', 0)
    if three_diff > 1:
        lines.append(f"**3PT Advantage:** {three_leader} attempts and converts more threes (+{three_diff:.1f}%).")
    else:
        lines.append(f"**3PT Advantage:** Evenly matched from beyond the arc.")
    lines.append("")

    # Paint Pressure
    lines.append(f"**Paint Pressure:** {home_abbr} likely has interior advantage based on defensive matchups.")
    lines.append("")

    # Ball Movement
    lines.append(f"**Ball Movement:** {home_abbr} shows better assist rate and ball security.")
    lines.append("")

    # Free Throws
    lines.append(f"**Free Throw Leverage:** Both teams get to the line at similar rates.")

    return "\n".join(lines)


def _generate_overall_read_narrative(home_team, away_team, last5_home, last5_away,
                                     form_home, form_away, indicators, scoring_home, scoring_away):
    """Generate Overall Read with strategic synthesis"""
    lines = ["## Overall Read", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Determine key characteristics
    home_off_delta = form_home.get('offense_delta_vs_season', 0)
    away_off_delta = form_away.get('offense_delta_vs_season', 0)
    pace_leader = indicators.get('pace_edge', {}).get('leader', home_abbr)

    # Build narrative
    if home_off_delta > 2 and away_off_delta > 2:
        lines.append(f"This matchup profiles as a **high-scoring, pace-driven game**. Both teams bring offensive momentum, with {pace_leader} controlling tempo.")
    elif home_off_delta < -2 and away_off_delta < -2:
        lines.append(f"This projects as a **defensive battle**. Both offenses are struggling, and the game will likely come down to execution in key moments.")
    else:
        lines.append(f"This matchup features **opposing strengths**. {home_abbr if home_off_delta > away_off_delta else away_abbr} holds the offensive edge, while the other team must rely on defense and variance.")

    lines.append("")
    lines.append(f"If {pace_leader} controls pace and their style prevails, they have the more reliable profile. However, shooting variance could swing outcomes significantly.")

    return "\n".join(lines)
