# Opponent-Conditioned Similarity - Implementation Summary

## Overview
Implemented opponent-conditioned similarity system that computes team playstyle similarity based on specific opponent archetypes.

## What Was Implemented

### 1. Database Schema Extensions
**File**: `api/utils/db_schema_similarity.py`

Extended two tables with conditional similarity support:

**team_feature_vectors**:
- `window_mode` TEXT: 'season', 'last20', or 'last10'  
- `opponent_cluster_id` INTEGER: NULL = global, 1-6 = conditional
- `games_used` INTEGER: Number of games used to compute vector
- UNIQUE constraint: `(team_id, season, window_mode, opponent_cluster_id)`

**team_similarity_scores**:
- `window_mode` TEXT: 'season', 'last20', or 'last10'
- `opponent_cluster_id` INTEGER: NULL = global, 1-6 = conditional  
- UNIQUE constraint: `(team_id, similar_team_id, season, window_mode, opponent_cluster_id)`

### 2. Core Functions
**File**: `api/utils/team_similarity.py`

#### `compute_team_feature_vector_vs_cluster(team_id, season, window_mode, opponent_cluster_id)`
- Computes 20D feature vector using ONLY games vs specific opponent cluster type
- Filters by opponent cluster assignment from `team_cluster_assignments`
- Returns None if <5 games (insufficient sample)
- Returns dict with `raw_features`, `games_used`, `date_range`

#### `refresh_conditional_vectors(season, window_mode)`
- Iterates through all 6 opponent cluster IDs
- Computes conditional vectors for all teams (where they have 5+ games)
- Normalizes vectors SEPARATELY within each cluster lens (critical!)
- Stores in `team_feature_vectors` with metadata

#### `compute_all_similarity_scores_conditional(season, window_mode)`
- For each opponent cluster, retrieves all conditional vectors
- Computes pairwise similarity ONLY among teams with vectors for that cluster
- Stores top 5 similar teams per team in `team_similarity_scores`

#### `get_team_similarity_ranking(team_id, season, limit, opponent_cluster_id, window_mode)`
- **Extended existing function** to support conditional similarity
- If `opponent_cluster_id` is None: Returns global similarity
- If `opponent_cluster_id` is set: Returns conditional similarity vs that opponent type
- Backward compatible with existing usage

#### `validate_conditional_similarity(season, window_mode)`
- Validates vectors, scores, and retrieval
- Checks data integrity and JSON structure
- Returns comprehensive validation report

## How to Use

### Initial Setup (One-Time)
```python
from api.utils.team_similarity import refresh_conditional_vectors, compute_all_similarity_scores_conditional
from api.utils.db_schema_similarity import initialize_schema

# 1. Initialize schema (adds new columns)
initialize_schema()

# 2. Compute conditional feature vectors  
refresh_conditional_vectors(season='2025-26', window_mode='season')

# 3. Compute conditional similarity scores
compute_all_similarity_scores_conditional(season='2025-26', window_mode='season')
```

### Usage in Matchup Analysis
```python
from api.utils.team_similarity import get_team_similarity_ranking, get_team_cluster_assignment

# Get opponent's cluster
opponent_cluster = get_team_cluster_assignment(opponent_team_id, season='2025-26')
opponent_cluster_id = opponent_cluster['primary_cluster']['id']

# Get conditional similarity: "Teams similar to X when playing vs opponent archetype Y"
similar_teams = get_team_similarity_ranking(
    team_id=my_team_id,
    season='2025-26',
    limit=5,
    opponent_cluster_id=opponent_cluster_id,  # Conditional!
    window_mode='season'
)

# Fallback to global similarity if no conditional data
if not similar_teams:
    similar_teams = get_team_similarity_ranking(
        team_id=my_team_id,
        season='2025-26',
        limit=5,
        opponent_cluster_id=None  # Global
    )
```

### Validation
```python
from api.utils.team_similarity import validate_conditional_similarity

# Run validation checks
validate_conditional_similarity(season='2025-26', window_mode='season')
```

## Current Status (Dec 28, 2025)

### ✅ Completed
- [x] Database schema extended
- [x] Conditional vector computation  
- [x] Conditional similarity scoring
- [x] Retrieval logic updated
- [x] Validation function created
- [x] All validation checks passing

### ⏳ Pending
- [ ] Wire into matchup prediction endpoints (`server.py`)
- [ ] Update frontend to display conditional similarity
- [ ] Add window mode support ('last20', 'last10')

## Data Summary (2025-26 Season)

**Conditional Vectors**:
- Cluster 2 (Paint Dominators): 2 teams
- Cluster 3 (Three-Point Hunters): 30 teams (all teams have data!)
- Cluster 5 (Balanced High-Assist): 4 teams
- Cluster 6 (ISO-Heavy): 1 team (skipped in scoring)

**Conditional Similarity Scores**:
- 164 total similarity scores stored
- Covers 36 unique teams
- Average similarity: 76.1% for Cluster 3 (most common)

## Key Design Decisions

1. **Separate Normalization Per Cluster**
   - Each opponent cluster has its own min/max normalization bounds
   - Teams are comparable ONLY within the same conditional lens
   - Prevents mixing global and conditional vectors

2. **Minimum Sample Size**
   - Requires 5+ games vs opponent cluster type
   - Graceful fallback to global similarity when insufficient data
   - Prevents noisy/unreliable conditional vectors

3. **Backward Compatibility**
   - `get_team_similarity_ranking()` defaults to global similarity (opponent_cluster_id=None)
   - Existing code continues to work without changes
   - Conditional similarity is opt-in via parameters

4. **Deterministic & Pre-Computed**
   - All vectors and scores pre-computed and stored
   - No per-request computation
   - Fast retrieval via indexed queries

## Testing

Run comprehensive validation:
```bash
cd "/Users/malcolmlittle/NBA OVER UNDER SW"
python3 -c "from api.utils.team_similarity import validate_conditional_similarity; validate_conditional_similarity()"
```

Expected output: All checks pass (✓)

## Files Modified

1. `api/utils/db_schema_similarity.py` - Schema extensions
2. `api/utils/team_similarity.py` - Core implementation (4 new functions, 1 updated)

## Next Steps

To complete the implementation:

1. **Update `server.py` endpoints**:
   - Modify game prediction endpoints to use conditional similarity
   - Pass opponent cluster ID to similarity ranking calls

2. **Frontend updates**:
   - Display "Similar Teams vs [Opponent Archetype]" instead of generic similar teams
   - Show conditional similarity context in UI

3. **Add window mode support**:
   - Run `refresh_conditional_vectors()` with 'last20' and 'last10'
   - Allow users to toggle between full season and recent performance

