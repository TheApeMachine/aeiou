local M = {}

-- Basic watchers for code analysis
-- These are light heuristics that can run periodically

local function count_lines(bufnr)
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  return #lines
end

local function detect_duplication(bufnr)
  -- Simple duplication detection: look for repeated lines
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local seen = {}
  local duplicates = 0

  for _, line in ipairs(lines) do
    line = vim.trim(line)
    if line ~= "" then
      if seen[line] then
        duplicates = duplicates + 1
      else
        seen[line] = true
      end
    end
  end

  return duplicates
end

local function detect_complexity(bufnr)
  -- Simple complexity metric: nesting depth + line count
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local max_nesting = 0
  local current_nesting = 0

  for _, line in ipairs(lines) do
    local indent = string.match(line, "^(%s*)")
    if indent then
      local spaces = #indent
      local nesting_level = math.floor(spaces / 2) -- assuming 2 spaces per indent
      current_nesting = math.max(current_nesting, nesting_level)
    end
  end

  max_nesting = current_nesting
  return {
    lines = #lines,
    max_nesting = max_nesting,
    complexity_score = #lines + max_nesting * 10
  }
end

local function detect_test_gap(bufnr)
  -- Look for functions without corresponding tests
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local functions = 0
  local test_functions = 0

  for _, line in ipairs(lines) do
    if string.match(line, "def ") or string.match(line, "function ") then
      functions = functions + 1
    end
    if string.match(line, "test_") or string.match(line, "Test") then
      test_functions = test_functions + 1
    end
  end

  return {
    functions = functions,
    test_functions = test_functions,
    test_coverage_ratio = functions > 0 and test_functions / functions or 0
  }
end

local function detect_todos_and_dead_code(bufnr)
  -- Look for TODO comments and potentially dead code patterns
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local todos = 0
  local dead_code_indicators = 0

  for _, line in ipairs(lines) do
    if string.match(line, "TODO") or string.match(line, "FIXME") then
      todos = todos + 1
    end
    if string.match(line, "# .*") or string.match(line, "// .*") then
      -- Simple heuristic: commented lines might indicate dead code
      dead_code_indicators = dead_code_indicators + 1
    end
  end

  return {
    todos = todos,
    dead_code_indicators = dead_code_indicators
  }
end

function M.analyze_buffer(bufnr)
  if not vim.api.nvim_buf_is_valid(bufnr) then
    return nil
  end

  local filepath = vim.api.nvim_buf_get_name(bufnr)
  if filepath == "" then
    return nil
  end

  return {
    filepath = filepath,
    duplication = detect_duplication(bufnr),
    complexity = detect_complexity(bufnr),
    test_gap = detect_test_gap(bufnr),
    todos_dead_code = detect_todos_and_dead_code(bufnr)
  }
end

function M.get_current_buffer_analysis()
  local bufnr = vim.api.nvim_get_current_buf()
  return M.analyze_buffer(bufnr)
end

return M