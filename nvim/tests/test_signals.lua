package.path = '../lua/?.lua;../lua/?/init.lua;' .. package.path

local signals = require('aeiou.signals')

-- Test signal processing
signals.process_signal("FILE_SAVED", { file = "test.py" })
signals.process_signal("USER_IDLE", {})
signals.process_signal("analysis", {
  duplication = 10,
  complexity = { complexity_score = 60 },
  test_gap = { test_coverage_ratio = 0.1 },
  todos_dead_code = { todos = 5 }
})

local recent = signals.get_recent_signals(5)
assert(#recent >= 3, "Should have at least 3 recent signals")

-- Test quorum rules
local triggered = signals.process_signal("analysis", {
  duplication = 10,
  complexity = { complexity_score = 60 }
})

assert(#triggered > 0, "Should trigger at least one rule")

print('OK: test_signals.lua')