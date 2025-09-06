local S = {}

local function toast(msg, level)
  local ui = require('aeiou.ui')
  if ui and ui.toast then ui.toast(msg, level) else vim.notify(msg) end
end

function S.health(cb)
  local cfg = require('aeiou').get_config()
  require('aeiou.http').get(cfg.sidecar_url .. "/health", function(ok, body)
    if not ok then return cb(false) end
    local ok2, decoded = pcall(vim.fn.json_decode, body)
    if ok2 and decoded and decoded.status == 'ok' then cb(true) else cb(false) end
  end)
end

function S.start()
  -- Best-effort start: assumes repo layout and venv at sidecar/.venv
  local cmd = { "bash", "-lc", "cd sidecar && test -d .venv || python3 -m venv .venv; . .venv/bin/activate && pip install -r sidecar/requirements.txt && uvicorn app.main:app --host 127.0.0.1 --port 8000" }
  vim.fn.jobstart(cmd, { detach = true })
  toast('Starting AEIOU sidecar…', 'info')
end

function S.stop()
  -- Minimal stop: attempt to kill uvicorn serving our port
  local cmd = { "bash", "-lc", "pkill -f 'uvicorn app.main:app --host 127.0.0.1 --port 8000' || true" }
  vim.fn.jobstart(cmd, { detach = true })
  toast('Stopping AEIOU sidecar…', 'info')
end

return S


