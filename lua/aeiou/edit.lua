local E = {}

local function ensure_dir(path)
  local dir = vim.fn.fnamemodify(path, ':h')
  if dir ~= '' then vim.fn.mkdir(dir, 'p') end
end

function E.apply_ops(ops)
  for _, op in ipairs(ops or {}) do
    local action = op.action
    local path = op.path
    if action == 'create' then
      ensure_dir(path)
      vim.fn.writefile(vim.split(op.content or '', '\n'), path)
    elseif action == 'append' then
      ensure_dir(path)
      local lines = vim.split(op.content or '', '\n')
      local existing = {}
      if vim.fn.filereadable(path) == 1 then existing = vim.fn.readfile(path) end
      for _, l in ipairs(lines) do table.insert(existing, l) end
      vim.fn.writefile(existing, path)
    end
  end
end

return E


