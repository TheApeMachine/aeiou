package.path = 'nvim/lua/?.lua;nvim/lua/?/init.lua;' .. package.path

local edit = require('aeiou.edit')

-- Use a temp file in the project root
local tmp = 'nvim/tests/tmp_generated.txt'
pcall(vim.fn.delete, tmp)

-- Apply create op
edit.apply_ops({ { action = 'create', path = tmp, content = 'line1\nline2' } })
local lines = vim.fn.readfile(tmp)
assert(#lines == 2, 'create op failed')
assert(lines[1] == 'line1', 'content mismatch')

-- Apply append op
edit.apply_ops({ { action = 'append', path = tmp, content = 'line3' } })
local lines2 = vim.fn.readfile(tmp)
assert(#lines2 == 3, 'append op failed')
assert(lines2[3] == 'line3', 'append content mismatch')

-- cleanup
pcall(vim.fn.delete, tmp)

print('OK: test_edit.lua')


