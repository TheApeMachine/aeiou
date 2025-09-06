local M = {}

-- Background digests: periodic summaries of deferred/backlog items
-- Provides regular updates on task status without constant interruptions

local digest_schedule = nil
local last_digest_time = 0
local digest_interval = 1800 -- 30 minutes default
local digest_enabled = true

function M.start_digest_schedule()
  if digest_schedule then
    M.stop_digest_schedule()
  end

  digest_schedule = vim.loop.new_timer()
  digest_schedule:start(60000, digest_interval * 1000, vim.schedule_wrap(function()
    M.generate_digest()
  end))
end

function M.stop_digest_schedule()
  if digest_schedule then
    digest_schedule:stop()
    digest_schedule:close()
    digest_schedule = nil
  end
end

function M.set_digest_interval(seconds)
  digest_interval = seconds
  if digest_schedule then
    M.stop_digest_schedule()
    M.start_digest_schedule()
  end
end

function M.generate_digest()
  if not digest_enabled then
    return
  end

  local intent_cards = require('aeiou.intent_cards')
  local stats = intent_cards.get_card_stats()

  -- Only show digest if there are meaningful updates
  if stats.total == 0 then
    return
  end

  local now = os.time()
  local time_since_last = now - last_digest_time

  -- Generate digest message
  local digest_lines = {
    "📊 AEIOU Digest (" .. os.date("%H:%M") .. ")",
    ""
  }

  if stats.pending > 0 then
    table.insert(digest_lines, string.format("⏳ Pending tasks: %d", stats.pending))
  end

  if stats.deferred > 0 then
    table.insert(digest_lines, string.format("⏰ Deferred tasks: %d", stats.deferred))
  end

  if stats.completed > 0 then
    table.insert(digest_lines, string.format("✅ Completed tasks: %d", stats.completed))
  end

  -- Add focus mode info
  local focus_modes = require('aeiou.focus_modes')
  local current_mode = focus_modes.get_current_mode()
  table.insert(digest_lines, string.format("🎯 Mode: %s", current_mode.name))

  -- Show high-priority pending tasks
  local high_priority_tasks = M.get_high_priority_tasks()
  if #high_priority_tasks > 0 then
    table.insert(digest_lines, "")
    table.insert(digest_lines, "🚨 High Priority:")
    for _, task in ipairs(high_priority_tasks) do
      table.insert(digest_lines, string.format("  • %s", task.title))
    end
  end

  -- Show digest
  if #digest_lines > 2 then -- More than just header and mode
    vim.notify(table.concat(digest_lines, "\n"), "info", {
      title = "AEIOU Digest",
      timeout = 10000
    })
  end

  last_digest_time = now
end

function M.get_high_priority_tasks()
  local intent_cards = require('aeiou.intent_cards')
  return intent_cards.get_high_priority_tasks()
end

function M.force_digest()
  M.generate_digest()
end

function M.enable_digests()
  digest_enabled = true
  M.start_digest_schedule()
end

function M.disable_digests()
  digest_enabled = false
  M.stop_digest_schedule()
end

function M.is_enabled()
  return digest_enabled
end

function M.get_status()
  return {
    enabled = digest_enabled,
    interval_seconds = digest_interval,
    last_digest = last_digest_time,
    next_digest = last_digest_time + digest_interval
  }
end

-- Auto-start digests
M.enable_digests()

return M