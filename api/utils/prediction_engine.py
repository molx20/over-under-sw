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

        # Get pace from advanced stats (with fallback)
        home_pace = home_advanced.get('PACE', 100.0) if home_advanced else 100.0
        away_pace = away_advanced.get('PACE', 100.0) if away_advanced else 100.0

        # Calculate projected pace
        game_pace = calculate_pace_projection(home_pace, away_pace)

        # Calculate expected scoring for each team
        home_projected = calculate_team_scoring(home_stats_dict, away_stats_dict, game_pace, is_home=True)
        away_projected = calculate_team_scoring(away_stats_dict, home_stats_dict, game_pace, is_home=False)

        # Apply recent form adjustments
        home_form = calculate_recent_form_factor(home_data.get('recent_games', []))
        away_form = calculate_recent_form_factor(away_data.get('recent_games', []))

        home_projected += home_form
        away_projected += away_form

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
                'home_form_adjustment': round(home_form, 1),
                'away_form_adjustment': round(away_form, 1),
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
