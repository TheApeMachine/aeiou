local M = {}

-- Focus modes for different interaction styles
-- Pair: narrated small steps with user guidance
-- Background: quiet operation with minimal interruptions
-- Solo Batches: autonomous execution of multiple tasks

local current_mode = "background" -- default to background mode
local mode_settings = {
  pair = {
    name = "Pair",
    description = "Narrated small steps with user guidance",
    interrupt_frequency = "high", -- interrupt for each step
    narration_enabled = true,
    auto_execute = false,
    step_by_step = true
  },
  background = {
    name = "Background",
    description = "Quiet operation with minimal interruptions",
    interrupt_frequency = "low", -- only interrupt for important issues
    narration_enabled = false,
    auto_execute = true,
    step_by_step = false
  },
  solo_batches = {
    name = "Solo Batches",
    description = "Autonomous execution of multiple tasks",
    interrupt_frequency = "none", -- no interruptions
    narration_enabled = false,
    auto_execute = true,
    step_by_step = false,
    batch_size = 5 -- execute up to 5 tasks at once
  }
}

function M.set_mode(mode_name)
  if mode_settings[mode_name] then
    current_mode = mode_name
    local mode = mode_settings[mode_name]
    print(string.format("AEIOU: Switched to %s mode - %s", mode.name, mode.description))
    return true
  else
    print("AEIOU: Invalid mode. Available modes: pair, background, solo_batches")
    return false
  end
end

function M.get_current_mode()
  return {
    name = current_mode,
    settings = mode_settings[current_mode]
  }
end

function M.should_interrupt_for_card(card)
  local mode = mode_settings[current_mode]

  if mode.interrupt_frequency == "none" then
    return false
  elseif mode.interrupt_frequency == "low" then
    -- Only interrupt for high impact cards
    return card.impact == "high"
  elseif mode.interrupt_frequency == "high" then
    -- Interrupt for medium and high impact cards
    return card.impact == "high" or card.impact == "medium"
  end

  return false
end

function M.should_narrate_action()
  return mode_settings[current_mode].narration_enabled
end

function M.should_auto_execute()
  return mode_settings[current_mode].auto_execute
end

function M.is_step_by_step()
  return mode_settings[current_mode].step_by_step
end

function M.get_batch_size()
  return mode_settings[current_mode].batch_size or 1
end

function M.narrate_action(action, details)
  if not M.should_narrate_action() then
    return
  end

  local narration = string.format("AEIOU [%s]: %s", current_mode, action)
  if details then
    narration = narration .. " - " .. details
  end

  print(narration)
end

function M.handle_card_action(card, action)
  local mode = mode_settings[current_mode]

  if action == "do" then
    if mode.step_by_step then
      M.narrate_action("Starting task", card.title)
      -- In pair mode, ask for confirmation before each step
      return "step_by_step"
    else
      M.narrate_action("Executing task", card.title)
      return "auto_execute"
    end
  elseif action == "defer" then
    M.narrate_action("Deferring task", card.title)
    return "deferred"
  elseif action == "dismiss" then
    M.narrate_action("Dismissing task", card.title)
    return "dismissed"
  end

  return "unknown"
end

function M.get_mode_status()
  local mode = mode_settings[current_mode]
  return {
    current_mode = current_mode,
    name = mode.name,
    description = mode.description,
    interrupt_frequency = mode.interrupt_frequency,
    narration_enabled = mode.narration_enabled,
    auto_execute = mode.auto_execute,
    step_by_step = mode.step_by_step,
    batch_size = mode.batch_size
  }
end

function M.list_available_modes()
  local modes = {}
  for name, settings in pairs(mode_settings) do
    table.insert(modes, {
      name = name,
      display_name = settings.name,
      description = settings.description
    })
  end
  return modes
end

-- Initialize with background mode
M.set_mode("background")

return M