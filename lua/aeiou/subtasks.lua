local M = {}

-- Parallel subtask dispatch and reconcile rules
-- Breaks down complex tasks into smaller subtasks for parallel execution

local active_subtasks = {}
local reconcile_rules = {}

function M.dispatch_subtasks(card, subtasks)
  local task_id = card.id
  active_subtasks[task_id] = {
    card = card,
    subtasks = {},
    completed = {},
    failed = {},
    start_time = os.time()
  }

  for i, subtask in ipairs(subtasks) do
    local subtask_id = task_id .. "_sub_" .. i
    active_subtasks[task_id].subtasks[subtask_id] = {
      id = subtask_id,
      description = subtask.description,
      action = subtask.action,
      params = subtask.params or {},
      status = "pending",
      created_at = os.time()
    }
  end

  -- Start executing subtasks
  M.execute_pending_subtasks(task_id)

  return task_id
end

function M.execute_pending_subtasks(task_id)
  local task = active_subtasks[task_id]
  if not task then return end

  local focus_modes = require('aeiou.focus_modes')
  local batch_size = focus_modes.get_batch_size()

  local executed = 0
  for subtask_id, subtask in pairs(task.subtasks) do
    if subtask.status == "pending" and executed < batch_size then
      M.execute_subtask(task_id, subtask_id)
      executed = executed + 1
    end
  end
end

function M.execute_subtask(task_id, subtask_id)
  local task = active_subtasks[task_id]
  if not task then return end

  local subtask = task.subtasks[subtask_id]
  if not subtask then return end

  subtask.status = "running"
  subtask.started_at = os.time()

  -- Simulate subtask execution (in real implementation, this would call actual functions)
  vim.defer_fn(function()
    M.complete_subtask(task_id, subtask_id, true, "Subtask completed successfully")
  end, 1000) -- Simulate 1 second execution time
end

function M.complete_subtask(task_id, subtask_id, success, result)
  local task = active_subtasks[task_id]
  if not task then return end

  local subtask = task.subtasks[subtask_id]
  if not subtask then return end

  subtask.status = success and "completed" or "failed"
  subtask.completed_at = os.time()
  subtask.result = result

  if success then
    table.insert(task.completed, subtask)
  else
    table.insert(task.failed, subtask)
  end

  -- Check if all subtasks are done
  M.check_task_completion(task_id)
end

function M.check_task_completion(task_id)
  local task = active_subtasks[task_id]
  if not task then return end

  local total_subtasks = 0
  local completed_subtasks = 0

  for _, subtask in pairs(task.subtasks) do
    total_subtasks = total_subtasks + 1
    if subtask.status == "completed" or subtask.status == "failed" then
      completed_subtasks = completed_subtasks + 1
    end
  end

  if completed_subtasks >= total_subtasks then
    M.reconcile_task(task_id)
  end
end

function M.reconcile_task(task_id)
  local task = active_subtasks[task_id]
  if not task then return end

  -- Apply reconcile rules
  local rule = reconcile_rules[task.card.title] or M.get_default_reconcile_rule()

  local success = rule.reconcile_function(task)

  -- Mark main task as completed
  local intent_cards = require('aeiou.intent_cards')
  if success then
    intent_cards.complete_card(task.card.id)
  else
    -- Handle failure - could retry or mark as failed
    print("AEIOU: Task reconciliation failed for " .. task.card.title)
  end

  -- Clean up
  active_subtasks[task_id] = nil
end

function M.get_default_reconcile_rule()
  return {
    name = "default",
    reconcile_function = function(task)
      -- Default: succeed if more than 50% of subtasks succeeded
      local success_ratio = #task.completed / (#task.completed + #task.failed)
      return success_ratio > 0.5
    end
  }
end

function M.add_reconcile_rule(task_pattern, rule)
  reconcile_rules[task_pattern] = rule
end

function M.break_down_task(card)
  -- Analyze the card and break it down into subtasks
  local subtasks = {}

  if card.taskspec then
    local spec = card.taskspec

    -- Break down based on constraints
    if spec.constraints_inferred then
      for _, constraint in ipairs(spec.constraints_inferred) do
        if string.find(constraint, "test") then
          table.insert(subtasks, {
            description = "Add test coverage for " .. spec.goal,
            action = "generate_tests",
            params = { spec = spec }
          })
        elseif string.find(constraint, "complexity") then
          table.insert(subtasks, {
            description = "Refactor complex functions in " .. (spec.inputs[1] or "file"),
            action = "refactor_complexity",
            params = { file = spec.inputs[1] }
          })
        elseif string.find(constraint, "duplicate") then
          table.insert(subtasks, {
            description = "Remove code duplication in " .. (spec.inputs[1] or "file"),
            action = "remove_duplicates",
            params = { file = spec.inputs[1] }
          })
        end
      end
    end
  end

  -- If no specific subtasks, create a generic one
  if #subtasks == 0 then
    table.insert(subtasks, {
      description = "Execute " .. card.title,
      action = "execute_task",
      params = { card = card }
    })
  end

  return subtasks
end

function M.get_active_subtasks()
  local active = {}
  for task_id, task in pairs(active_subtasks) do
    table.insert(active, {
      task_id = task_id,
      card_title = task.card.title,
      total_subtasks = M.count_subtasks(task.subtasks),
      completed = #task.completed,
      failed = #task.failed
    })
  end
  return active
end

function M.count_subtasks(subtasks)
  local count = 0
  for _ in pairs(subtasks) do
    count = count + 1
  end
  return count
end

return M