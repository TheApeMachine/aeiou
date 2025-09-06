local M = {}

local energy = 40
local cooldown = false
local config = {
  quiet_hours_start = 22,  -- 10 PM
  quiet_hours_end = 8,     -- 8 AM
  max_unsolicited_per_hour = 5,
  unsolicited_count = 0,
  last_hour = os.date("%H")
}

local function schedule_heartbeat()
  if cooldown then return end
  vim.defer_fn(function()
    local cfg = require('aeiou').get_config()
    local watchers = require('aeiou.watchers')
    local signals = require('aeiou.signals')
    local analysis = watchers.get_current_buffer_analysis()

    -- Process analysis through quorum system if we have data
    local triggered = {}
    if analysis then
      triggered = signals.process_signal("analysis", analysis)
    end

    local budget_status = M.get_budget_status()
    -- Check for reactivated deferred cards
    local intent_cards = require('aeiou.intent_cards')
    intent_cards.check_deferred_cards()

    require('aeiou.http').post_json(cfg.sidecar_url .. '/heartbeat', {
      energy = energy,
      analysis = analysis,
      budget_status = budget_status,
      triggered_rules = triggered
    }, function(ok, result)
      if ok then
        -- Handle heartbeat response - could adjust energy based on sidecar feedback
        -- If we have analysis data and triggered rules, generate a TaskSpec
        if analysis and #triggered > 0 then
          require('aeiou.http').post_json(cfg.sidecar_url .. '/generate_taskspec', analysis, function(ok2, taskspec)
            if ok2 and taskspec then
              -- Check for clarifying questions
              require('aeiou.http').post_json(cfg.sidecar_url .. '/generate_clarifying_questions', taskspec, function(ok3, response)
                if ok3 and response and response.questions and #response.questions > 0 then
                  -- Show clarifying questions to user
                  require('aeiou.ui').show_clarifying_questions(taskspec, response.questions)
                else
                  -- No questions needed, create intent card and show TaskSpec
                  M.latest_taskspec = taskspec
                  local intent_cards = require('aeiou.intent_cards')
                  intent_cards.add_card_from_taskspec(taskspec)
                  require('aeiou.ui').show_taskspec(taskspec)
                end
              end)
            end
          end)
        end
      end
    end)
    schedule_heartbeat()
  end, math.max(10000, 120000 - energy * 1000)) -- 10–120s adaptive
end

function M.setup()
  local safety = require('aeiou.safety')

  vim.api.nvim_create_autocmd({"BufWritePost"}, {
    callback = function(args)
      local cfg = require('aeiou').get_config()
      local signals = require('aeiou.signals')

      -- Check safety before processing
      local allowed, reason = safety.record_action("FILE_SAVED", { file = args.file })
      if not allowed then
        print("AEIOU Safety: " .. reason)
        return
      end

      -- Process signal through quorum system
      local triggered = signals.process_signal("FILE_SAVED", { file = args.file })

      require('aeiou.http').post_json(cfg.sidecar_url .. '/event', {
        type = "FILE_SAVED",
        file = args.file,
        triggered_rules = triggered
      }, function(ok, result) end)
      energy = math.min(100, energy + 8)
    end
  })
  vim.api.nvim_create_autocmd({"CursorHold"}, {
    callback = function()
      local cfg = require('aeiou').get_config()
      local signals = require('aeiou.signals')

      -- Check safety before processing
      local allowed, reason = safety.record_action("USER_IDLE", {})
      if not allowed then
        print("AEIOU Safety: " .. reason)
        return
      end

      -- Process signal through quorum system
      local triggered = signals.process_signal("USER_IDLE", {})

      require('aeiou.http').post_json(cfg.sidecar_url .. '/event', {
        type = "USER_IDLE",
        triggered_rules = triggered
      }, function(ok, result) end)
      energy = math.max(0, energy - 5)
    end
  })
  schedule_heartbeat()
end

function M.get_energy()
  return energy
end

function M.set_cooldown(state)
  cooldown = state
end

local function is_quiet_hours()
  local hour = tonumber(os.date("%H"))
  if config.quiet_hours_start > config.quiet_hours_end then
    -- Quiet hours span midnight (e.g., 22:00 to 08:00)
    return hour >= config.quiet_hours_start or hour < config.quiet_hours_end
  else
    -- Quiet hours within same day
    return hour >= config.quiet_hours_start and hour < config.quiet_hours_end
  end
end

local function can_send_unsolicited()
  local current_hour = os.date("%H")
  if current_hour ~= config.last_hour then
    config.unsolicited_count = 0
    config.last_hour = current_hour
  end
  return config.unsolicited_count < config.max_unsolicited_per_hour and not is_quiet_hours()
end

function M.should_initiate_action()
  return energy > 30 and can_send_unsolicited() and not cooldown
end

function M.record_unsolicited_action()
  config.unsolicited_count = config.unsolicited_count + 1
end

function M.get_budget_status()
  return {
    energy = energy,
    is_quiet_hours = is_quiet_hours(),
    unsolicited_used = config.unsolicited_count,
    unsolicited_limit = config.max_unsolicited_per_hour,
    can_initiate = M.should_initiate_action()
  }
end

return M