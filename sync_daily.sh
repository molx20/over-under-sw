#!/bin/bash
# Daily NBA Data Sync Script
# Runs at 3 AM MT to fetch today's games and update Last 5 trends

cd "/Users/malcolmlittle/NBA OVER UNDER SW"

# Log file with date
LOG_FILE="/Users/malcolmlittle/NBA OVER UNDER SW/logs/sync_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "=== NBA Data Sync Started: $(date) ===" >> "$LOG_FILE" 2>&1

# Run the sync
python3 << 'PYTHON_SCRIPT' >> "$LOG_FILE" 2>&1
import sys
sys.path.insert(0, '/Users/malcolmlittle/NBA OVER UNDER SW')

from api.utils.sync_nba_data import sync_all

print("Starting daily sync...")
result = sync_all(season='2025-26', triggered_by='cron')
print(f"\nSync completed!")
print(f"  Success: {result['success']}")
print(f"  Game Logs: {result['game_logs']}")
print(f"  Today's Games: {result['todays_games']}")
print(f"  Total Records: {result['total_records']}")
if result.get('errors'):
    print(f"  Errors: {', '.join(result['errors'])}")
PYTHON_SCRIPT

echo "=== NBA Data Sync Completed: $(date) ===" >> "$LOG_FILE" 2>&1

# Keep only last 30 days of logs
find "/Users/malcolmlittle/NBA OVER UNDER SW/logs" -name "sync_*.log" -mtime +30 -delete 2>/dev/null

exit 0
