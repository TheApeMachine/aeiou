local M = {}

-- Tree-sitter/LSP extractors for context window management
-- Extracts current symbol, siblings, imports, callers/callees, and outlines

function M.get_current_symbol()
  local bufnr = vim.api.nvim_get_current_buf()
  local cursor = vim.api.nvim_win_get_cursor(0)
  local line = cursor[1] - 1
  local col = cursor[2]

  -- Use LSP to get symbol at cursor
  local params = {
    textDocument = vim.lsp.util.make_text_document_params(),
    position = { line = line, character = col }
  }

  local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/documentSymbol', params, 1000)
  if result and result[1] and result[1].result then
    return M._find_symbol_at_position(result[1].result, line, col)
  end

  return nil
end

function M._find_symbol_at_position(symbols, line, col)
  for _, symbol in ipairs(symbols) do
    if symbol.range and
       line >= symbol.range.start.line and line <= symbol.range['end'].line and
       col >= symbol.range.start.character and col <= symbol.range['end'].character then
      return {
        name = symbol.name,
        kind = symbol.kind,
        range = symbol.range
      }
    end
    -- Check children recursively
    if symbol.children then
      local child = M._find_symbol_at_position(symbol.children, line, col)
      if child then return child end
    end
  end
  return nil
end

function M.get_symbol_siblings()
  local current = M.get_current_symbol()
  if not current then return {} end

  -- Get document symbols and find siblings
  local bufnr = vim.api.nvim_get_current_buf()
  local params = { textDocument = vim.lsp.util.make_text_document_params() }

  local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/documentSymbol', params, 1000)
  if result and result[1] and result[1].result then
    return M._find_siblings(result[1].result, current)
  end

  return {}
end

function M._find_siblings(symbols, target_symbol)
  for _, symbol in ipairs(symbols) do
    if symbol.children then
      for _, child in ipairs(symbol.children) do
        if child.name == target_symbol.name then
          -- Return all siblings
          return vim.tbl_filter(function(s) return s.name ~= target_symbol.name end, symbol.children)
        end
      end
      -- Check deeper levels
      local siblings = M._find_siblings(symbol.children, target_symbol)
      if #siblings > 0 then return siblings end
    end
  end
  return {}
end

function M.get_imports()
  local bufnr = vim.api.nvim_get_current_buf()
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)

  local imports = {}
  for _, line in ipairs(lines) do
    -- Basic import detection (can be enhanced with tree-sitter)
    if line:match("^import ") or line:match("^from ") then
      table.insert(imports, line)
    end
  end

  return imports
end

function M.get_callers_callees()
  local current = M.get_current_symbol()
  if not current then return { callers = {}, callees = {} } end

  -- Use LSP to find references and definitions
  local bufnr = vim.api.nvim_get_current_buf()
  local params = {
    textDocument = vim.lsp.util.make_text_document_params(),
    position = { line = current.range.start.line, character = current.range.start.character }
  }

  local references = vim.lsp.buf_request_sync(bufnr, 'textDocument/references', params, 1000)
  local definitions = vim.lsp.buf_request_sync(bufnr, 'textDocument/definition', params, 1000)

  return {
    callers = references and references[1] and references[1].result or {},
    callees = definitions and definitions[1] and definitions[1].result or {}
  }
end

function M.get_file_outline()
  local bufnr = vim.api.nvim_get_current_buf()
  local params = { textDocument = vim.lsp.util.make_text_document_params() }

  local result = vim.lsp.buf_request_sync(bufnr, 'textDocument/documentSymbol', params, 1000)
  if result and result[1] and result[1].result then
    return M._flatten_symbols(result[1].result)
  end

  return {}
end

function M._flatten_symbols(symbols, depth)
  depth = depth or 0
  local flattened = {}

  for _, symbol in ipairs(symbols) do
    table.insert(flattened, {
      name = symbol.name,
      kind = symbol.kind,
      depth = depth,
      range = symbol.range
    })

    if symbol.children then
      local children = M._flatten_symbols(symbol.children, depth + 1)
      for _, child in ipairs(children) do
        table.insert(flattened, child)
      end
    end
  end

  return flattened
end

function M.get_context_window(max_tokens)
  max_tokens = max_tokens or 4000

  local context = {
    current_symbol = M.get_current_symbol(),
    siblings = M.get_symbol_siblings(),
    imports = M.get_imports(),
    callers_callees = M.get_callers_callees(),
    outline = M.get_file_outline()
  }

  -- Estimate token count and trim if necessary
  local estimated_tokens = M._estimate_context_tokens(context)
  if estimated_tokens > max_tokens then
    context = M._trim_context(context, max_tokens)
  end

  return context
end

function M._estimate_context_tokens(context)
  -- Rough token estimation
  local tokens = 0

  if context.current_symbol then tokens = tokens + 10 end
  tokens = tokens + #context.siblings * 5
  tokens = tokens + #context.imports * 3
  tokens = tokens + #context.outline * 2

  return tokens
end

function M._trim_context(context, max_tokens)
  -- Trim less important context to fit token limit
  local trimmed = vim.deepcopy(context)

  -- Remove outline if too large
  if #trimmed.outline > 20 then
    trimmed.outline = vim.list_slice(trimmed.outline, 1, 20)
  end

  -- Limit siblings
  if #trimmed.siblings > 10 then
    trimmed.siblings = vim.list_slice(trimmed.siblings, 1, 10)
  end

  return trimmed
end

return M