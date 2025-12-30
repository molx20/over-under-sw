#!/usr/bin/env python3
"""
Quick validation script for archetype system
"""
import sys
import os

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from utils.archetype_classifier import assign_all_team_archetypes
from utils.archetype_validation import validate_archetypes, print_validation_report

def main():
    print("=" * 80)
    print("ARCHETYPE SYSTEM VALIDATION TEST")
    print("=" * 80)
    print()

    try:
        # Assign archetypes
        print("Step 1: Assigning archetypes to all teams...")
        assignments = assign_all_team_archetypes('2025-26')
        print(f"✓ Successfully assigned archetypes to {len(assignments)} teams")
        print()

        # Validate
        print("Step 2: Running validation...")
        validation_results = validate_archetypes(assignments, '2025-26')
        print("✓ Validation complete")
        print()

        # Print report
        print_validation_report(validation_results)

        # Check for errors
        if validation_results['warnings']:
            print("\n⚠️  WARNINGS DETECTED - Review archetype distributions above")
            return 1
        else:
            print("\n✓ ALL VALIDATION CHECKS PASSED")
            return 0

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
