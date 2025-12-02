"""
Enhanced prediction engine for calculating Over/Under predictions
Uses comprehensive NBA stats from nba_api
"""

def calculate_pace_projection(home_pace, away_pace):
    """
    Calculate projected pace for the game
    Args:
        home_pace: Home team's pace
        away_pace: Away team's pace
    Returns:
        Projected possessions per team
    """
    # Average the two team's paces with slight weight to home team
    avg_pace = (home_pace * 0.52 + away_pace * 0.48)
    return avg_pace


def calculate_pace_effect(team_id, projected_pace, season_ppg, season='2025-26'):
    """
    Calculate pace-based scoring adjustment using team's historical pace bucket data.

    Args:
        team_id: Team's NBA ID
        projected_pace: Projected game pace (possessions per 48 minutes)
        season_ppg: Team's season average PPG (used as baseline)
        season: Season string

    Returns:
        Dict with:
        - adjustment: Points to add/subtract (moderated and capped)
        - bucket: 'slow', 'normal', or 'fast'
        - bucket_avg: Team's avg points in that bucket (or None if no data)
        - bucket_games: Number of games in that bucket (or 0 if no data)
        - raw_effect: Unmoderated effect before applying weight/cap
    """
    try:
        from api.utils.db_queries import get_pace_bucket, get_team_scoring_vs_pace
        from api.utils.pace_constants import PACE_EFFECT_WEIGHT, MAX_PACE_ADJUSTMENT

        # Determine pace bucket for this game
        bucket = get_pace_bucket(projected_pace)

        # Try to load team's scoring vs pace data
        pace_data = get_team_scoring_vs_pace(team_id, season)

        if not pace_data or bucket not in pace_data:
            # No data for this pace bucket - no adjustment
            return {
                'adjustment': 0.0,
                'bucket': bucket,
                'bucket_avg': None,
                'bucket_games': 0,
                'raw_effect': 0.0
            }

        bucket_info = pace_data[bucket]
        bucket_avg = bucket_info['avg_points']
        bucket_games = bucket_info['games']

        # Calculate raw effect (how much team scores in this bucket vs season avg)
        raw_effect = bucket_avg - season_ppg

        # Apply moderation factor (only trust PACE_EFFECT_WEIGHT % of the difference)
        moderated_effect = raw_effect * PACE_EFFECT_WEIGHT

        # Cap the adjustment to prevent wild swings
        capped_adjustment = max(-MAX_PACE_ADJUSTMENT, min(MAX_PACE_ADJUSTMENT, moderated_effect))

        return {
            'adjustment': capped_adjustment,
            'bucket': bucket,
            'bucket_avg': bucket_avg,
            'bucket_games': bucket_games,
            'raw_effect': raw_effect
        }

    except Exception as e:
        # Fallback: no adjustment on error
        print(f'[prediction_engine] Error calculating pace effect for team {team_id}: {e}')
        return {
            'adjustment': 0.0,
            'bucket': 'unknown',
            'bucket_avg': None,
            'bucket_games': 0,
            'raw_effect': 0.0
        }


def calculate_team_scoring_with_profile(team_id, team_stats, opponent_stats, pace, is_home=True, season='2025-26'):
    """
    Calculate expected scoring using team-specific profile weights.
    Falls back to global weights if profile not available.

    HYBRID APPROACH:
    - Keeps current 60/40 rating/PPG baseline blend
    - Uses profile weights for pace and home court adjustments only

    Args:
        team_id: Team's NBA ID (for profile lookup)
        team_stats: Dict with team's stats (overall, advanced, etc.)
        opponent_stats: Dict with opponent's stats
        pace: Projected pace for the game
        is_home: Whether team is playing at home
        season: Season string

    Returns:
        Expected points for the team
    """
    # Try to load team profile
    try:
        from api.utils.db_queries import get_team_profile
        profile = get_team_profile(team_id, season)

        if profile:
            pace_weight = profile['pace_weight']
            home_away_weight = profile['home_away_weight']
        else:
            # Fallback to global weights (current behavior)
            pace_weight = 1.0
            home_away_weight = 1.0
    except Exception as e:
        # Fallback on any error
        print(f'[prediction_engine] Error loading profile for team {team_id}: {e}')
        pace_weight = 1.0
        home_away_weight = 1.0

    # Extract key stats
    team_ppg = team_stats.get('overall', {}).get('PTS', 110.0)
    team_ortg = team_stats.get('advanced', {}).get('OFF_RATING', 110.0)

    # Opponent defensive stats
    opp_drtg = opponent_stats.get('advanced', {}).get('DEF_RATING', 110.0)
    opp_opp_ppg = opponent_stats.get('opponent', {}).get('OPP_PTS', 110.0)

    # Method 1: Simple PPG average
    ppg_projection = (team_ppg + opp_opp_ppg) / 2

    # Method 2: Advanced rating-based projection
    league_avg_rating = 112.0
    league_avg_ppg = 115.0
    rating_projection = (team_ortg / league_avg_rating) * (league_avg_rating / opp_drtg) * league_avg_ppg

    # KEEP CURRENT 60/40 BLEND (not affected by profile)
    baseline = rating_projection * 0.6 + ppg_projection * 0.4

    # Apply pace adjustment (MODULATED by team's pace_weight from profile)
    pace_factor = (pace / 100.0) * pace_weight
    adjusted_score = baseline * pace_factor

    # Home court advantage (MODULATED by team's home_away_weight from profile)
    if is_home:
        adjusted_score += 2.5 * home_away_weight
    else:
        adjusted_score -= 1.0 * home_away_weight

    return adjusted_score


def calculate_team_scoring(team_stats, opponent_stats, pace, is_home=True):
    """
    Calculate expected scoring for a team using advanced metrics

    Args:
        team_stats: Dict with team's stats (overall, advanced, etc.)
        opponent_stats: Dict with opponent's stats
        pace: Projected pace for the game
        is_home: Whether team is playing at home

    Returns:
        Expected points for the team
    """
    # Extract key stats
    team_ppg = team_stats.get('overall', {}).get('PTS', 110.0)
    team_ortg = team_stats.get('advanced', {}).get('OFF_RATING', 110.0)

    # Opponent defensive stats
    opp_drtg = opponent_stats.get('advanced', {}).get('DEF_RATING', 110.0)
    opp_opp_ppg = opponent_stats.get('opponent', {}).get('OPP_PTS', 110.0)

    # Method 1: Simple PPG average
    ppg_projection = (team_ppg + opp_opp_ppg) / 2

    # Method 2: Advanced rating-based projection
    # Formula: Team_ORTG / League_Avg * Opp_DRTG / League_Avg * League_Avg_PPG
    league_avg_rating = 112.0  # Approximate league average
    league_avg_ppg = 115.0     # Approximate league average PPG

    rating_projection = (team_ortg / league_avg_rating) * (league_avg_rating / opp_drtg) * league_avg_ppg

    # Combine both methods (60% advanced, 40% simple)
    baseline = rating_projection * 0.6 + ppg_projection * 0.4

    # Pace adjustment (normalized to 100 possessions)
    pace_factor = pace / 100.0
    adjusted_score = baseline * pace_factor

    # Home court advantage (typically 2-3 points)
    if is_home:
        adjusted_score += 2.5
    else:
        adjusted_score -= 1.0

    return adjusted_score

def calculate_recent_form_factor(recent_games):
    """
    Calculate a factor based on recent performance

    Args:
        recent_games: List of recent games

    Returns:
        Factor adjustment (-5 to +5 points)
    """
    if not recent_games or len(recent_games) == 0:
        return 0

    # Calculate average points from recent games
    recent_ppg = sum(game.get('PTS', 0) for game in recent_games) / len(recent_games)

    # Calculate trend (are they improving or declining?)
    if len(recent_games) >= 3:
        first_half_avg = sum(game.get('PTS', 0) for game in recent_games[:2]) / 2
        second_half_avg = sum(game.get('PTS', 0) for game in recent_games[-3:]) / 3
        trend = second_half_avg - first_half_avg
    else:
        trend = 0

    # Win percentage in recent games
    wins = sum(1 for game in recent_games if game.get('WL') == 'W')
    win_pct = wins / len(recent_games)

    # Combine factors
    form_factor = (trend * 0.3) + ((win_pct - 0.5) * 5)

    # Cap at +/- 5 points
    return max(-5, min(5, form_factor))

def calculate_pace_consistency(home_recent, away_recent):
    """
    Calculate how consistent the pace has been
    Lower variance = higher confidence
    """
    if not home_recent or not away_recent:
        return 10  # Default high variance

    # Calculate variance in recent game totals
    home_totals = [game.get('PTS', 0) for game in home_recent]
    away_totals = [game.get('PTS', 0) for game in away_recent]

    import statistics
    try:
        home_std = statistics.stdev(home_totals) if len(home_totals) > 1 else 10
        away_std = statistics.stdev(away_totals) if len(away_totals) > 1 else 10
        avg_std = (home_std + away_std) / 2
        return avg_std
    except:
        return 10

def calculate_confidence(predicted_total, betting_line, factors):
    """
    Calculate confidence level for the prediction

    Args:
        predicted_total: Our predicted total
        betting_line: Vegas betting line
        factors: Dictionary of various factors affecting confidence

    Returns:
        Confidence percentage (0-100)
    """
    # Start with base confidence
    confidence = 50

    # Distance from line (larger difference = higher confidence)
    diff = abs(predicted_total - betting_line)
    if diff > 12:
        confidence += 35
    elif diff > 10:
        confidence += 30
    elif diff > 7:
        confidence += 20
    elif diff > 5:
        confidence += 15
    elif diff > 3:
        confidence += 10
    else:
        confidence += 5

    # Recent form consistency
    if factors.get('recent_form_consistent', False):
        confidence += 10

    # Injury impact (if significant injuries, reduce confidence)
    if factors.get('injury_impact', 0) > 5:
        confidence -= 15

    # Pace consistency (lower variance = higher confidence)
    pace_variance = factors.get('pace_variance', 10)
    if pace_variance < 5:
        confidence += 10
    elif pace_variance < 8:
        confidence += 5
    else:
        confidence -= 5

    # Data quality (if we have complete stats, increase confidence)
    if factors.get('complete_data', True):
        confidence += 5

    # Cap confidence at 95%
    return max(40, min(confidence, 95))

def predict_game_total(home_data, away_data, betting_line=None, home_team_id=None, away_team_id=None, home_team_abbr=None, away_team_abbr=None, season='2025-26'):
    """
    Main prediction function for game total

    Args:
        home_data: Dictionary with home team's comprehensive data
                   Expected structure: {'stats': {...}, 'advanced': {...},
                                       'opponent': {...}, 'recent_games': [...]}
        away_data: Dictionary with away team's comprehensive data
        betting_line: Current betting O/U line (optional)
        home_team_id: Home team NBA ID (optional, for trend analysis)
        away_team_id: Away team NBA ID (optional, for trend analysis)
        home_team_abbr: Home team abbreviation (optional, for trend analysis)
        away_team_abbr: Away team abbreviation (optional, for trend analysis)
        season: Season string (default '2025-26')

    Returns:
        Dictionary with prediction details
    """
    try:
        # Check if data is valid
        if not home_data or not away_data:
            raise ValueError("Missing team data")

        # Safely extract stats with null checks
        home_stats = home_data.get('stats') or {}
        away_stats = away_data.get('stats') or {}
        home_advanced = home_data.get('advanced') or {}
        away_advanced = away_data.get('advanced') or {}
        home_opponent = home_data.get('opponent') or {}
        away_opponent = away_data.get('opponent') or {}

        # Validate critical data
        if not home_stats.get('overall') or not away_stats.get('overall'):
            raise ValueError("Missing team stats data - API may have failed")

        # Extract stats from new data structure
        home_stats_dict = {
            'overall': home_stats.get('overall', {}),
            'advanced': home_advanced,
            'opponent': home_opponent,
        }

        away_stats_dict = {
            'overall': away_stats.get('overall', {}),
            'advanced': away_advanced,
            'opponent': away_opponent,
        }

        # Get season pace
        home_season_pace = home_advanced.get('PACE', 100.0) if home_advanced else 100.0
        away_season_pace = away_advanced.get('PACE', 100.0) if away_advanced else 100.0

        # Calculate projected pace (factors in last 5 games + season average)
        # Also get blended pace for each team to display in factors
        home_pace = home_season_pace  # Default to season pace
        away_pace = away_season_pace

        if home_team_id and away_team_id:
            try:
                from api.utils.pace_projection import calculate_projected_pace, get_team_recent_pace

                # Get recent pace for both teams
                home_recent = get_team_recent_pace(home_team_id, season, n_games=5)
                away_recent = get_team_recent_pace(away_team_id, season, n_games=5)

                # Calculate blended pace for each team (40% season + 60% recent)
                if home_recent is not None:
                    home_pace = (home_season_pace * 0.4) + (home_recent * 0.6)
                if away_recent is not None:
                    away_pace = (away_season_pace * 0.4) + (away_recent * 0.6)

                # Calculate projected game pace
                game_pace = calculate_projected_pace(home_team_id, away_team_id, season)
                print(f'[prediction_engine] Using pace projection with recent form: {game_pace:.1f}')
            except Exception as e:
                print(f'[prediction_engine] Error calculating pace projection: {e}')
                # Fallback to old method
                game_pace = calculate_pace_projection(home_season_pace, away_season_pace)
        else:
            # Fallback if team IDs not provided
            game_pace = calculate_pace_projection(home_season_pace, away_season_pace)

        # ========================================================================
        # DEFENSE-FIRST ARCHITECTURE (Dec 2025 Refactor)
        # ========================================================================
        # STEP 1: Get defense-adjusted base PPG (NEW FOUNDATION)
        # This replaces the old rating-based baseline approach
        home_base_ppg = None
        away_base_ppg = None
        home_data_quality = 'fallback'
        away_data_quality = 'fallback'

        if home_team_id and away_team_id:
            try:
                from api.utils.defense_adjusted_scoring import get_defense_adjusted_ppg
                from api.utils.db_queries import get_team_stats_with_ranks

                # Get opponent defensive ranks
                home_stats_with_ranks = get_team_stats_with_ranks(home_team_id, season)
                away_stats_with_ranks = get_team_stats_with_ranks(away_team_id, season)

                if home_stats_with_ranks and away_stats_with_ranks:
                    home_def_rank = home_stats_with_ranks['stats'].get('def_rtg', {}).get('rank')
                    away_def_rank = away_stats_with_ranks['stats'].get('def_rtg', {}).get('rank')

                    # Get season PPG as fallback
                    home_season_ppg = home_stats.get('overall', {}).get('PTS', 115.0)
                    away_season_ppg = away_stats.get('overall', {}).get('PTS', 115.0)

                    # Get defense-adjusted PPG for home team vs away defense
                    home_base_ppg, home_data_quality = get_defense_adjusted_ppg(
                        team_id=home_team_id,
                        opponent_def_rank=away_def_rank,
                        is_home=True,
                        season=season,
                        fallback_ppg=home_season_ppg
                    )

                    # Get defense-adjusted PPG for away team vs home defense
                    away_base_ppg, away_data_quality = get_defense_adjusted_ppg(
                        team_id=away_team_id,
                        opponent_def_rank=home_def_rank,
                        is_home=False,
                        season=season,
                        fallback_ppg=away_season_ppg
                    )

                    # SAFETY CHECK: Blend with season average for limited data or significantly low values
                    # This prevents over-relying on small sample sizes or outlier historical data

                    if home_data_quality == 'limited':
                        # Always blend limited data (<3 games) with season average
                        original_home = home_base_ppg
                        home_base_ppg = home_season_ppg * 0.6 + home_base_ppg * 0.4
                        print(f'[prediction_engine] Home has limited data, blending: {original_home:.1f} → {home_base_ppg:.1f}')
                    elif home_data_quality == 'excellent' and home_base_ppg < home_season_ppg - 10:
                        # Excellent data but significantly low: blend 50/50 to avoid over-penalizing
                        original_home = home_base_ppg
                        home_base_ppg = home_season_ppg * 0.5 + home_base_ppg * 0.5
                        print(f'[prediction_engine] Home defense-adjusted significantly low, blending: {original_home:.1f} → {home_base_ppg:.1f}')

                    if away_data_quality == 'limited':
                        # Always blend limited data (<3 games) with season average
                        original_away = away_base_ppg
                        away_base_ppg = away_season_ppg * 0.6 + away_base_ppg * 0.4
                        print(f'[prediction_engine] Away has limited data, blending: {original_away:.1f} → {away_base_ppg:.1f}')
                    elif away_data_quality == 'excellent' and away_base_ppg < away_season_ppg - 10:
                        # Excellent data but significantly low: blend 50/50 to avoid over-penalizing
                        original_away = away_base_ppg
                        away_base_ppg = away_season_ppg * 0.5 + away_base_ppg * 0.5
                        print(f'[prediction_engine] Away defense-adjusted significantly low, blending: {original_away:.1f} → {away_base_ppg:.1f}')

                    print(f'[prediction_engine] Defense-adjusted base PPG:')
                    print(f'  Home: {home_base_ppg:.1f} ({home_data_quality} quality)')
                    print(f'  Away: {away_base_ppg:.1f} ({away_data_quality} quality)')

            except Exception as e:
                print(f'[prediction_engine] Error getting defense-adjusted base: {e}')
                # Will fall through to rating-based baseline

        # If defense-adjusted PPG not available, fall back to rating-based baseline
        if home_base_ppg is None or away_base_ppg is None:
            print('[prediction_engine] Using rating-based baseline (no defense context available)')

            # Use old baseline calculation as fallback
            home_base_ppg = calculate_team_scoring_with_profile(
                home_team_id, home_stats_dict, away_stats_dict, game_pace, is_home=True, season=season
            ) if home_team_id else calculate_team_scoring(home_stats_dict, away_stats_dict, game_pace, is_home=True)

            away_base_ppg = calculate_team_scoring_with_profile(
                away_team_id, away_stats_dict, home_stats_dict, game_pace, is_home=False, season=season
            ) if away_team_id else calculate_team_scoring(away_stats_dict, home_stats_dict, game_pace, is_home=False)

            home_data_quality = 'fallback'
            away_data_quality = 'fallback'

        # Start with defense-adjusted base PPG as foundation
        home_projected = home_base_ppg
        away_projected = away_base_ppg

        # STEP 2: Apply pace multiplier (small adjustment ~3%)
        league_avg_pace = 100.0
        home_pace_multiplier = 1.0
        away_pace_multiplier = 1.0

        if game_pace and game_pace > 0:
            # Calculate pace differential from league average
            pace_diff = game_pace - league_avg_pace

            # Convert to small multiplier (3% per 10 pace units)
            # Example: pace=105 (+5 from avg) -> multiplier=1.015 (1.5% boost)
            pace_multiplier_base = 1.0 + (pace_diff / 100.0) * 0.3

            # Get team-specific pace weights from profiles (if available)
            try:
                from api.utils.db_queries import get_team_profile
                home_profile = get_team_profile(home_team_id, season) if home_team_id else None
                away_profile = get_team_profile(away_team_id, season) if away_team_id else None

                home_pace_weight = home_profile['pace_weight'] if home_profile else 1.0
                away_pace_weight = away_profile['pace_weight'] if away_profile else 1.0
            except Exception as e:
                home_pace_weight = 1.0
                away_pace_weight = 1.0

            # Apply team-specific pace sensitivity
            home_pace_multiplier = 1.0 + (pace_multiplier_base - 1.0) * home_pace_weight
            away_pace_multiplier = 1.0 + (pace_multiplier_base - 1.0) * away_pace_weight

            home_projected *= home_pace_multiplier
            away_projected *= away_pace_multiplier

            print(f'[prediction_engine] Pace multiplier: {pace_multiplier_base:.4f} (game_pace: {game_pace:.1f}, avg: {league_avg_pace:.1f})')
            print(f'  Home: {home_pace_multiplier:.4f} -> {home_projected:.1f} PPG')
            print(f'  Away: {away_pace_multiplier:.4f} -> {away_projected:.1f} PPG')

        # STEP 3: Blend recent form (moderate adjustment ~30%)
        RECENT_FORM_BLEND_WEIGHT = 0.30
        home_form_adjustment = 0.0
        away_form_adjustment = 0.0

        # Calculate recent average PPG for home team
        if home_data.get('recent_games'):
            recent_games = home_data['recent_games']
            if len(recent_games) > 0:
                home_recent_ppg = sum(g.get('PTS', 0) for g in recent_games) / len(recent_games)
                home_before_blend = home_projected

                # Blend: 70% base + 30% recent
                home_projected = home_projected * (1 - RECENT_FORM_BLEND_WEIGHT) + home_recent_ppg * RECENT_FORM_BLEND_WEIGHT

                # Cap total adjustment at ±5 pts to prevent wild swings
                raw_adjustment = home_projected - home_before_blend
                home_form_adjustment = max(-5.0, min(5.0, raw_adjustment))
                home_projected = home_before_blend + home_form_adjustment

                print(f'[prediction_engine] Home recent form blend: {home_recent_ppg:.1f} recent -> {home_form_adjustment:+.1f} pts adjustment')

        # Calculate recent average PPG for away team
        if away_data.get('recent_games'):
            recent_games = away_data['recent_games']
            if len(recent_games) > 0:
                away_recent_ppg = sum(g.get('PTS', 0) for g in recent_games) / len(recent_games)
                away_before_blend = away_projected

                # Blend: 70% base + 30% recent
                away_projected = away_projected * (1 - RECENT_FORM_BLEND_WEIGHT) + away_recent_ppg * RECENT_FORM_BLEND_WEIGHT

                # Cap total adjustment
                raw_adjustment = away_projected - away_before_blend
                away_form_adjustment = max(-5.0, min(5.0, raw_adjustment))
                away_projected = away_before_blend + away_form_adjustment

                print(f'[prediction_engine] Away recent form blend: {away_recent_ppg:.1f} recent -> {away_form_adjustment:+.1f} pts adjustment')

        # Apply trend-based adjustments (new deterministic layer)
        home_last5_trends = None
        away_last5_trends = None
        trend_adjustment = None

        if home_team_id and away_team_id and home_team_abbr and away_team_abbr:
            try:
                from api.utils.last_5_trends import get_last_5_trends
                from api.utils.trend_adjustment import compute_trend_adjustment

                # Get last 5 trends for both teams
                home_last5_trends = get_last_5_trends(home_team_id, home_team_abbr, season)
                away_last5_trends = get_last_5_trends(away_team_id, away_team_abbr, season)

                # Compute trend adjustment
                trend_adjustment = compute_trend_adjustment(
                    home_trends=home_last5_trends,
                    away_trends=away_last5_trends,
                    base_home_score=home_projected,
                    base_away_score=away_projected,
                    base_total=home_projected + away_projected
                )

                # Apply adjustments
                home_projected = trend_adjustment['adjusted_home']
                away_projected = trend_adjustment['adjusted_away']

            except Exception as e:
                print(f'[prediction_engine] Error computing trend adjustment: {e}')
                # Continue without trend adjustment on error

        # REMOVED: Old defense adjustment code (now handled in Step 1 as foundation)
        # Defense-adjusted scoring is now the BASE, not a late 30% adjustment
        defense_adjustment_home = None
        defense_adjustment_away = None

        # REMOVED: Pace effect adjustments (to avoid double-counting with Step 2 pace multiplier)
        # Pace is now handled as a small multiplier (~3%) applied to defense-adjusted base
        pace_effect_home = None
        pace_effect_away = None

        # Total prediction
        predicted_total = round(home_projected + away_projected, 1)

        # Determine recommendation
        if betting_line is None:
            betting_line = predicted_total

        diff = predicted_total - betting_line

        # Calculate pace consistency for confidence
        pace_variance = calculate_pace_consistency(
            home_data.get('recent_games', []),
            away_data.get('recent_games', [])
        )

        if diff > 4:
            recommendation = "OVER"
            confidence_factors = {
                'recent_form_consistent': pace_variance < 8,
                'pace_variance': pace_variance,
                'injury_impact': 0,
                'complete_data': True,
            }
        elif diff < -4:
            recommendation = "UNDER"
            confidence_factors = {
                'recent_form_consistent': pace_variance < 8,
                'pace_variance': pace_variance,
                'injury_impact': 0,
                'complete_data': True,
            }
        else:
            recommendation = "NO BET"
            confidence_factors = {
                'recent_form_consistent': False,
                'pace_variance': pace_variance,
                'injury_impact': 0,
                'complete_data': True,
            }

        confidence = calculate_confidence(predicted_total, betting_line, confidence_factors)

        # Get additional stats for display (with safe access)
        home_ppg = home_stats.get('overall', {}).get('PTS', 0)
        away_ppg = away_stats.get('overall', {}).get('PTS', 0)
        home_ortg = home_advanced.get('OFF_RATING', 0) if home_advanced else 0
        away_ortg = away_advanced.get('OFF_RATING', 0) if away_advanced else 0

        result = {
            'predicted_total': predicted_total,
            'betting_line': betting_line,
            'recommendation': recommendation,
            'confidence': confidence,
            'breakdown': {
                'home_projected': round(home_projected, 1),
                'away_projected': round(away_projected, 1),
                'game_pace': round(game_pace, 1),
                'difference': round(diff, 1),
                'home_form_adjustment': round(home_form_adjustment, 1),
                'away_form_adjustment': round(away_form_adjustment, 1),
                # NEW FIELDS: Defense-first architecture transparency
                'home_base_ppg': round(home_base_ppg, 1) if home_base_ppg else None,
                'away_base_ppg': round(away_base_ppg, 1) if away_base_ppg else None,
                'home_data_quality': home_data_quality,
                'away_data_quality': away_data_quality,
                'home_pace_multiplier': round(home_pace_multiplier, 4) if home_pace_multiplier != 1.0 else None,
                'away_pace_multiplier': round(away_pace_multiplier, 4) if away_pace_multiplier != 1.0 else None,
            },
            'factors': {
                'home_ppg': round(home_ppg, 1),
                'away_ppg': round(away_ppg, 1),
                'home_ortg': round(home_ortg, 1),
                'away_ortg': round(away_ortg, 1),
                'home_pace': round(home_pace, 1),
                'away_pace': round(away_pace, 1),
                'game_pace': round(game_pace, 1),
                'pace_variance': round(pace_variance, 1),
            }
        }

        # Add trend data if available
        if home_last5_trends:
            result['home_last5_trends'] = home_last5_trends
        if away_last5_trends:
            result['away_last5_trends'] = away_last5_trends
        if trend_adjustment:
            result['trend_adjustment'] = trend_adjustment

        # Add defense adjustment data if available
        if defense_adjustment_home:
            result['defense_adjustment_home'] = defense_adjustment_home
        if defense_adjustment_away:
            result['defense_adjustment_away'] = defense_adjustment_away

        # Add pace effect data if available
        if pace_effect_home:
            result['pace_effect_home'] = pace_effect_home
        if pace_effect_away:
            result['pace_effect_away'] = pace_effect_away

        # Add team profile explanations
        if home_team_id and away_team_id:
            try:
                from api.utils.profile_explanation import explain_team_prediction
                result['home_team_explanation'] = explain_team_prediction(home_team_id, season)
                result['away_team_explanation'] = explain_team_prediction(away_team_id, season)
            except Exception as e:
                print(f'[prediction_engine] Error generating explanations: {e}')
                # Continue without explanations

        return result

    except Exception as e:
        print(f"Error in predict_game_total: {str(e)}")
        # Return a safe default prediction
        return {
            'predicted_total': betting_line if betting_line else 220.0,
            'betting_line': betting_line if betting_line else 220.0,
            'recommendation': 'NO BET',
            'confidence': 50,
            'breakdown': {
                'home_projected': 110.0,
                'away_projected': 110.0,
                'game_pace': 100.0,
                'difference': 0.0,
                'home_form_adjustment': 0.0,
                'away_form_adjustment': 0.0,
            },
            'factors': {
                'home_ppg': 110.0,
                'away_ppg': 110.0,
                'home_ortg': 110.0,
                'away_ortg': 110.0,
                'home_pace': 100.0,
                'away_pace': 100.0,
                'game_pace': 100.0,
                'pace_variance': 10.0,
            },
            'error': str(e)
        }
