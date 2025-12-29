/**
 * Unit Tests for Decision Engine
 *
 * Run with: node --experimental-modules src/utils/decisionEngine.test.js
 * Or with a testing framework like Vitest/Jest
 */

import { makeDecision } from './decisionEngine.js'

// Test helper
let passedTests = 0
let failedTests = 0

function assertEquals(actual, expected, testName) {
  if (actual === expected) {
    console.log(`✅ ${testName}`)
    passedTests++
  } else {
    console.error(`❌ ${testName}`)
    console.error(`   Expected: ${expected}`)
    console.error(`   Actual: ${actual}`)
    failedTests++
  }
}

function assertRange(actual, min, max, testName) {
  if (actual >= min && actual <= max) {
    console.log(`✅ ${testName}`)
    passedTests++
  } else {
    console.error(`❌ ${testName}`)
    console.error(`   Expected: ${min} <= ${actual} <= ${max}`)
    failedTests++
  }
}

function assertContains(array, value, testName) {
  if (array && array.some(item => item.text && item.text.includes(value))) {
    console.log(`✅ ${testName}`)
    passedTests++
  } else {
    console.error(`❌ ${testName}`)
    console.error(`   Expected reasoning to contain: "${value}"`)
    failedTests++
  }
}

// Test 1: Strong OVER signal (2 greens + competitive game)
console.log('\n--- Test 1: Strong OVER Signal ---')
const test1Drivers = {
  ftPoints: { value: 42, status: 'green', target: '38+' },
  paintPoints: { value: 71, status: 'green', target: '68+' },
  efg: { value: 56, status: 'yellow', target: '59%+' }
}
const test1Result = makeDecision(
  test1Drivers,
  { cluster_name: 'Elite Pace Pushers', confidence: 'high', sample_size: 35 },
  { index: 4.0, label: 'Stable' },
  { label: 'Competitive', rating_gap: 3.2 }
)
assertEquals(test1Result.call, 'OVER', 'Should recommend OVER with 2 greens')
assertRange(test1Result.confidence, 70, 90, 'Confidence should be in 70-90 range')
// 75% confidence is MEDIUM (60-79%), not HIGH (80+)
if (test1Result.confidenceLabel === 'MEDIUM' || test1Result.confidenceLabel === 'HIGH') {
  console.log('✅ Should have MEDIUM or HIGH confidence label')
  passedTests++
} else {
  console.error(`❌ Should have MEDIUM or HIGH confidence label, got ${test1Result.confidenceLabel}`)
  failedTests++
}
// Check reasoning is not empty
if (test1Result.reasoning && test1Result.reasoning.length > 0) {
  console.log('✅ Should have reasoning bullets')
  passedTests++
} else {
  console.error('❌ Should have reasoning bullets')
  failedTests++
}

// Test 2: Strong UNDER signal (2 reds + not high FT)
console.log('\n--- Test 2: Strong UNDER Signal ---')
const test2Drivers = {
  ftPoints: { value: 30, status: 'red', target: '38+' },
  paintPoints: { value: 58, status: 'red', target: '68+' },
  efg: { value: 54, status: 'yellow', target: '59%+' }
}
const test2Result = makeDecision(
  test2Drivers,
  {},
  { index: 3.5, label: 'Stable' },
  { label: 'Competitive', rating_gap: 2.1 }
)
assertEquals(test2Result.call, 'UNDER', 'Should recommend UNDER with 2 reds')
assertRange(test2Result.confidence, 65, 85, 'Confidence should be MEDIUM-HIGH')

// Test 3: Mixed signals -> PASS
console.log('\n--- Test 3: Mixed Signals (PASS) ---')
const test3Drivers = {
  ftPoints: { value: 40, status: 'green', target: '38+' },
  paintPoints: { value: 58, status: 'red', target: '68+' },
  efg: { value: 56, status: 'yellow', target: '59%+' }
}
const test3Result = makeDecision(
  test3Drivers,
  {},
  { index: 5.0, label: 'Swingy' },
  { label: 'Competitive', rating_gap: 4.0 }
)
assertEquals(test3Result.call, 'PASS', 'Should PASS with mixed signals')
assertRange(test3Result.confidence, 30, 60, 'Confidence should be LOW-MEDIUM')

// Test 4: All yellows -> PASS
console.log('\n--- Test 4: All Yellow Signals (PASS) ---')
const test4Drivers = {
  ftPoints: { value: 35, status: 'yellow', target: '38+' },
  paintPoints: { value: 64, status: 'yellow', target: '68+' },
  efg: { value: 56, status: 'yellow', target: '59%+' }
}
const test4Result = makeDecision(
  test4Drivers,
  {},
  { index: 4.5, label: 'Stable' },
  { label: 'Competitive', rating_gap: 3.0 }
)
assertEquals(test4Result.call, 'PASS', 'Should PASS with all yellow signals')
assertRange(test4Result.confidence, 30, 60, 'Confidence should be LOW-MEDIUM')

// Test 5: Archetype boost works
console.log('\n--- Test 5: Archetype Confidence Boost ---')
const test5Drivers = {
  ftPoints: { value: 42, status: 'green', target: '38+' },
  paintPoints: { value: 71, status: 'green', target: '68+' },
  efg: { value: 60, status: 'green', target: '59%+' }
}
const test5WithArchetype = makeDecision(
  test5Drivers,
  { cluster_name: 'Elite Matchup', confidence: 'high', sample_size: 40 },
  { index: 3.0, label: 'Stable' },
  { label: 'Competitive', rating_gap: 2.0 }
)
const test5WithoutArchetype = makeDecision(
  test5Drivers,
  { cluster_name: 'Unknown', confidence: 'low', sample_size: 0 },
  { index: 3.0, label: 'Stable' },
  { label: 'Competitive', rating_gap: 2.0 }
)
console.log(`   With archetype: ${test5WithArchetype.confidence}%`)
console.log(`   Without archetype: ${test5WithoutArchetype.confidence}%`)
if (test5WithArchetype.confidence > test5WithoutArchetype.confidence) {
  console.log('✅ Archetype boost increases confidence')
  passedTests++
} else {
  console.error('❌ Archetype boost should increase confidence')
  failedTests++
}

// Test 6: Blowout risk penalty works
console.log('\n--- Test 6: Blowout Risk Penalty ---')
const test6Drivers = {
  ftPoints: { value: 42, status: 'green', target: '38+' },
  paintPoints: { value: 71, status: 'green', target: '68+' },
  efg: { value: 60, status: 'green', target: '59%+' }
}
const test6Competitive = makeDecision(
  test6Drivers,
  {},
  { index: 3.0, label: 'Stable' },
  { label: 'Competitive', rating_gap: 3.0 }
)
const test6Blowout = makeDecision(
  test6Drivers,
  {},
  { index: 3.0, label: 'Stable' },
  { label: 'Blowout Risk', rating_gap: 12.0 }
)
console.log(`   Competitive: ${test6Competitive.confidence}% (${test6Competitive.call})`)
console.log(`   Blowout Risk: ${test6Blowout.confidence}% (${test6Blowout.call})`)
if (test6Blowout.call === 'PASS' || test6Blowout.confidence < test6Competitive.confidence) {
  console.log('✅ Blowout risk reduces OVER confidence or changes to PASS')
  passedTests++
} else {
  console.error('❌ Blowout risk should reduce OVER confidence')
  failedTests++
}

// Test 7: Volatility adjustment works
console.log('\n--- Test 7: High Volatility Penalty ---')
const test7Drivers = {
  ftPoints: { value: 42, status: 'green', target: '38+' },
  paintPoints: { value: 71, status: 'green', target: '68+' },
  efg: { value: 56, status: 'yellow', target: '59%+' }
}
const test7Stable = makeDecision(
  test7Drivers,
  {},
  { index: 2.5, label: 'Stable' },
  { label: 'Competitive', rating_gap: 3.0 }
)
const test7Wild = makeDecision(
  test7Drivers,
  {},
  { index: 8.0, label: 'Wild' },
  { label: 'Competitive', rating_gap: 3.0 }
)
console.log(`   Stable volatility: ${test7Stable.confidence}%`)
console.log(`   Wild volatility: ${test7Wild.confidence}%`)
if (test7Wild.confidence < test7Stable.confidence) {
  console.log('✅ High volatility reduces confidence')
  passedTests++
} else {
  console.error('❌ High volatility should reduce confidence')
  failedTests++
}

// Test 8: 3 greens -> Strong OVER
console.log('\n--- Test 8: Perfect OVER Setup (3 Greens) ---')
const test8Drivers = {
  ftPoints: { value: 45, status: 'green', target: '38+' },
  paintPoints: { value: 75, status: 'green', target: '68+' },
  efg: { value: 62, status: 'green', target: '59%+' }
}
const test8Result = makeDecision(
  test8Drivers,
  { cluster_name: 'Elite Matchup', confidence: 'high', sample_size: 35 },
  { index: 2.0, label: 'Stable' },
  { label: 'Competitive', rating_gap: 1.5 }
)
assertEquals(test8Result.call, 'OVER', 'Should recommend OVER with 3 greens')
assertRange(test8Result.confidence, 80, 100, 'Confidence should be VERY HIGH')

// Test 9: 3 reds -> Strong UNDER
console.log('\n--- Test 9: Perfect UNDER Setup (3 Reds) ---')
const test9Drivers = {
  ftPoints: { value: 28, status: 'red', target: '38+' },
  paintPoints: { value: 55, status: 'red', target: '68+' },
  efg: { value: 50, status: 'red', target: '59%+' }
}
const test9Result = makeDecision(
  test9Drivers,
  {},
  { index: 3.0, label: 'Stable' },
  { label: 'Competitive', rating_gap: 2.0 }
)
assertEquals(test9Result.call, 'UNDER', 'Should recommend UNDER with 3 reds')
assertRange(test9Result.confidence, 75, 95, 'Confidence should be HIGH')

// Test 10: Edge case - Missing data
console.log('\n--- Test 10: Graceful Handling of Missing Data ---')
const test10Result = makeDecision(
  test1Drivers,
  undefined,
  undefined,
  undefined
)
if (test10Result.call && test10Result.confidence && test10Result.reasoning) {
  console.log('✅ Handles missing archetype/volatility/margin data gracefully')
  passedTests++
} else {
  console.error('❌ Should handle missing data without crashing')
  failedTests++
}

// Summary
console.log('\n' + '='.repeat(50))
console.log(`TEST SUMMARY: ${passedTests} passed, ${failedTests} failed`)
console.log('='.repeat(50))

if (failedTests > 0) {
  process.exit(1)
}
