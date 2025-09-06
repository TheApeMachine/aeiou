local Http = {}

local function decode_json(s)
  local ok, res = pcall(vim.fn.json_decode, s)
  if ok then return res end
  return nil
end

function Http.post_json(url, payload, callback)
  local body = vim.fn.json_encode(payload)
  local cmd = {
    "curl", "-sS", "-X", "POST", url,
    "-H", "Content-Type: application/json",
    "--data", body,
  }
  vim.fn.jobstart(cmd, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      if not data then return end
      local text = table.concat(data, "\n")
      local decoded = decode_json(text)
      callback(true, decoded or text)
    end,
    on_stderr = function(_, data)
      if data and #data > 0 then
        callback(false, table.concat(data, "\n"))
      end
    end,
  })
end

function Http.get(url, callback)
  local cmd = { "curl", "-sS", url }
  vim.fn.jobstart(cmd, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      if not data then return end
      callback(true, table.concat(data, "\n"))
    end,
    on_stderr = function(_, data)
      if data and #data > 0 then
        callback(false, table.concat(data, "\n"))
      end
    end,
  })
end

return Http


