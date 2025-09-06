local G = {}

local function toast(msg, level)
  local ui = require('aeiou.ui')
  if ui and ui.toast then ui.toast(msg, level) else vim.notify(msg) end
end

local function open_code_buffer(code)
  local buf = vim.api.nvim_create_buf(true, false)
  local lines = {}
  for s in string.gmatch(code or '', "[^\n]*\n?") do
    if s == '' then break end
    lines[#lines + 1] = select(1, s:gsub("\n$", ""))
  end
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_set_current_buf(buf)
end

function G.generate_from_prompt()
  vim.ui.input({ prompt = 'Describe the code to generate: ' }, function(text)
    if not text or #text == 0 then return end
    local cfg = require('aeiou').get_config()
    -- 1) transcode
    require('aeiou.http').post_json(cfg.sidecar_url .. '/transcode', {
      prompt = text,
      verbosity = 'normal',
    }, function(ok, spec)
      if not ok or type(spec) ~= 'table' then
        return toast('Transcode failed', 'error')
      end
      -- 2) generate
      require('aeiou.http').post_json(cfg.sidecar_url .. '/generate', { spec = spec }, function(ok2, body)
        if not ok2 or type(body) ~= 'table' or type(body.code) ~= 'string' then
          return toast('Generate failed', 'error')
        end
        open_code_buffer(body.code)
        toast('Generated code opened in new buffer', 'info')
      end)
    end)
  end)
end

return G


