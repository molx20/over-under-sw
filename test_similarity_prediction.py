"""
Test Similarity-Based Predictions Integration

Tests that similarity adjustments are properly integrated into the prediction engine.
"""

import requests
import json

# Test with Orlando Magic (1610612753) vs Minnesota Timberwolves (1610612750)
# Orlando = Cluster 1 (Elite Pace Pushers)
# Minnesota = Cluster 3 (Three-Point Hunters)

def test_similarity_prediction():
    """Test prediction with similarity data"""

    print("="*70)
    print("TESTING SIMILARITY-BASED PREDICTION INTEGRATION")
    print("="*70)

    # Assuming server is running on localhost:8080
    url = "http://localhost:8080/api/predict"

    # Test matchup: Orlando Magic (home) vs Minnesota Timberwolves (away)
    payload = {
        "home_team_id": 1610612753,  # Orlando Magic - Cluster 1 (Elite Pace Pushers)
        "away_team_id": 1610612750,  # Minnesota Timberwolves - Cluster 3 (Three-Point Hunters)
        "betting_line": 220.5
    }

    print(f"\nTest Matchup: ORL ({payload['home_team_id']}) vs MIN ({payload['away_team_id']})")
    print(f"Betting Line: {payload['betting_line']}")
    print("\nExpected Clusters:")
    print("  - Home (ORL): Cluster 1 (Elite Pace Pushers)")
    print("  - Away (MIN): Cluster 3 (Three-Point Hunters)")
    print("\nExpected Adjustments:")
    print("  - Pace: +1.5 (Elite pace pusher influence)")
    print("  - Home Scoring: ~+0.75 (Pace pusher advantage)")
    print("  - Away Scoring: ~+0.5 (Perimeter advantage)")
    print("\n" + "-"*70)

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code != 200:
            print(f"\n❌ ERROR: Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False

        result = response.json()

        # Check if prediction data is present
        if 'prediction' not in result:
            print("\n❌ FAIL: No 'prediction' field in response")
            print(f"Available keys: {list(result.keys())}")
            return False

        # The prediction is wrapped in a list, get the first element
        if isinstance(result['prediction'], list) and len(result['prediction']) > 0:
            prediction = result['prediction'][0]
        else:
            prediction = result['prediction']

        # Check if similarity data is present
        if 'similarity' not in prediction:
            print("\n❌ FAIL: No 'similarity' field in prediction result")
            print(f"Available prediction keys: {list(prediction.keys())}")
            return False

        similarity = prediction['similarity']

        print(f"\n✅ SUCCESS: Similarity data found in prediction result")
        print(f"\nPrediction Results:")
        print(f"  Predicted Total: {prediction.get('predicted_total', 'N/A')}")
        print(f"  Betting Line: {prediction.get('betting_line', 'N/A')}")
        print(f"  Recommendation: {prediction.get('recommendation', 'N/A')}")

        print(f"\nSimilarity Data:")
        print(f"  Matchup Type: {similarity.get('matchup_type', 'N/A')}")

        if 'home_cluster' in similarity:
            home_cluster = similarity['home_cluster']
            print(f"\n  Home Team Cluster:")
            print(f"    ID: {home_cluster.get('id', 'N/A')}")
            print(f"    Name: {home_cluster.get('name', 'N/A')}")
            print(f"    Description: {home_cluster.get('description', 'N/A')}")
            print(f"    Distance to Centroid: {home_cluster.get('distance_to_centroid', 'N/A')}")

        if 'away_cluster' in similarity:
            away_cluster = similarity['away_cluster']
            print(f"\n  Away Team Cluster:")
            print(f"    ID: {away_cluster.get('id', 'N/A')}")
            print(f"    Name: {away_cluster.get('name', 'N/A')}")
            print(f"    Description: {away_cluster.get('description', 'N/A')}")
            print(f"    Distance to Centroid: {away_cluster.get('distance_to_centroid', 'N/A')}")

        if 'adjustments' in similarity:
            adjustments = similarity['adjustments']
            print(f"\n  Cluster Adjustments Applied:")
            print(f"    Pace: {adjustments.get('pace_adjustment', 0):+.1f} ({adjustments.get('pace_explanation', 'N/A')})")
            print(f"    Home Scoring: {adjustments.get('home_scoring_adjustment', 0):+.1f}")
            print(f"    Away Scoring: {adjustments.get('away_scoring_adjustment', 0):+.1f}")
            print(f"    Scoring Reason: {adjustments.get('scoring_explanation', 'N/A')}")
            print(f"    Home Paint/Perimeter: {adjustments.get('home_paint_perimeter_adjustment', 0):+.1f}")
            print(f"    Away Paint/Perimeter: {adjustments.get('away_paint_perimeter_adjustment', 0):+.1f}")
            print(f"    Paint/Perimeter Reason: {adjustments.get('paint_perimeter_explanation', 'N/A')}")

        if 'home_similar_teams' in similarity and similarity['home_similar_teams']:
            print(f"\n  Home Team Similar To:")
            for team in similarity['home_similar_teams'][:3]:
                print(f"    - {team['team_name']} ({team['team_abbreviation']}): {team['similarity_score']}% similar")

        if 'away_similar_teams' in similarity and similarity['away_similar_teams']:
            print(f"\n  Away Team Similar To:")
            for team in similarity['away_similar_teams'][:3]:
                print(f"    - {team['team_name']} ({team['team_abbreviation']}): {team['similarity_score']}% similar")

        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)

        return True

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server at http://localhost:8080")
        print("Make sure the server is running: python3 server.py")
        return False
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_similarity_prediction()
    exit(0 if success else 1)
