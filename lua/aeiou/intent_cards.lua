local M = {}

-- Intent Cards system for presenting actionable tasks to users
-- Each card shows impact, cost, plan with Do/Defer/Dismiss options

local cards = {}
local current_card_index = 1

local function create_intent_card_from_taskspec(taskspec)
  return {
    id = tostring(os.time()) .. "_" .. tostring(math.random(1000, 9999)),
    title = taskspec.goal or "Code Improvement Task",
    description = M._generate_description(taskspec),
    impact = M._calculate_impact(taskspec),
    cost = taskspec.estimated_cost or "medium",
    plan = M._generate_plan(taskspec),
    taskspec = taskspec,
    status = "pending", -- pending, deferred, dismissed, completed
    created_at = os.time(),
    deferred_until = nil
  }
end

function M._generate_description(taskspec)
  local desc = taskspec.goal or "Improve code quality"

  if taskspec.risk and taskspec.priority then
    desc = desc .. string.format(" (Risk: %s, Priority: %s)", taskspec.risk, taskspec.priority)
  end

  return desc
end

function M._calculate_impact(taskspec)
  -- Calculate impact based on risk, priority, and scope
  local risk_score = ({low = 1, medium = 2, high = 3})[taskspec.risk or "medium"] or 2
  local priority_score = ({low = 1, medium = 2, high = 3})[taskspec.priority or "medium"] or 2

  local impact_score = risk_score * priority_score

  if impact_score >= 6 then
    return "high"
  elseif impact_score >= 3 then
    return "medium"
  else
    return "low"
  end
end

function M._generate_plan(taskspec)
  local plan = {}

  if taskspec.inputs and #taskspec.inputs > 0 then
    table.insert(plan, "Handle inputs: " .. table.concat(taskspec.inputs, ", "))
  end

  if taskspec.constraints_inferred and #taskspec.constraints_inferred > 0 then
    table.insert(plan, "Apply constraints: " .. table.concat(taskspec.constraints_inferred, ", "))
  end

  if taskspec.outputs and #taskspec.outputs > 0 then
    table.insert(plan, "Produce outputs: " .. table.concat(taskspec.outputs, ", "))
  end

  if #plan == 0 then
    table.insert(plan, "Execute code improvements based on analysis")
  end

  return plan
end

function M.add_card_from_taskspec(taskspec)
  local card = create_intent_card_from_taskspec(taskspec)
  table.insert(cards, card)
  return card
end

function M.get_current_card()
  if #cards == 0 then
    return nil
  end

  -- Find the next pending card
  for i, card in ipairs(cards) do
    if card.status == "pending" then
      current_card_index = i
      return card
    end
  end

  return nil
end

function M.do_card(card_id)
  local focus_modes = require('aeiou.focus_modes')
  local subtasks = require('aeiou.subtasks')

  for _, card in ipairs(cards) do
    if card.id == card_id then
      card.status = "in_progress"

      -- Break down into subtasks and dispatch
      local task_subtasks = subtasks.break_down_task(card)
      subtasks.dispatch_subtasks(card, task_subtasks)

      -- Use focus mode to handle the action
      local result = focus_modes.handle_card_action(card, "do")
      return true
    end
  end
  return false
end

function M.defer_card(card_id, minutes)
  minutes = minutes or 60 -- default 1 hour
  for _, card in ipairs(cards) do
    if card.id == card_id then
      card.status = "deferred"
      card.deferred_until = os.time() + (minutes * 60)
      print(string.format("AEIOU: Deferred task for %d minutes - %s", minutes, card.title))
      return true
    end
  end
  return false
end

function M.dismiss_card(card_id)
  for _, card in ipairs(cards) do
    if card.id == card_id then
      card.status = "dismissed"
      print("AEIOU: Dismissed task - " .. card.title)
      return true
    end
  end
  return false
end

function M.complete_card(card_id)
  for _, card in ipairs(cards) do
    if card.id == card_id then
      card.status = "completed"
      print("AEIOU: Completed task - " .. card.title)
      return true
    end
  end
  return false
end

function M.get_card_stats()
  local stats = {
    total = #cards,
    pending = 0,
    deferred = 0,
    dismissed = 0,
    completed = 0,
    in_progress = 0
  }

  for _, card in ipairs(cards) do
    stats[card.status] = (stats[card.status] or 0) + 1
  end

  return stats
end

function M.check_deferred_cards()
  local now = os.time()
  local reactivated = 0

  for _, card in ipairs(cards) do
    if card.status == "deferred" and card.deferred_until and now >= card.deferred_until then
      card.status = "pending"
      card.deferred_until = nil
      reactivated = reactivated + 1
    end
  end

  if reactivated > 0 then
    print(string.format("AEIOU: Reactivated %d deferred tasks", reactivated))
  end

  return reactivated
end

function M.clear_completed_cards()
  local new_cards = {}
  for _, card in ipairs(cards) do
    if card.status ~= "completed" and card.status ~= "dismissed" then
      table.insert(new_cards, card)
    end
  end
  local cleared = #cards - #new_cards
  cards = new_cards
  return cleared
end

function M.get_high_priority_tasks()
  local high_priority = {}
  for _, card in ipairs(cards) do
    if card.status == "pending" and card.impact == "high" then
      table.insert(high_priority, {
        id = card.id,
        title = card.title,
        impact = card.impact
      })
    end
  end
  return high_priority
end

function M.get_pending_cards()
  local pending = {}
  for _, card in ipairs(cards) do
    if card.status == "pending" then
      table.insert(pending, card)
    end
  end
  return pending
end

return M