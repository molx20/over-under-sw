"""
Generate Full Matchup Summary Write-up
Pulls from real data sources to create markdown breakdown
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
    matchup_indicators
):
    """
    Generate full matchup summary write-up from all data sources
    Returns markdown string
    """
    sections = []

    # Section 1: Recent Form
    sections.append(_generate_recent_form_section(home_team, away_team, last5_home, last5_away))

    # Section 2: Advanced Splits Breakdown
    sections.append(_generate_advanced_splits_section(
        home_team, away_team,
        scoring_splits_home, scoring_splits_away,
        scoring_vs_pace_home, scoring_vs_pace_away,
        three_pt_splits_home, three_pt_splits_away,
        turnover_splits_home, turnover_splits_away
    ))

    # Section 3: Similar Opponents Performance
    sections.append(_generate_similar_opponents_section(
        home_team, away_team,
        similar_opponents_home,
        similar_opponents_away
    ))

    # Section 4: Team Form Index
    sections.append(_generate_team_form_section(home_team, away_team, team_form_home, team_form_away))

    # Section 5: Matchup Indicators
    sections.append(_generate_matchup_indicators_section(home_team, away_team, matchup_indicators))

    # Section 6: Overall Read
    sections.append(_generate_overall_read_section(
        home_team, away_team,
        last5_home, last5_away,
        team_form_home, team_form_away,
        matchup_indicators
    ))

    return "\n\n".join(sections)


def _generate_recent_form_section(home_team, away_team, last5_home, last5_away):
    """Generate Recent Form section from Last 5 Games data"""
    lines = ["## Recent Form (Last 5 Games)", ""]

    # Home team
    home_record = last5_home.get('record', '0-0')
    home_trends = last5_home.get('trends', {})
    home_pts_trend = home_trends.get('pts', 'N/A')
    home_opp_pts_trend = home_trends.get('opp_pts', 'N/A')

    lines.append(f"**{home_team['abbreviation']}** ({home_record})")
    lines.append(f"- Averaging {home_pts_trend} PPG, allowing {home_opp_pts_trend} PPG")

    # Away team
    away_record = last5_away.get('record', '0-0')
    away_trends = last5_away.get('trends', {})
    away_pts_trend = away_trends.get('pts', 'N/A')
    away_opp_pts_trend = away_trends.get('opp_pts', 'N/A')

    lines.append("")
    lines.append(f"**{away_team['abbreviation']}** ({away_record})")
    lines.append(f"- Averaging {away_pts_trend} PPG, allowing {away_opp_pts_trend} PPG")

    return "\n".join(lines)


def _generate_advanced_splits_section(
    home_team, away_team,
    scoring_splits_home, scoring_splits_away,
    scoring_vs_pace_home, scoring_vs_pace_away,
    three_pt_splits_home, three_pt_splits_away,
    turnover_splits_home, turnover_splits_away
):
    """Generate Advanced Splits Breakdown with highlighted bucket values"""
    lines = ["## Advanced Splits Breakdown", ""]

    # Scoring vs Defense Tiers
    lines.append("### Scoring vs Defense Tiers")
    lines.append("")

    # Home team scoring vs defense
    home_def_bucket = scoring_splits_home.get('highlighted_bucket', {})
    home_def_tier = home_def_bucket.get('tier', 'N/A')
    home_def_ppg = home_def_bucket.get('ppg', 'N/A')
    home_def_gp = home_def_bucket.get('gp', 0)

    lines.append(f"**{home_team['abbreviation']}** vs {home_def_tier} defenses: **{home_def_ppg} PPG** ({home_def_gp} games)")

    # Away team scoring vs defense
    away_def_bucket = scoring_splits_away.get('highlighted_bucket', {})
    away_def_tier = away_def_bucket.get('tier', 'N/A')
    away_def_ppg = away_def_bucket.get('ppg', 'N/A')
    away_def_gp = away_def_bucket.get('gp', 0)

    lines.append(f"**{away_team['abbreviation']}** vs {away_def_tier} defenses: **{away_def_ppg} PPG** ({away_def_gp} games)")
    lines.append("")

    # Scoring vs Pace Buckets
    lines.append("### Scoring vs Pace Buckets")
    lines.append("")

    # Home team scoring vs pace
    home_pace_bucket = scoring_vs_pace_home.get('highlighted_bucket', {})
    home_pace_label = home_pace_bucket.get('pace_bucket', 'N/A')
    home_pace_ppg = home_pace_bucket.get('ppg', 'N/A')
    home_pace_gp = home_pace_bucket.get('gp', 0)

    lines.append(f"**{home_team['abbreviation']}** in {home_pace_label} games: **{home_pace_ppg} PPG** ({home_pace_gp} games)")

    # Away team scoring vs pace
    away_pace_bucket = scoring_vs_pace_away.get('highlighted_bucket', {})
    away_pace_label = away_pace_bucket.get('pace_bucket', 'N/A')
    away_pace_ppg = away_pace_bucket.get('ppg', 'N/A')
    away_pace_gp = away_pace_bucket.get('gp', 0)

    lines.append(f"**{away_team['abbreviation']}** in {away_pace_label} games: **{away_pace_ppg} PPG** ({away_pace_gp} games)")
    lines.append("")

    # 3-Point Scoring vs Defense
    lines.append("### 3-Point Scoring vs Defense")
    lines.append("")

    # Home team 3PT vs defense
    home_3pt_bucket = three_pt_splits_home.get('highlighted_bucket', {})
    home_3pt_tier = home_3pt_bucket.get('opp_3pt_tier', 'N/A')
    home_3pt_pct = home_3pt_bucket.get('three_pt_pct', 'N/A')
    home_3pt_gp = home_3pt_bucket.get('gp', 0)

    lines.append(f"**{home_team['abbreviation']}** vs {home_3pt_tier} 3PT defenses: **{home_3pt_pct}%** ({home_3pt_gp} games)")

    # Away team 3PT vs defense
    away_3pt_bucket = three_pt_splits_away.get('highlighted_bucket', {})
    away_3pt_tier = away_3pt_bucket.get('opp_3pt_tier', 'N/A')
    away_3pt_pct = away_3pt_bucket.get('three_pt_pct', 'N/A')
    away_3pt_gp = away_3pt_bucket.get('gp', 0)

    lines.append(f"**{away_team['abbreviation']}** vs {away_3pt_tier} 3PT defenses: **{away_3pt_pct}%** ({away_3pt_gp} games)")
    lines.append("")

    # Turnovers vs Defensive Pressure
    lines.append("### Turnovers vs Defensive Pressure")
    lines.append("")

    # Home team turnovers vs pressure
    home_to_bucket = turnover_splits_home.get('highlighted_bucket', {})
    home_to_tier = home_to_bucket.get('pressure_tier', 'N/A')
    home_to_avg = home_to_bucket.get('to_avg', 'N/A')
    home_to_gp = home_to_bucket.get('gp', 0)

    lines.append(f"**{home_team['abbreviation']}** vs {home_to_tier} pressure: **{home_to_avg} TO/game** ({home_to_gp} games)")

    # Away team turnovers vs pressure
    away_to_bucket = turnover_splits_away.get('highlighted_bucket', {})
    away_to_tier = away_to_bucket.get('pressure_tier', 'N/A')
    away_to_avg = away_to_bucket.get('to_avg', 'N/A')
    away_to_gp = away_to_bucket.get('gp', 0)

    lines.append(f"**{away_team['abbreviation']}** vs {away_to_tier} pressure: **{away_to_avg} TO/game** ({away_to_gp} games)")

    return "\n".join(lines)


def _generate_similar_opponents_section(home_team, away_team, similar_home, similar_away):
    """Generate Similar Opponents Performance section"""
    lines = ["## Similar Opponents Performance", ""]

    # Home team
    home_record = similar_home.get('record', 'N/A')
    home_summary = similar_home.get('summary', {})
    home_vs_similar_ppg = home_summary.get('vs_similar_ppg', 'N/A')
    home_season_ppg = home_summary.get('season_ppg', 'N/A')
    home_ppg_delta = home_summary.get('ppg_delta', 'N/A')

    lines.append(f"**{home_team['abbreviation']}** vs similar opponents: **{home_record}**")
    lines.append(f"- {home_vs_similar_ppg} PPG vs similar ({home_ppg_delta:+.1f} vs season avg of {home_season_ppg})")

    # Away team
    away_record = similar_away.get('record', 'N/A')
    away_summary = similar_away.get('summary', {})
    away_vs_similar_ppg = away_summary.get('vs_similar_ppg', 'N/A')
    away_season_ppg = away_summary.get('season_ppg', 'N/A')
    away_ppg_delta = away_summary.get('ppg_delta', 'N/A')

    lines.append("")
    lines.append(f"**{away_team['abbreviation']}** vs similar opponents: **{away_record}**")
    lines.append(f"- {away_vs_similar_ppg} PPG vs similar ({away_ppg_delta:+.1f} vs season avg of {away_season_ppg})")

    return "\n".join(lines)


def _generate_team_form_section(home_team, away_team, form_home, form_away):
    """Generate Team Form Index section with deltas"""
    lines = ["## Team Form Index", ""]

    # Home team
    home_offense_delta = form_home.get('offense_delta_vs_season', 0)
    home_defense_delta = form_home.get('defense_delta_vs_season', 0)
    home_pace_delta = form_home.get('pace_delta_vs_season', 0)

    lines.append(f"**{home_team['abbreviation']}**")
    lines.append(f"- Offense: {home_offense_delta:+.1f} vs season")
    lines.append(f"- Defense: {home_defense_delta:+.1f} vs season")
    lines.append(f"- Pace: {home_pace_delta:+.1f} vs season")

    # Away team
    away_offense_delta = form_away.get('offense_delta_vs_season', 0)
    away_defense_delta = form_away.get('defense_delta_vs_season', 0)
    away_pace_delta = form_away.get('pace_delta_vs_season', 0)

    lines.append("")
    lines.append(f"**{away_team['abbreviation']}**")
    lines.append(f"- Offense: {away_offense_delta:+.1f} vs season")
    lines.append(f"- Defense: {away_defense_delta:+.1f} vs season")
    lines.append(f"- Pace: {away_pace_delta:+.1f} vs season")

    return "\n".join(lines)


def _generate_matchup_indicators_section(home_team, away_team, indicators):
    """Generate Matchup Indicators section"""
    lines = ["## Matchup Indicators", ""]

    pace_edge = indicators.get('pace_edge', {})
    three_pt_advantage = indicators.get('three_pt_advantage', {})
    turnover_battle = indicators.get('turnover_battle', {})

    # Pace Edge
    pace_leader = pace_edge.get('leader', 'N/A')
    pace_diff = pace_edge.get('difference', 0)
    lines.append(f"**Pace Edge**: {pace_leader} (+{pace_diff:.1f})")

    # 3PT Advantage
    three_pt_leader = three_pt_advantage.get('leader', 'N/A')
    three_pt_diff = three_pt_advantage.get('difference', 0)
    lines.append(f"**3PT Advantage**: {three_pt_leader} (+{three_pt_diff:.1f}%)")

    # Turnover Battle
    to_leader = turnover_battle.get('advantage', 'N/A')
    lines.append(f"**Turnover Battle**: {to_leader}")

    return "\n".join(lines)


def _generate_overall_read_section(home_team, away_team, last5_home, last5_away, form_home, form_away, indicators):
    """Generate Overall Read summary paragraph"""
    lines = ["## Overall Read", ""]

    # Determine form trends
    home_offense_delta = form_home.get('offense_delta_vs_season', 0)
    away_offense_delta = form_away.get('offense_delta_vs_season', 0)

    home_hot = home_offense_delta > 2
    away_hot = away_offense_delta > 2

    # Determine pace expectation
    pace_edge = indicators.get('pace_edge', {})
    pace_diff = pace_edge.get('difference', 0)
    pace_expectation = "up-tempo" if pace_diff > 2 else "controlled-pace" if pace_diff < -2 else "moderate-pace"

    # Build summary
    if home_hot and away_hot:
        summary = f"Both teams enter this matchup trending offensively. Expect a {pace_expectation} game with scoring opportunities on both ends."
    elif home_hot:
        summary = f"{home_team['abbreviation']} brings offensive momentum into this {pace_expectation} matchup, while {away_team['abbreviation']} looks to slow things down."
    elif away_hot:
        summary = f"{away_team['abbreviation']} enters hot offensively against {home_team['abbreviation']} in what projects as a {pace_expectation} game."
    else:
        summary = f"Both teams have been inconsistent offensively. This {pace_expectation} matchup could come down to defensive execution."

    lines.append(summary)

    return "\n".join(lines)
