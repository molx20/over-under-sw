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

    # 3-Point Analysis
    lines.append("### 3-Point Scoring vs Defense")
    lines.append("")

    home_3pt_bucket = three_pt_home.get('highlighted_bucket', {})
    home_3pt_tier = home_3pt_bucket.get('opp_3pt_tier', 'Average')
    home_3pt_ppg = home_3pt_bucket.get('three_pt_ppg', 'N/A')
    home_3pt_gp = home_3pt_bucket.get('gp', 0)
    home_3pt_opp_rank = home_3pt_bucket.get('opp_rank', None)

    # Map 3PT tier to rank ranges
    three_pt_ranges = {
        'Elite': 'Ranks 1-10',
        'Average': 'Ranks 11-20',
        'Bad': 'Ranks 21-30'
    }
    home_3pt_range = three_pt_ranges.get(home_3pt_tier, '')

    if home_3pt_ppg != 'N/A' and home_3pt_gp > 0:
        opp_rank_text = f", opponent **#{home_3pt_opp_rank}**" if home_3pt_opp_rank else ""
        lines.append(f"**{home_abbr}** is facing **{home_3pt_tier.lower()} 3PT defense ({home_3pt_range}){opp_rank_text}**. In this matchup context, {home_abbr} is averaging **{home_3pt_ppg} 3PT PPG** across {home_3pt_gp} similar games. This {'strong' if isinstance(home_3pt_ppg, (int, float)) and home_3pt_ppg > 38 else 'below-average'} perimeter efficiency shows {'ceiling-raising' if isinstance(home_3pt_ppg, (int, float)) and home_3pt_ppg > 38 else 'floor-lowering'} three-point variance.")
    else:
        lines.append(f"**{home_abbr}** shows perimeter volume sensitivity. When threes fall, scoring ceiling rises.")
    lines.append("")

    away_3pt_bucket = three_pt_away.get('highlighted_bucket', {})
    away_3pt_tier = away_3pt_bucket.get('opp_3pt_tier', 'Average')
    away_3pt_ppg = away_3pt_bucket.get('three_pt_ppg', 'N/A')
    away_3pt_gp = away_3pt_bucket.get('gp', 0)
    away_3pt_opp_rank = away_3pt_bucket.get('opp_rank', None)
    away_3pt_range = three_pt_ranges.get(away_3pt_tier, '')

    if away_3pt_ppg != 'N/A' and away_3pt_gp > 0:
        opp_rank_text = f", opponent **#{away_3pt_opp_rank}**" if away_3pt_opp_rank else ""
        lines.append(f"**{away_abbr}** faces **{away_3pt_tier.lower()} 3PT defense ({away_3pt_range}){opp_rank_text}**, averaging **{away_3pt_ppg} 3PT PPG** in {away_3pt_gp} comparable matchups. Their perimeter shooting is {'reliable' if isinstance(away_3pt_ppg, (int, float)) and away_3pt_ppg > 37 else 'inconsistent'}, with {'high' if isinstance(away_3pt_ppg, (int, float)) and away_3pt_ppg > 37 else 'moderate'} variance potential.")
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
    home_to_opp_rank = home_to_bucket.get('opp_rank', None)

    # Map pressure tier to rank ranges
    pressure_ranges = {
        'Elite Pressure': 'Ranks 1-10',
        'Average Pressure': 'Ranks 11-20',
        'Low Pressure': 'Ranks 21-30'
    }
    home_to_range = pressure_ranges.get(home_to_tier, '')

    if home_to_avg != 'N/A' and home_to_gp > 0:
        opp_rank_text = f", opponent **#{home_to_opp_rank}**" if home_to_opp_rank else ""
        lines.append(f"**{home_abbr}** is facing **{home_to_tier.lower()} ({home_to_range}){opp_rank_text}**. In this matchup context, {home_abbr} is averaging **{home_to_avg} TOV/G** across {home_to_gp} similar games. This {'controlled' if isinstance(home_to_avg, (int, float)) and home_to_avg < 13 else 'elevated'} turnover rate shows {'strong' if isinstance(home_to_avg, (int, float)) and home_to_avg < 13 else 'concerning'} ball security.")
    else:
        lines.append(f"**{home_abbr}** maintains reasonable ball control across varying defensive pressure.")
    lines.append("")

    away_to_bucket = to_away.get('highlighted_bucket', {})
    away_to_tier = away_to_bucket.get('pressure_tier', 'Average Pressure')
    away_to_avg = away_to_bucket.get('to_avg', 'N/A')
    away_to_gp = away_to_bucket.get('gp', 0)
    away_to_opp_rank = away_to_bucket.get('opp_rank', None)
    away_to_range = pressure_ranges.get(away_to_tier, '')

    if away_to_avg != 'N/A' and away_to_gp > 0:
        opp_rank_text = f", opponent **#{away_to_opp_rank}**" if away_to_opp_rank else ""
        lines.append(f"**{away_abbr}** faces **{away_to_tier.lower()} ({away_to_range}){opp_rank_text}**, averaging **{away_to_avg} TOV/G** in {away_to_gp} comparable matchups. Their turnover management is {'solid' if isinstance(away_to_avg, (int, float)) and away_to_avg < 13 else 'problematic'} in high-pressure situations.")
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
    """Generate Team Form Index as narrative paragraph"""
    lines = ["## Team Form Index", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Home team deltas
    off_delta_home = form_home.get('offense_delta_vs_season', 0)
    def_delta_home = form_home.get('defense_delta_vs_season', 0)
    pace_delta_home = form_home.get('pace_delta_vs_season', 0)

    # Away team deltas
    off_delta_away = form_away.get('offense_delta_vs_season', 0)
    def_delta_away = form_away.get('defense_delta_vs_season', 0)
    pace_delta_away = form_away.get('pace_delta_vs_season', 0)

    # Build 8-sentence narrative paragraph
    sentences = []

    # Sentence 1: Home offensive rating
    off_home_desc = "surging" if off_delta_home > 3 else "trending up" if off_delta_home > 0 else "struggling" if off_delta_home < -3 else "declining slightly" if off_delta_home < 0 else "holding steady"
    sentences.append(f"**{home_abbr}** enters this matchup with their offense {off_home_desc}, scoring **{off_delta_home:+.1f} points per game** {'above' if off_delta_home > 0 else 'below'} their season average over recent contests.")

    # Sentence 2: Home defensive rating
    def_home_desc = "significantly tighter" if def_delta_home > 3 else "improved" if def_delta_home > 0 else "considerably worse" if def_delta_home < -3 else "slightly worse" if def_delta_home < 0 else "consistent"
    sentences.append(f"Defensively, they've been {def_home_desc}, allowing **{abs(def_delta_home):.1f} {'fewer' if def_delta_home > 0 else 'more' if def_delta_home < 0 else 'the same'} points** compared to season norms.")

    # Sentence 3: Home pace
    pace_home_desc = "significantly faster" if pace_delta_home > 2 else "slightly faster" if pace_delta_home > 0 else "considerably slower" if pace_delta_home < -2 else "slightly slower" if pace_delta_home < 0 else "unchanged"
    sentences.append(f"Their pace has been {pace_home_desc}, running **{abs(pace_delta_home):.1f} possessions {'more' if pace_delta_home > 0 else 'fewer' if pace_delta_home < 0 else 'per game at the same rate'}** than their season average.")

    # Sentence 4: Home overall interpretation
    if off_delta_home > 2 and def_delta_home > 2:
        home_summary = "peaking at the right time with both ends firing"
    elif off_delta_home < -2 and def_delta_home < -2:
        home_summary = "struggling on both sides of the ball"
    elif off_delta_home > 2:
        home_summary = "riding an offensive hot streak"
    elif def_delta_home > 2:
        home_summary = "compensating offensive inconsistencies with defensive intensity"
    elif off_delta_home < -2:
        home_summary = "searching for offensive rhythm"
    else:
        home_summary = "maintaining relatively steady form"
    sentences.append(f"Overall, **{home_abbr}** is {home_summary}.")

    # Sentence 5: Away offensive rating
    off_away_desc = "explosive" if off_delta_away > 3 else "productive" if off_delta_away > 0 else "inconsistent" if off_delta_away < -3 else "below expectations" if off_delta_away < 0 else "steady"
    sentences.append(f"**{away_abbr}** has been {off_away_desc} offensively, posting **{off_delta_away:+.1f} points** {'above' if off_delta_away > 0 else 'below'} their season baseline in their last five games.")

    # Sentence 6: Away defensive rating
    def_away_desc = "locking down opponents" if def_delta_away > 3 else "showing defensive improvement" if def_delta_away > 0 else "leaking points" if def_delta_away < -3 else "vulnerable defensively" if def_delta_away < 0 else "defensively consistent"
    sentences.append(f"On defense, they've been {def_away_desc}, with opponents scoring **{abs(def_delta_away):.1f} {'fewer' if def_delta_away > 0 else 'more' if def_delta_away < 0 else 'the same'} points** than {away_abbr}'s season average allows.")

    # Sentence 7: Away pace
    pace_away_desc = "pushing tempo aggressively" if pace_delta_away > 2 else "playing faster" if pace_delta_away > 0 else "grinding to a slower pace" if pace_delta_away < -2 else "slowing things down" if pace_delta_away < 0 else "maintaining their typical pace"
    sentences.append(f"They've been {pace_away_desc}, at **{abs(pace_delta_away):.1f} possessions {'above' if pace_delta_away > 0 else 'below' if pace_delta_away < 0 else 'matching'}** season norms.")

    # Sentence 8: Comparative summary
    home_net = off_delta_home + def_delta_home
    away_net = off_delta_away + def_delta_away
    if abs(home_net - away_net) < 2:
        comparative = f"Both teams enter with similar recent trajectories, though **{home_abbr if abs(off_delta_home) > abs(off_delta_away) else away_abbr}** has shown slightly more offensive firepower in recent contests"
    elif home_net > away_net:
        comparative = f"**{home_abbr}** holds the momentum edge based on recent form, particularly {'their offensive surge' if off_delta_home > def_delta_home else 'their defensive improvements'}"
    else:
        comparative = f"**{away_abbr}** enters with superior recent form, driven primarily by {'offensive execution' if off_delta_away > def_delta_away else 'defensive intensity'}"
    sentences.append(f"{comparative}.")

    lines.append(" ".join(sentences))

    return "\n".join(lines)


def _generate_matchup_indicators_narrative(home_team, away_team, indicators, home_adv, away_adv):
    """Generate Matchup Indicators with detailed written breakdown"""
    lines = ["## Matchup Indicators", ""]

    home_abbr = home_team.get('abbreviation', 'Home')
    away_abbr = away_team.get('abbreviation', 'Away')

    # Pace Edge
    pace = indicators.get('pace', {})
    home_pace = pace.get('home', 100)
    away_pace = pace.get('away', 100)
    projected = pace.get('projected', 100)
    pace_leader = pace.get('leader', home_abbr)
    pace_follower = away_abbr if pace_leader == home_abbr else home_abbr

    pace_env = "slightly fast" if projected > 100 else "moderate" if projected >= 98 else "slower"
    tempo_desc = "modestly elevated" if projected > 100 else "measured" if projected >= 98 else "deliberate"

    lines.append(f"**Pace Edge**")
    lines.append(f"{pace_leader} holds a {'slight' if abs(home_pace - away_pace) < 3 else 'clear'} pace advantage in this matchup. While {pace_follower} averages {min(home_pace, away_pace):.1f} possessions and {pace_leader} plays {'faster' if abs(home_pace - away_pace) > 2 else 'slightly faster'} at {max(home_pace, away_pace):.1f}, the projected pace lands at {projected:.1f}, placing this game in a {pace_env} environment. That suggests tempo should be {tempo_desc} but not extreme, favoring a {'controlled uptick' if projected > 100 else 'grind-it-out pace'} rather than a {'full track meet' if projected > 100 else 'complete standstill'}.")
    lines.append("")

    # 3PT Advantage
    three_pt = indicators.get('three_pt', {})
    home_3pa = three_pt.get('home_attempts', 0)
    away_3pa = three_pt.get('away_attempts', 0)
    home_3p_pct = three_pt.get('home_pct', 0)
    away_3p_pct = three_pt.get('away_pct', 0)
    attempt_edge = three_pt.get('attempt_edge', 0)
    attempt_leader = three_pt.get('attempt_leader', home_abbr)
    efficiency_leader = three_pt.get('efficiency_leader', home_abbr)

    lines.append(f"**3PT Advantage**")
    lines.append(f"{attempt_leader} carries the edge in three-point volume, attempting {max(home_3pa, away_3pa):.1f} threes per game compared to {min(home_3pa, away_3pa):.1f}. However, {efficiency_leader} shoots more efficiently from deep at {max(home_3p_pct, away_3p_pct):.1f}% versus {min(home_3p_pct, away_3p_pct):.1f}%. Overall, {attempt_leader} has a +{attempt_edge:.1f} three-point attempt edge, but {efficiency_leader}'s shooting efficiency {'offsets that volume advantage' if attempt_leader != efficiency_leader else 'compounds their volume edge'}, making perimeter scoring {'more balanced than the raw attempts suggest' if attempt_leader != efficiency_leader else 'heavily tilted in their favor'}.")
    lines.append("")

    # Paint Pressure
    paint = indicators.get('paint', {})
    home_paint = paint.get('home_paint', 0)
    away_paint = paint.get('away_paint', 0)
    home_opp_paint = paint.get('home_opp_paint', 0)
    away_opp_paint = paint.get('away_opp_paint', 0)
    home_edge = paint.get('home_edge', 0)
    away_edge = paint.get('away_edge', 0)
    paint_leader = paint.get('leader', home_abbr)
    paint_edge = max(abs(home_edge), abs(away_edge))

    lines.append(f"**Paint Pressure**")
    lines.append(f"{paint_leader} owns a {'clear' if paint_edge > 15 else 'slight' if paint_edge > 5 else 'marginal'} interior scoring advantage in this matchup. {paint_leader} {'average' if paint_leader == home_abbr else 'averages'} {home_paint if paint_leader == home_abbr else away_paint:.1f} points in the paint, while {away_abbr if paint_leader == home_abbr else home_abbr} scores {away_paint if paint_leader == home_abbr else home_paint:.1f}, and {paint_leader} also benefits from {away_abbr if paint_leader == home_abbr else home_abbr} allowing {away_opp_paint if paint_leader == home_abbr else home_opp_paint:.1f} paint points per game. This creates a +{paint_edge:.1f} point paint edge for {paint_leader} in the matchup, making interior scoring {'one of the strongest structural advantages on the floor' if paint_edge > 15 else 'a moderate edge to exploit' if paint_edge > 5 else 'relatively even between both teams'}.")
    lines.append("")

    # Ball Movement
    ball = indicators.get('ball_movement', {})
    home_ast = ball.get('home_ast_pct', 0) if ball.get('home_ast_pct') else 0
    away_ast = ball.get('away_ast_pct', 0) if ball.get('away_ast_pct') else 0
    home_tov = ball.get('home_tov_pct', 0)
    away_tov = ball.get('away_tov_pct', 0)
    ast_leader = ball.get('ast_leader', home_abbr)
    tov_leader = ball.get('tov_leader', home_abbr)

    lines.append(f"**Ball Movement**")
    lines.append(f"{ast_leader} moves the ball more effectively, posting a {max(home_ast, away_ast):.1f}% assist rate compared to {min(home_ast, away_ast):.1f}%. At the same time, {tov_leader} protects the ball better, with a lower turnover rate ({min(home_tov, away_tov):.1f}%) than {away_abbr if tov_leader == home_abbr else home_abbr} ({max(home_tov, away_tov):.1f}%). This indicates {ast_leader}'s offense is {'more structured and efficient' if ast_leader == tov_leader else 'more fluid but riskier'}, while {away_abbr if ast_leader == home_abbr else home_abbr} is {'more prone to possessions breaking down' if ast_leader == tov_leader else 'more conservative with possessions'}.")
    lines.append("")

    # Free Throw Leverage
    ft = indicators.get('free_throws', {})
    home_fta = ft.get('home_fta', 0)
    away_fta = ft.get('away_fta', 0)
    home_ft_pct = ft.get('home_ft_pct', 0)
    away_ft_pct = ft.get('away_ft_pct', 0)
    attempt_leader = ft.get('attempt_leader', home_abbr)
    efficiency_leader = ft.get('efficiency_leader', home_abbr)

    lines.append(f"**Free Throw Leverage**")
    lines.append(f"{attempt_leader} {'also' if attempt_leader == ast_leader or attempt_leader == paint_leader else ''} holds an edge at the free-throw line. {attempt_leader} {'attempt' if attempt_leader == away_abbr else 'attempts'} more free throws per game ({max(home_fta, away_fta):.1f} vs {min(home_fta, away_fta):.1f}) and {'convert' if efficiency_leader == attempt_leader else 'while'} {efficiency_leader} {'converts' if efficiency_leader != attempt_leader else ''} them at a {'slightly' if abs(home_ft_pct - away_ft_pct) < 3 else 'noticeably'} {'higher' if attempt_leader == efficiency_leader else 'better'} rate ({max(home_ft_pct, away_ft_pct):.1f}% vs {min(home_ft_pct, away_ft_pct):.1f}%). This gives {attempt_leader if attempt_leader == efficiency_leader else efficiency_leader} a {'small but meaningful' if abs(home_ft_pct - away_ft_pct) < 3 else 'clear'} efficiency advantage, particularly in half-court and late-possession situations.")

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
