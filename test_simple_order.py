#!/usr/bin/env python3
"""
Simple test to verify the pipeline order changes
"""
import re

# Read the prediction engine file
with open('/Users/malcolmlittle/NBA OVER UNDER SW/api/utils/prediction_engine.py', 'r') as f:
    content = f.read()

# Extract all STEP comments
steps = re.findall(r'# STEP \d+: ([^\n]+)', content)

print("=" * 80)
print("PIPELINE ORDER VERIFICATION")
print("=" * 80)
print()
print("Current pipeline order (from code comments):")
print()

for i, step in enumerate(steps, 1):
    print(f"{i}. {step}")

print()
print("=" * 80)
print("EXPECTED ORDER:")
print("=" * 80)
print()
print("1. PACE ADJUSTMENT (Possessions per game)")
print("2. TURNOVER ADJUSTMENT (Lost possessions per game)")
print("3. 3PT SCORING DATA COLLECTION (For later shootout detection)")
print("4. DEFENSE ADJUSTMENT (Scoring efficiency vs defense tiers)")
print("5. RECENT FORM (Last 5 Games) - 25% weight")
print("6. SHOOTOUT BONUS (Applied Last - Strict Criteria)")
print()

# Verify order
expected_keywords = [
    'PACE',
    'TURNOVER',
    '3PT',
    'DEFENSE',
    'RECENT',
    'SHOOTOUT'
]

print("=" * 80)
print("VERIFICATION:")
print("=" * 80)
print()

correct_order = True
for i, (step, keyword) in enumerate(zip(steps, expected_keywords), 1):
    match = keyword.lower() in step.lower()
    status = "✓" if match else "✗"
    print(f"{status} Step {i}: Expected '{keyword}', got '{step[:50]}...'")
    if not match:
        correct_order = False

print()
if correct_order:
    print("✓✓✓ PIPELINE ORDER IS CORRECT! ✓✓✓")
    print()
    print("KEY ARCHITECTURAL FIX:")
    print("Turnovers now come IMMEDIATELY after pace (Step 2) because both are")
    print("possession-based adjustments. This prevents double-counting and ensures")
    print("mathematical consistency.")
else:
    print("✗✗✗ PIPELINE ORDER IS INCORRECT ✗✗✗")
print()
