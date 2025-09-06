local M = {}

-- Rolling chat memory with turn compression and focus-stack for active tasks

local memory = {}
local max_memory_entries = 50
local focus_stack = {}

function M.add_message(role, content, metadata)
  table.insert(memory, {
    role = role,
    content = content,
    timestamp = os.time(),
    metadata = metadata or {},
    compressed = false
  })

  -- Maintain memory limit
  if #memory > max_memory_entries then
    M.compress_old_messages()
  end
end

function M.compress_old_messages()
  -- Compress older messages to save space
  local cutoff = #memory - max_memory_entries + 10

  for i = 1, cutoff do
    if not memory[i].compressed then
      memory[i].content = M._compress_message(memory[i].content)
      memory[i].compressed = true
    end
  end

  -- Remove oldest messages if still too many
  if #memory > max_memory_entries then
    local excess = #memory - max_memory_entries
    for i = 1, excess do
      table.remove(memory, 1)
    end
  end
end

function M._compress_message(content)
  -- Simple compression: truncate long messages
  if #content > 200 then
    return content:sub(1, 200) .. "..."
  end
  return content
end

function M.get_recent_context(max_tokens)
  max_tokens = max_tokens or 2000
  local context = {}
  local total_tokens = 0

  -- Start from most recent and work backwards
  for i = #memory, 1, -1 do
    local msg = memory[i]
    local msg_tokens = M._estimate_tokens(msg.content)

    if total_tokens + msg_tokens <= max_tokens then
      table.insert(context, 1, msg)  -- Insert at beginning to maintain order
      total_tokens = total_tokens + msg_tokens
    else
      break
    end
  end

  return context
end

function M._estimate_tokens(text)
  -- Rough estimation: ~4 characters per token
  return math.ceil(#text / 4)
end

function M.push_focus(task_id, description)
  table.insert(focus_stack, {
    task_id = task_id,
    description = description,
    started_at = os.time()
  })
end

function M.pop_focus()
  return table.remove(focus_stack)
end

function M.get_current_focus()
  return focus_stack[#focus_stack]
end

function M.get_focus_stack()
  return vim.deepcopy(focus_stack)
end

function M.clear_memory()
  memory = {}
  focus_stack = {}
end

return M