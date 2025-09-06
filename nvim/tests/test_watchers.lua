package.path = '../lua/?.lua;../lua/?/init.lua;' .. package.path

local watchers = require('aeiou.watchers')

-- Create a test buffer
local buf = vim.api.nvim_create_buf(false, true)
vim.api.nvim_buf_set_lines(buf, 0, -1, false, {
  "def test_function():",
  "    x = 1",
  "    y = 2",
  "    return x + y",
  "",
  "def another_function():",
  "    x = 1",  -- duplicate line
  "    z = 3",
  "    return x + z",
  "",
  "# TODO: add error handling",
  "// This is dead code"
})

local analysis = watchers.analyze_buffer(buf)

assert(analysis ~= nil, "Analysis should not be nil")
assert(analysis.duplication >= 1, "Should detect duplication")
assert(analysis.complexity.lines == 11, "Should count lines correctly")
assert(analysis.todos_dead_code.todos >= 1, "Should detect TODO")
assert(analysis.test_gap.functions >= 2, "Should detect functions")

-- Cleanup
vim.api.nvim_buf_delete(buf, { force = true })

print('OK: test_watchers.lua')