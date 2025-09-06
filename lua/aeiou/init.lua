local M = {}

local config = {
  sidecar_url = "http://127.0.0.1:8000",
  auto_start = true,
}

function M.setup(opts)
  opts = opts or {}
  for k, v in pairs(opts) do
    config[k] = v
  end
  -- autostart sidecar if desired
  if config.auto_start then
    require('aeiou.sidecar').health(function(ok)
      if not ok then require('aeiou.sidecar').start() end
    end)
  end
  -- setup impulse engine
  require('aeiou.impulse').setup()
  vim.api.nvim_create_user_command("AeiouTranscode", function(params)
    require('aeiou.ui').open_spec_window()
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouGenerateFromPrompt", function()
    require('aeiou.gen').generate_from_prompt()
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouGenerateOpsFromPrompt", function()
    vim.ui.input({ prompt = 'Describe small change to scaffold tests: ' }, function(text)
      if not text or #text == 0 then return end
      local cfg = require('aeiou').get_config()
      require('aeiou.http').post_json(cfg.sidecar_url .. '/transcode', { prompt = text, verbosity = 'normal' }, function(ok, spec)
        if not ok or type(spec) ~= 'table' then return require('aeiou.ui').toast('Transcode failed', 'error') end
        require('aeiou.http').post_json(cfg.sidecar_url .. '/generate_ops', { spec = spec }, function(ok2, body)
          if not ok2 or type(body) ~= 'table' or type(body.ops) ~= 'table' then return require('aeiou.ui').toast('Ops failed', 'error') end
          require('aeiou.edit').apply_ops(body.ops)
          require('aeiou.ui').toast('Applied ops', 'info')
        end)
      end)
    end)
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouStart", function()
    require('aeiou.sidecar').start()
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouStop", function()
    require('aeiou.sidecar').stop()
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouKillSwitch", function()
    require('aeiou.safety').activate_kill_switch()
    print("AEIOU: Kill switch activated")
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouResetSafety", function()
    require('aeiou.safety').deactivate_kill_switch()
    require('aeiou.safety').reset_safety_counters()
    print("AEIOU: Safety reset")
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouShowTaskSpec", function()
    local impulse = require('aeiou.impulse')
    if impulse.latest_taskspec then
      require('aeiou.ui').show_taskspec(impulse.latest_taskspec)
    else
      print("AEIOU: No TaskSpec available")
    end
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouEditStyleProfile", function()
    local style_file = vim.fn.expand("~/.aeiou/style_profile.json")
    vim.cmd("edit " .. style_file)
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouShowIntentCard", function()
    local intent_cards = require('aeiou.intent_cards')
    local card = intent_cards.get_current_card()
    if card then
      require('aeiou.ui').show_intent_card(card)
    else
      print("AEIOU: No intent cards available")
    end
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouIntentStats", function()
    local intent_cards = require('aeiou.intent_cards')
    local stats = intent_cards.get_card_stats()
    print(string.format("AEIOU Intent Cards - Total: %d, Pending: %d, Deferred: %d, Completed: %d",
      stats.total, stats.pending, stats.deferred, stats.completed))
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouFocusMode", function(params)
    local mode = params.args
    if mode == "" then
      local focus_modes = require('aeiou.focus_modes')
      local current = focus_modes.get_current_mode()
      print(string.format("AEIOU Focus Mode: %s - %s", current.name, current.settings.description))
    else
      local focus_modes = require('aeiou.focus_modes')
      focus_modes.set_mode(mode)
    end
  end, { nargs = "?" })
  vim.api.nvim_create_user_command("AeiouListModes", function()
    local focus_modes = require('aeiou.focus_modes')
    local modes = focus_modes.list_available_modes()
    print("AEIOU Available Focus Modes:")
    for _, mode in ipairs(modes) do
      print(string.format("  %s: %s", mode.name, mode.description))
    end
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouDigest", function()
    local digests = require('aeiou.digests')
    digests.force_digest()
  end, { nargs = 0 })
  vim.api.nvim_create_user_command("AeiouDigestInterval", function(params)
    local interval = tonumber(params.args)
    if interval and interval > 0 then
      local digests = require('aeiou.digests')
      digests.set_digest_interval(interval)
      print(string.format("AEIOU: Digest interval set to %d seconds", interval))
    else
      local digests = require('aeiou.digests')
      local status = digests.get_status()
      print(string.format("AEIOU: Current digest interval is %d seconds", status.interval_seconds))
    end
  end, { nargs = "?" })
  vim.api.nvim_create_user_command("AeiouSubtasks", function()
    local subtasks = require('aeiou.subtasks')
    local active = subtasks.get_active_subtasks()
    if #active == 0 then
      print("AEIOU: No active subtasks")
      return
    end
    print("AEIOU Active Subtasks:")
    for _, task in ipairs(active) do
      print(string.format("  %s: %d/%d completed (%d failed)",
        task.card_title, task.completed, task.total_subtasks, task.failed))
    end
  end, { nargs = 0 })
end

function M.get_config()
  return config
end

return M


