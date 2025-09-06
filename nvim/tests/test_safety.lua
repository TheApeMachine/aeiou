package.path = '../lua/?.lua;../lua/?/init.lua;' .. package.path

local safety = require('aeiou.safety')

-- Test safety status
local status = safety.get_safety_status()
assert(status.kill_switch_active == false, "Kill switch should be inactive initially")
assert(status.action_history_count == 0, "Should have no action history initially")

-- Test action recording
local allowed, reason = safety.record_action("test_action", { data = "test" })
assert(allowed == true, "First action should be allowed")
assert(reason == "Action allowed", "Should return success message")

-- Test safety status after action
status = safety.get_safety_status()
assert(status.action_history_count == 1, "Should have 1 action in history")

-- Test kill switch
safety.activate_kill_switch()
assert(safety.is_kill_switch_active() == true, "Kill switch should be active")

allowed, reason = safety.record_action("test_action2", {})
assert(allowed == false, "Action should be blocked when kill switch is active")
assert(reason == "Kill switch is active", "Should return kill switch message")

-- Test safety reset
safety.deactivate_kill_switch()
safety.reset_safety_counters()
status = safety.get_safety_status()
assert(status.kill_switch_active == false, "Kill switch should be inactive after reset")
assert(status.action_history_count == 0, "Action history should be cleared")

print('OK: test_safety.lua')