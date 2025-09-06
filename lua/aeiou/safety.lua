local M = {}

-- Safety caps and kill-switch mechanisms

local safety_config = {
  max_tool_chain_length = 10,
  max_consecutive_actions = 5,
  runaway_detection_threshold = 3,  -- actions per minute
  kill_switch_active = false
}

local action_history = {}
local consecutive_actions = 0
local last_action_time = 0

function M.reset_safety_counters()
  action_history = {}
  consecutive_actions = 0
  last_action_time = 0
end

function M.record_action(action_type, data)
  if safety_config.kill_switch_active then
    return false, "Kill switch is active"
  end

  local now = os.time()
  table.insert(action_history, {
    type = action_type,
    timestamp = now,
    data = data
  })

  -- Keep only recent actions (last 5 minutes)
  local cutoff = now - 300
  local recent_actions = {}
  for _, action in ipairs(action_history) do
    if action.timestamp > cutoff then
      table.insert(recent_actions, action)
    end
  end
  action_history = recent_actions

  -- Check runaway detection
  if #action_history >= safety_config.runaway_detection_threshold then
    local time_span = now - action_history[1].timestamp
    if time_span < 60 then  -- within 1 minute
      safety_config.kill_switch_active = true
      return false, "Runaway detection triggered - kill switch activated"
    end
  end

  -- Check tool chain length
  if #action_history > safety_config.max_tool_chain_length then
    return false, "Maximum tool chain length exceeded"
  end

  -- Track consecutive actions
  if now - last_action_time < 10 then  -- within 10 seconds
    consecutive_actions = consecutive_actions + 1
    if consecutive_actions > safety_config.max_consecutive_actions then
      return false, "Too many consecutive actions"
    end
  else
    consecutive_actions = 0
  end

  last_action_time = now
  return true, "Action allowed"
end

function M.activate_kill_switch()
  safety_config.kill_switch_active = true
  M.reset_safety_counters()
end

function M.deactivate_kill_switch()
  safety_config.kill_switch_active = false
end

function M.is_kill_switch_active()
  return safety_config.kill_switch_active
end

function M.get_safety_status()
  return {
    kill_switch_active = safety_config.kill_switch_active,
    action_history_count = #action_history,
    consecutive_actions = consecutive_actions,
    max_tool_chain_length = safety_config.max_tool_chain_length,
    max_consecutive_actions = safety_config.max_consecutive_actions,
    runaway_threshold = safety_config.runaway_detection_threshold
  }
end

function M.set_safety_limits(limits)
  if limits.max_tool_chain_length then
    safety_config.max_tool_chain_length = limits.max_tool_chain_length
  end
  if limits.max_consecutive_actions then
    safety_config.max_consecutive_actions = limits.max_consecutive_actions
  end
  if limits.runaway_detection_threshold then
    safety_config.runaway_detection_threshold = limits.runaway_detection_threshold
  end
end

return M