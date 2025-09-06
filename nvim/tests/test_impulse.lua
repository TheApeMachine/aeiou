package.path = '../lua/?.lua;../lua/?/init.lua;' .. package.path

local impulse = require('aeiou.impulse')

-- Test energy system
local initial_energy = impulse.get_energy()
assert(initial_energy == 40, "Initial energy should be 40")

-- Test budget status
local budget = impulse.get_budget_status()
assert(budget.energy == 40, "Budget energy should match")
assert(budget.can_initiate == false, "Should not be able to initiate with low energy")

-- Test quiet hours (assuming current time is not in quiet hours)
-- Note: This test might fail depending on actual time, but it's a basic check
local is_quiet = budget.is_quiet_hours
assert(type(is_quiet) == "boolean", "Quiet hours should be boolean")

-- Test energy increase simulation
-- (We can't easily test the actual autocmds, but we can test the logic)
print("Note: Autocmd testing would require integration tests")

-- Test safety integration
local safety = require('aeiou.safety')
local safety_status = safety.get_safety_status()
assert(safety_status.kill_switch_active == false, "Safety should be OK for impulse tests")

print('OK: test_impulse.lua')