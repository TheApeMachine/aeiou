local ui = {}

local state = {
  win = nil,
  buf = nil,
}

local function center_size()
  local columns = vim.o.columns
  local lines = vim.o.lines
  local width = math.min(100, math.floor(columns * 0.6))
  local height = math.min(24, math.floor(lines * 0.4))
  local row = math.floor((lines - height) / 2 - 1)
  local col = math.floor((columns - width) / 2)
  return width, height, row, col
end

local function ensure_window()
  if state.win and vim.api.nvim_win_is_valid(state.win) and state.buf and vim.api.nvim_buf_is_valid(state.buf) then
    return state.buf, state.win
  end
  state.buf = vim.api.nvim_create_buf(false, true)
  local width, height, row, col = center_size()
  state.win = vim.api.nvim_open_win(state.buf, true, {
    relative = 'editor', style = 'minimal',
    width = width, height = height, row = row, col = col,
    border = 'rounded',
  })
  vim.api.nvim_buf_set_option(state.buf, 'buftype', 'nofile')
  vim.api.nvim_buf_set_option(state.buf, 'bufhidden', 'wipe')
  vim.api.nvim_buf_set_option(state.buf, 'modifiable', true)
  return state.buf, state.win
end

local function render_lines(lines)
  local buf = ensure_window()
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
end

local function pretty_json(tbl)
  local encoded = vim.fn.json_encode(tbl)
  if not encoded then return {"<invalid json>"} end
  local ok, parsed = pcall(vim.fn.json_decode, encoded)
  if not ok then return { encoded } end
  local formatted = vim.fn.json_encode(parsed)
  local out = {}
  for s in string.gmatch(formatted, "[^\n]+") do table.insert(out, s) end
  return out
end

function ui.open_spec_window()
  local buf = ensure_window()
  local lines = {
    "AEIOU Transcoder",
    "",
    "Type a prompt below, then press <Enter> to transcode:",
    "",
  }
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_buf_set_option(buf, 'modifiable', true)
  vim.api.nvim_buf_set_option(buf, 'filetype', 'markdown')

  local input_prompt = "Prompt: "
  table.insert(lines, input_prompt)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_win_set_cursor(state.win, { #lines, string.len(input_prompt) + 1 })

  local function on_enter()
    local row = #lines
    local text = vim.api.nvim_buf_get_lines(buf, row - 1, row, false)[1] or ""
    local prompt = string.sub(text, string.len(input_prompt) + 1)
    if prompt == nil or prompt == '' then return end
    render_lines({"Transcoding..."})
    local cfg = require('aeiou').get_config()
    require('aeiou.http').post_json(cfg.sidecar_url .. "/transcode", {
      prompt = prompt,
      verbosity = "normal",
    }, function(ok, result)
      if ok and type(result) == 'table' then
        render_lines(pretty_json(result))
      else
        render_lines({"Error:", tostring(result)})
      end
    end)
  end

  vim.keymap.set('n', '<CR>', on_enter, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('i', '<CR>', function()
    vim.api.nvim_input('<Esc>')
    on_enter()
  end, { buffer = buf, nowait = true, noremap = true, silent = true })
end

function ui.show_taskspec(taskspec)
  local buf = ensure_window()
  local lines = {
    "AEIOU TaskSpec",
    "==============",
    "",
    "Goal: " .. (taskspec.goal or "N/A"),
    "",
    "Risk: " .. (taskspec.risk or "N/A") .. " | Priority: " .. (taskspec.priority or "N/A") .. " | Cost: " .. (taskspec.estimated_cost or "N/A"),
    "",
  }

  -- Show inputs
  if taskspec.inputs and #taskspec.inputs > 0 then
    table.insert(lines, "Inputs:")
    for _, input in ipairs(taskspec.inputs) do
      table.insert(lines, "• " .. input)
    end
  else
    table.insert(lines, "Inputs: (none specified)")
  end
  table.insert(lines, "")

  -- Show outputs
  if taskspec.outputs and #taskspec.outputs > 0 then
    table.insert(lines, "Outputs:")
    for _, output in ipairs(taskspec.outputs) do
      table.insert(lines, "• " .. output)
    end
  else
    table.insert(lines, "Outputs: (none specified)")
  end
  table.insert(lines, "")

  if taskspec.open_questions and #taskspec.open_questions > 0 then
    table.insert(lines, "Open Questions:")
    for _, question in ipairs(taskspec.open_questions) do
      table.insert(lines, "• " .. question)
    end
    table.insert(lines, "")
  end

  if taskspec.constraints_inferred and #taskspec.constraints_inferred > 0 then
    table.insert(lines, "Constraints:")
    for _, constraint in ipairs(taskspec.constraints_inferred) do
      table.insert(lines, "• " .. constraint)
    end
  end

  table.insert(lines, "")
  table.insert(lines, "Commands: 'i' (add inputs) | 'o' (add outputs) | 'q' (quit)")

  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_buf_set_option(buf, 'modifiable', false)
  vim.api.nvim_buf_set_option(buf, 'filetype', 'markdown')

  -- Store taskspec for editing
  ui.current_taskspec = taskspec

  vim.keymap.set('n', 'i', function() ui.add_inputs() end, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('n', 'o', function() ui.add_outputs() end, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('n', 'q', function() ui.close_window() end, { buffer = buf, nowait = true, noremap = true, silent = true })
end

function ui.show_clarifying_questions(taskspec, questions)
  local buf = ensure_window()
  local lines = {
    "AEIOU Clarifying Questions",
    "===========================",
    "",
    "The following information would help improve the TaskSpec:",
    "",
  }

  for i, question in ipairs(questions) do
    table.insert(lines, string.format("%d. %s", i, question))
    table.insert(lines, "")
  end

  table.insert(lines, "Press 'a' to answer questions, 's' to skip")

  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_buf_set_option(buf, 'modifiable', false)
  vim.api.nvim_buf_set_option(buf, 'filetype', 'markdown')

  -- Store questions for later use
  ui.pending_questions = { taskspec = taskspec, questions = questions }

  vim.keymap.set('n', 'a', function() ui.answer_questions() end, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('n', 's', function() ui.skip_questions() end, { buffer = buf, nowait = true, noremap = true, silent = true })
end

function ui.answer_questions()
  if not ui.pending_questions then return end

  local answers = {}
  local questions = ui.pending_questions.questions

  -- Simple implementation: collect answers one by one
  local function collect_answer(index)
    if index > #questions then
      -- All answers collected, enhance TaskSpec
      local cfg = require('aeiou').get_config()
      require('aeiou.http').post_json(cfg.sidecar_url .. '/enhance_taskspec', {
        taskspec = ui.pending_questions.taskspec,
        answers = answers
      }, function(ok, enhanced)
        if ok and enhanced then
          ui.show_taskspec(enhanced)
          local impulse = require('aeiou.impulse')
          impulse.latest_taskspec = enhanced
        else
          print("AEIOU: Failed to enhance TaskSpec")
        end
      end)
      return
    end

    vim.ui.input({
      prompt = questions[index] .. ": "
    }, function(answer)
      if answer and answer ~= "" then
        answers[questions[index]] = answer
      end
      collect_answer(index + 1)
    end)
  end

  collect_answer(1)
end

function ui.skip_questions()
  -- Just show the original TaskSpec
  ui.show_taskspec(ui.pending_questions.taskspec)
  ui.pending_questions = nil
end

function ui.add_inputs()
  if not ui.current_taskspec then return end

  vim.ui.input({
    prompt = "Add input (comma-separated): "
  }, function(input_text)
    if input_text and input_text ~= "" then
      local inputs = vim.split(input_text, ",")
      for i, input in ipairs(inputs) do
        inputs[i] = vim.trim(input)
      end

      -- Update taskspec
      ui.current_taskspec.inputs = ui.current_taskspec.inputs or {}
      for _, input in ipairs(inputs) do
        table.insert(ui.current_taskspec.inputs, input)
      end

      -- Update impulse
      local impulse = require('aeiou.impulse')
      impulse.latest_taskspec = ui.current_taskspec

      -- Refresh display
      ui.show_taskspec(ui.current_taskspec)
    end
  end)
end

function ui.add_outputs()
  if not ui.current_taskspec then return end

  vim.ui.input({
    prompt = "Add output (comma-separated): "
  }, function(output_text)
    if output_text and output_text ~= "" then
      local outputs = vim.split(output_text, ",")
      for i, output in ipairs(outputs) do
        outputs[i] = vim.trim(output)
      end

      -- Update taskspec
      ui.current_taskspec.outputs = ui.current_taskspec.outputs or {}
      for _, output in ipairs(outputs) do
        table.insert(ui.current_taskspec.outputs, output)
      end

      -- Update impulse
      local impulse = require('aeiou.impulse')
      impulse.latest_taskspec = ui.current_taskspec

      -- Refresh display
      ui.show_taskspec(ui.current_taskspec)
    end
  end)
end

function ui.close_window()
  local win = vim.api.nvim_get_current_win()
  vim.api.nvim_win_close(win, true)
end

function ui.show_intent_card(card)
  local buf = ensure_window()
  local lines = {
    "AEIOU Intent Card",
    "=================",
    "",
    "Title: " .. (card.title or "N/A"),
    "",
    "Impact: " .. (card.impact or "medium") .. " | Cost: " .. (card.cost or "medium"),
    "",
    "Description:",
    card.description or "No description available",
    "",
  }

  if card.plan and #card.plan > 0 then
    table.insert(lines, "Plan:")
    for _, step in ipairs(card.plan) do
      table.insert(lines, "• " .. step)
    end
    table.insert(lines, "")
  end

  table.insert(lines, "Actions: 'd' (Do) | 'f' (Defer 1h) | 's' (Skip) | 'q' (Quit)")

  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_buf_set_option(buf, 'modifiable', false)
  vim.api.nvim_buf_set_option(buf, 'filetype', 'markdown')

  -- Store current card for actions
  ui.current_card = card

  vim.keymap.set('n', 'd', function() ui.do_current_card() end, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('n', 'f', function() ui.defer_current_card() end, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('n', 's', function() ui.skip_current_card() end, { buffer = buf, nowait = true, noremap = true, silent = true })
  vim.keymap.set('n', 'q', function() ui.close_window() end, { buffer = buf, nowait = true, noremap = true, silent = true })
end

function ui.do_current_card()
  if not ui.current_card then return end

  local intent_cards = require('aeiou.intent_cards')
  intent_cards.do_card(ui.current_card.id)

  -- Close window and show next card if available
  ui.close_window()
  ui.show_next_intent_card()
end

function ui.defer_current_card()
  if not ui.current_card then return end

  local intent_cards = require('aeiou.intent_cards')
  intent_cards.defer_card(ui.current_card.id)

  -- Close window and show next card if available
  ui.close_window()
  ui.show_next_intent_card()
end

function ui.skip_current_card()
  if not ui.current_card then return end

  local intent_cards = require('aeiou.intent_cards')
  intent_cards.dismiss_card(ui.current_card.id)

  -- Close window and show next card if available
  ui.close_window()
  ui.show_next_intent_card()
end

function ui.show_next_intent_card()
  local intent_cards = require('aeiou.intent_cards')
  local focus_modes = require('aeiou.focus_modes')
  local next_card = intent_cards.get_current_card()

  if next_card then
    -- Check if we should show this card based on focus mode
    if focus_modes.should_interrupt_for_card(next_card) then
      ui.show_intent_card(next_card)
    else
      print("AEIOU: Skipping low-impact card in current focus mode")
    end
  else
    print("AEIOU: No more intent cards available")
  end
end

return ui


