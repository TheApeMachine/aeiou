# AEIOU MVP Scaffold — Neovim Plugin + FastAPI Sidecar (Extended)

> Adds `/generate` endpoint for codegen, plus AST‑guided edit application and heartbeat/quorum for impulse engine.

```
├─ schemas/
│  └─ canonical_spec.schema.json
├─ sidecar/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ llm.py
│  │  ├─ vectors.py
│  │  └─ voice.py
│  └─ requirements.txt
└─ nvim/
   ├─ plugin/
   │  └─ aeiou.lua
   └─ lua/aeiou/
      ├─ init.lua
      ├─ http.lua
      ├─ ui.lua
      ├─ impulse.lua
      └─ ts.lua
```

---

## sidecar/app/main.py (extended)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jsonschema import validate
import json, sqlite3, time, os
from . import llm

APP_DIR = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(APP_DIR)), "schemas", "canonical_spec.schema.json")
with open(SCHEMA_PATH) as f: SPEC_SCHEMA = json.load(f)

DB="aeiou.db"
app = FastAPI(title="AEIOU Sidecar")

class TranscodeIn(BaseModel):
    prompt: str
    style_profile: dict | None = None

class GenerateIn(BaseModel):
    spec: dict

@app.on_event("startup")
def init_db():
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS decisions(
      id INTEGER PRIMARY KEY, ts INTEGER, project TEXT, spec JSON
    );
    CREATE TABLE IF NOT EXISTS generations(
      id INTEGER PRIMARY KEY, ts INTEGER, spec JSON, code TEXT
    );
    CREATE TABLE IF NOT EXISTS nodes(
      id TEXT PRIMARY KEY, kind TEXT, uri TEXT, meta JSON
    );
    CREATE TABLE IF NOT EXISTS edges(
      src TEXT, dst TEXT, rel TEXT, meta JSON,
      PRIMARY KEY(src,dst,rel)
    );
    """)
    con.commit(); con.close()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/transcode")
async def transcode(inp: TranscodeIn):
    sys_prompt = "Be precise. Extract explicit constraints; infer style gently. Return valid JSON only."
    data = await llm.chat_json(sys_prompt, inp.prompt, SPEC_SCHEMA)
    try:
        validate(instance=data, schema=SPEC_SCHEMA)
    except Exception as e:
        raise HTTPException(400, f"Schema validation failed: {e}")
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("INSERT INTO decisions(ts,project,spec) VALUES(?,?,?)",
                (int(time.time()), "default", json.dumps(data)))
    con.commit(); con.close()
    return {"spec": data}

@app.post("/generate")
async def generate(inp: GenerateIn):
    """Turn an approved spec into candidate code."""
    sys_prompt = "You are a code generator. Given a CanonicalSpec, produce code implementation. Return only code fenced in triple backticks." 
    data = inp.spec
    text = json.dumps(data, indent=2)
    codegen = await llm.chat_json(sys_prompt, text, {"type":"object","properties":{"code":{"type":"string"}}})
    code = codegen.get("code", "")
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("INSERT INTO generations(ts,spec,code) VALUES(?,?,?)", (int(time.time()), json.dumps(data), code))
    con.commit(); con.close()
    return {"code": code}
```

---

## nvim/lua/aeiou/init.lua (extended)
```lua
local M = {}
local http = require('aeiou.http')
local ui = require('aeiou.ui')

M.config = {
  sidecar = { url = 'http://127.0.0.1:8000' },
  schema_name = 'canonical_spec.schema.json',
}

function M.setup(opts)
  M.config = vim.tbl_deep_extend('force', M.config, opts or {})
  require('aeiou.impulse').setup()
end

function M.transcode_prompt()
  ui.prompt_input("Describe the task…", function(text)
    if not text or #text == 0 then return end
    http.post('/transcode', { prompt = text }, function(ok, body)
      if not ok then return ui.toast('Transcode failed: '..tostring(body), 'error') end
      ui.show_spec(body.spec)
    end)
  end)
end

function M.generate_code(spec)
  http.post('/generate', { spec = spec }, function(ok, body)
    if not ok then return ui.toast('Generate failed', 'error') end
    local code = body.code or ""
    local buf = vim.api.nvim_create_buf(true, false)
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(code, "\n"))
    vim.api.nvim_set_current_buf(buf)
  end)
end

return M
```

---

## nvim/lua/aeiou/impulse.lua (quorum)
```lua
local M = {}
local energy = 40
local signals = {}

local function quorum_check()
  -- naive quorum: if 2+ different signals in last interval
  local distinct = {}
  for _, s in ipairs(signals) do distinct[s] = true end
  local n = 0; for _ in pairs(distinct) do n = n + 1 end
  signals = {}
  return n >= 2
end

local function heartbeat()
  local ui = require('aeiou.ui')
  if quorum_check() and energy > 50 then
    ui.toast('Impulse: potential refactor/test-gap, open Pilot Panel', 'info')
  end
  vim.defer_fn(heartbeat, math.max(10000, 120000 - energy * 1000))
end

function M.setup()
  vim.api.nvim_create_autocmd('BufWritePost', {
    callback = function(args)
      table.insert(signals, 'save')
      energy = math.min(100, energy + 8)
    end
  })
  vim.api.nvim_create_autocmd('CursorHold', {
    callback = function()
      table.insert(signals, 'idle')
      energy = math.max(0, energy - 5)
    end
  })
  heartbeat()
end

return M
```

---

## nvim/lua/aeiou/ts.lua (AST edit stub)
```lua
local M = {}
function M.insert_function(bufnr, name, code_lines)
  local parser = vim.treesitter.get_parser(bufnr)
  local tree = parser:parse()[1]
  local root = tree:root()
  local src = vim.treesitter.get_node_text(root, bufnr)
  -- naive: append at EOF if no smarter placement
  vim.api.nvim_buf_set_lines(bufnr, -1, -1, false, code_lines)
end
return M
```

---

## Usage
- `:AeiouTranscode` → capture task → spec popup.
- Pass spec to `require('aeiou').generate_code(spec)` to create a buffer with candidate code.
- Impulse engine now monitors BufWrite/idle, fuses signals, and surfaces gentle prompts via toasts.
- AST edit stub ready: extend `insert_function` for symbol‑aware placement.

Next steps: flesh out Intent Cards in Pilot Panel, implement smarter AST diff application, and call `/generate` automatically from approved specs.



---

# Additions: /generate endpoint, AST-guided edits, and Impulse → Intent Cards

## sidecar/app/llm.py — add codegen helper
```python
import os, httpx, json
OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("AEIOU_MODEL", "gpt-4o-mini")

async def chat_json(system: str, user: str, schema: dict) -> dict:
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.2
    }
    async with httpx.AsyncClient(base_url=OPENAI_BASE, timeout=60) as client:
        r = await client.post("/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"].strip()
        try:
            return json.loads(txt)
        except Exception:
            start = txt.find("{"); end = txt.rfind("}")
            if start >=0 and end > start:
                return json.loads(txt[start:end+1])
            raise

async def chat_text(system: str, user: str) -> str:
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.3
    }
    async with httpx.AsyncClient(base_url=OPENAI_BASE, timeout=120) as client:
        r = await client.post("/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
```

## sidecar/app/main.py — add `/generate`
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jsonschema import validate
import json, sqlite3, time, os
from . import llm

# ... existing code above ...

class GenerateIn(BaseModel):
    spec: dict
    context: dict | None = None

@app.post("/generate")
async def generate(inp: GenerateIn):
    """
    Return operations list for the editor to apply.
    Each op: {action:'edit'|'create', path, locator?, content?}
    locator: {kind:'function', name:'foo'} for AST-guided edits.
    """
    sys = (
        "You generate precise code edits for a Neovim agent.
"
        "Respond ONLY with JSON: {\"ops\":[...]} where each op has action, path, optional locator, and content.
"
        "Prefer small, safe changes; keep user style; add tests if specified."
    )
    user = "SPEC:
" + json.dumps(inp.spec) + "

CONTEXT:
" + json.dumps(inp.context or {})
    data = await llm.chat_json(sys, user, {"type":"object","properties":{"ops":{"type":"array"}},"required":["ops"]})
    if not isinstance(data, dict) or "ops" not in data:
        raise HTTPException(400, "Malformed ops")
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("INSERT INTO decisions(ts,project,spec) VALUES(?,?,?)",
                (int(time.time()), "default", json.dumps({"generated": data})))
    con.commit(); con.close()
    return data
```

## nvim/lua/aeiou/edit.lua — AST‑guided apply
```lua
local M = {}

function M.replace_function_body(bufnr, func_name, new_body)
  local ft = vim.bo[bufnr].filetype
  local lang = vim.treesitter.language.get_lang(ft)
  if not lang then return false, 'no treesitter lang' end
  local ok, parser = pcall(vim.treesitter.get_parser, bufnr, lang)
  if not ok then return false, 'no parser' end
  local tree = parser:parse()[1]
  local root = tree:root()
  local queries = {
    python = [[(function_definition name: (identifier) @name body: (block) @body)]],
    javascript = [[(function_declaration name: (identifier) @name body: (statement_block) @body)]],
    typescript = [[(function_declaration name: (identifier) @name body: (statement_block) @body)]]
  }
  local qsrc = queries[ft]
  if not qsrc then return false, 'lang not supported' end
  local q = vim.treesitter.query.parse(lang, qsrc)
  for _, match in q:iter_matches(root, bufnr, 0, -1) do
    local name_node, body_node
    for cid, node in pairs(match) do
      local cap = q.captures[cid]
      if cap == 'name' then name_node = node end
      if cap == 'body' then body_node = node end
    end
    if name_node and body_node then
      local name = vim.treesitter.get_node_text(name_node, bufnr)
      if name == func_name then
        local srow, scol, erow, ecol = body_node:range()
        local indent = string.match(vim.api.nvim_buf_get_lines(bufnr, srow, srow+1, false)[1] or '', '^(%s*)') or ''
        local lines = {}
        for line in (new_body.."
"):gmatch("(.-)?
") do table.insert(lines, indent .. line) end
        vim.api.nvim_buf_set_lines(bufnr, srow, erow, false, lines)
        return true
      end
    end
  end
  return false, 'function not found'
end

function M.apply_ops(ops)
  for _, op in ipairs(ops or {}) do
    if op.action == 'create' then
      local path = op.path
      vim.fn.mkdir(vim.fn.fnamemodify(path, ':h'), 'p')
      vim.fn.writefile(vim.split(op.content or '', '
'), path)
    elseif op.action == 'edit' then
      local path = op.path
      local bufnr = vim.fn.bufnr(path)
      if bufnr == -1 then vim.cmd('edit '..path); bufnr = vim.api.nvim_get_current_buf() end
      if op.locator and op.locator.kind == 'function' and op.locator.name then
        local ok, err = M.replace_function_body(bufnr, op.locator.name, op.content or '')
        if not ok then vim.notify('Edit failed: '..tostring(err), vim.log.levels.WARN) end
      else
        local last = vim.api.nvim_buf_line_count(bufnr)
        vim.api.nvim_buf_set_lines(bufnr, last, last, false, vim.split(op.content or '', '
'))
      end
    end
  end
end

return M
```

## nvim/lua/aeiou/ui.lua — Intent Cards
```lua
-- add near bottom
function M.intent_card(card, on_do, on_defer, on_dismiss)
  local lines = { 'Intent: '..(card.title or card.goal or 'Task') }
  if card.why and #card.why>0 then table.insert(lines, 'Why: '..table.concat(card.why, '; ')) end
  table.insert(lines, 'Plan:')
  for _, step in ipairs(card.plan or {}) do table.insert(lines, '  • '..step) end
  table.insert(lines, 'Actions: [d]o  [f]later  [x]dismiss')
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local win = vim.api.nvim_open_win(buf, true, {relative='editor', style='minimal', border='rounded', width=math.min(72, math.floor(vim.o.columns*0.6)), height=#lines+2, row=2, col=2})
  vim.keymap.set('n','d', function() pcall(vim.api.nvim_win_close, win, true); if on_do then on_do() end end, {buffer=buf, nowait=true})
  vim.keymap.set('n','f', function() pcall(vim.api.nvim_win_close, win, true); if on_defer then on_defer() end end, {buffer=buf, nowait=true})
  vim.keymap.set('n','x', function() pcall(vim.api.nvim_win_close, win, true); if on_dismiss then on_dismiss() end end, {buffer=buf, nowait=true})
end
```

## nvim/lua/aeiou/impulse.lua — quorum → Intent Card and `/generate`
```lua
local M = {}
local http = require('aeiou.http')
local ui = require('aeiou.ui')
local edit = require('aeiou.edit')

local energy = 40

local function detect_signals()
  local bufnr = vim.api.nvim_get_current_buf()
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local text = table.concat(lines, '
')
  local signals = {}
  local todo = 0
  for _, l in ipairs(lines) do if l:match('%f[%w]TODO%f[%W]') then todo = todo + 1 end end
  if todo >= 1 then table.insert(signals, {type='TODO_PRESENT'}) end
  if #text > 0 and text:find('
%s*def%s+test_') == nil and vim.bo[bufnr].filetype == 'python' then
    table.insert(signals, {type='TEST_GAP'})
  end
  return signals
end

local function quorum(signals)
  local types = {}
  for _,s in ipairs(signals) do types[s.type]=true end
  if types.TODO_PRESENT and types.TEST_GAP then return 'ADD_TESTS' end
  return nil
end

local function heartbeat()
  local sigs = detect_signals()
  local action = quorum(sigs)
  if action == 'ADD_TESTS' then
    local card = { title='Add edge-case tests', why={'TODOs','No tests'}, plan={'Generate minimal tests','Run tests'} }
    ui.intent_card(card, function()
      local spec = { goal='add tests for current file', testing_strategy={'pytest minimal'}, constraints_inferred={'follow style'} }
      local ctx = { path = vim.api.nvim_buf_get_name(0), code = table.concat(vim.api.nvim_buf_get_lines(0,0,-1,false),'
') }
      http.post('/generate', { spec = spec, context = ctx }, function(ok, body)
        if not ok then return ui.toast('Generate failed','error') end
        edit.apply_ops(body.ops)
        ui.toast('Applied test scaffold','info')
      end)
    end)
  end
  vim.defer_fn(heartbeat, math.max(10000, 120000 - energy * 1000))
end

function M.setup()
  vim.api.nvim_create_autocmd('BufWritePost', function() energy = math.min(100, energy + 8) end)
  vim.api.nvim_create_autocmd('CursorHold', function() energy = math.max(0, energy - 5) end)
  heartbeat()
end

return M
```

## Optional: manual codegen command
```lua
-- nvim/plugin/aeiou.lua snippet
vim.api.nvim_create_user_command("AeiouGenerate", function()
  local http = require('aeiou.http')
  local ui = require('aeiou.ui')
  local edit = require('aeiou.edit')
  local spec = { goal='improve current function', constraints_inferred={'style'} }
  local ctx = { path = vim.api.nvim_buf_get_name(0), code = table.concat(vim.api.nvim_buf_get_lines(0,0,-1,false),'
') }
  http.post('/generate', { spec = spec, context = ctx }, function(ok, body)
    if not ok then return ui.toast('Generate failed','error') end
    edit.apply_ops(body.ops or {})
    ui.toast('Applied ops','info')
  end)
end, {})
```

## Updated Quick Start
- Sidecar: `uvicorn app.main:app --reload`
- Neovim: `require('aeiou').setup({ sidecar = { url = 'http://127.0.0.1:8000' } })`
- `:AeiouTranscode` → see spec; `:AeiouPanel` → panel; heartbeat may propose an **Intent Card**; `:AeiouGenerate` (optional) to test codegen.



---

# Extensions: multi‑file ops + language‑specific queries + test‑runner hook

## sidecar/app/main.py — extend `/generate` schema
```python
class GenerateIn(BaseModel):
    spec: dict
    context: dict | None = None

@app.post("/generate")
async def generate(inp: GenerateIn):
    sys = (
        "You generate precise code edits for a Neovim agent.
"
        "Respond ONLY with JSON: {\"ops\":[...]} where each op has action, path, optional locator, and content.
"
        "Ops can include creating new test files (e.g., tests/test_*.py) or editing existing ones.
"
        "Use locators where possible for AST-guided safety. Keep changes small and consistent with style."
    )
    user = "SPEC:
" + json.dumps(inp.spec) + "

CONTEXT:
" + json.dumps(inp.context or {})
    data = await llm.chat_json(sys, user, {"type":"object","properties":{"ops":{"type":"array"}},"required":["ops"]})
    if not isinstance(data, dict) or "ops" not in data:
        raise HTTPException(400, "Malformed ops")
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("INSERT INTO decisions(ts,project,spec) VALUES(?,?,?)",
                (int(time.time()), "default", json.dumps({"generated": data})))
    con.commit(); con.close()
    return data
```

## nvim/lua/aeiou/edit.lua — extend language queries
```lua
local queries = {
  python = [[(function_definition name: (identifier) @name body: (block) @body)]],
  javascript = [[(function_declaration name: (identifier) @name body: (statement_block) @body)]],
  typescript = [[(function_declaration name: (identifier) @name body: (statement_block) @body)]],
  go = [[(function_declaration name: (identifier) @name body: (block) @body)]]
}
```

## nvim/lua/aeiou/test.lua — simple runner
```lua
local M = {}

-- Run tests for current project (pytest, jest, go test)
function M.run(cb)
  local ft = vim.bo.filetype
  local cmd
  if ft == 'python' then cmd = { 'pytest', '-q' }
  elseif ft == 'javascript' or ft == 'typescript' then cmd = { 'npm', 'test', '--', '--silent' }
  elseif ft == 'go' then cmd = { 'go', 'test', './...' }
  else cb(false, 'No runner'); return end
  vim.fn.jobstart(cmd, {
    stdout_buffered = true,
    stderr_buffered = true,
    on_stdout = function(_, data)
      if cb then cb(true, table.concat(data, '
')) end
    end,
    on_stderr = function(_, data)
      if cb then cb(false, table.concat(data, '
')) end
    end
  })
end

return M
```

## nvim/lua/aeiou/impulse.lua — after apply_ops, trigger test runner
```lua
local test = require('aeiou.test')
-- inside ui.intent_card on_do handler after edit.apply_ops(...)
test.run(function(ok, out)
  if ok then ui.toast('Tests passed','info') else ui.toast('Tests failed: '..out,'error') end
end)
```

## Usage
- When quorum triggers, Intent Card may propose creating a new test file under `tests/`.
- `/generate` can now return ops like:
```json
{"ops":[{"action":"create","path":"tests/test_invoice.py","content":"def test_basic(): assert True"}]}
```
- AST‑guided edits work for Python, JS/TS, and Go.
- After applying ops, test runner hook executes automatically and reports pass/fail inline.

> Next steps: enrich context (imports, dependencies), smarter test diffing, and multi‑file reconciliation (group ops by dir/module).



---

# Extended: multi‑file ops, language coverage (TS/JS/Go), and a test‑runner hook

## sidecar/app/main.py — multi‑file codegen stays the same API
> `/generate` already accepts any number of ops. Here’s a stronger **system prompt** you can swap in to encourage multi‑file plans (e.g., create `tests/` files):
```python
sys = (
  "You generate precise code edits for a Neovim agent.
"
  "Respond ONLY with JSON {\"ops\":[...]} — each op has action(edit|create|delete), path, optional locator, and content.
"
  "Prefer small safe changes; KEEP USER STYLE.
"
  "OK to create NEW FILES under project (e.g., tests/test_*.py, __init__.py).
"
  "When adding tests, also add minimal fixtures if missing."
)
```

## NEW: sidecar/app/tests.py — simple local test runner
```python
# sidecar/app/tests.py
import subprocess, shlex, os, json, tempfile
from typing import Tuple

def run_cmd(cmd: str, cwd: str|None=None, timeout: int=30) -> Tuple[int,str,str]:
    p = subprocess.Popen(shlex.split(cmd), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill(); return 124, '', 'timeout'
    return p.returncode, out, err

LANG_RUNNERS = {
    'python': ['pytest', 'python -m pytest'],
    'javascript': ['npm test --silent', 'pnpm test --silent', 'yarn test --silent'],
    'typescript': ['npm test --silent', 'pnpm test --silent', 'yarn test --silent'],
    'go': ['go test ./...']
}

def detect_lang(root: str) -> str|None:
    if os.path.exists(os.path.join(root, 'go.mod')): return 'go'
    if os.path.exists(os.path.join(root, 'package.json')): return 'javascript'
    # naive: default to python if pytest.ini/pyproject
    if os.path.exists(os.path.join(root, 'pytest.ini')) or os.path.exists(os.path.join(root,'pyproject.toml')):
        return 'python'
    return None

def run_tests(root: str, lang: str|None=None) -> dict:
    lang = lang or detect_lang(root) or 'python'
    cmds = LANG_RUNNERS.get(lang, [])
    for cmd in cmds:
        code, out, err = run_cmd(cmd, cwd=root, timeout=120)
        if code in (0,1):
            return { 'lang': lang, 'code': code, 'stdout': out, 'stderr': err, 'cmd': cmd }
    return { 'lang': lang, 'code': 127, 'stdout': '', 'stderr': 'no runner succeeded', 'cmd': '' }
```

## sidecar/app/main.py — add `/run_tests`
```python
from .tests import run_tests

class RunTestsIn(BaseModel):
    root: str
    lang: str | None = None

@app.post('/run_tests')
async def run_tests_ep(inp: RunTestsIn):
    res = run_tests(inp.root, inp.lang)
    return res
```

## nvim/lua/aeiou/edit.lua — extend AST queries (TS/JS/Go) & add delete
```lua
-- extend queries map and add Go
local queries = {
  python = [[(function_definition name: (identifier) @name body: (block) @body)]],
  javascript = [[(function_declaration name: (identifier) @name body: (statement_block) @body)]],
  typescript = [[(function_declaration name: (identifier) @name body: (statement_block) @body)]],
  go = [[(function_declaration name: (identifier) @name body: (block) @body)]]
}
```
```lua
-- support delete ops
elseif op.action == 'delete' then
  local path = op.path
  if vim.fn.filereadable(path) == 1 then vim.fn.delete(path) end
  local bufnr = vim.fn.bufnr(path)
  if bufnr ~= -1 then vim.api.nvim_buf_delete(bufnr, { force = true }) end
```

## NEW: nvim/lua/aeiou/test.lua — call `/run_tests` and show quickfix
```lua
local M = {}
local http = require('aeiou.http')
local ui = require('aeiou.ui')

local function parse_pytest(out)
  local items = {}
  for file, line, msg in out:gmatch("([%w%._/%-]+):(%d+): ([^
]+)") do
    table.insert(items, { filename=file, lnum=tonumber(line), col=1, text=msg })
  end
  return items
end

function M.run(root)
  http.post('/run_tests', { root = root }, function(ok, body)
    if not ok then return ui.toast('Tests failed to run','error') end
    local code = body.code or 0
    local out = body.stdout or ''
    if code == 0 then
      ui.toast('Tests passed ✓','info')
      return
    end
    -- populate quickfix with best-effort parse (pytest style)
    local items = parse_pytest(out)
    if #items > 0 then
      vim.fn.setqflist({}, ' ', { title = 'AI test run', items = items })
      vim.cmd('copen')
    else
      ui.toast('Tests failed; open :messages for logs','warn')
    end
  end)
end

return M
```

## nvim/lua/aeiou/impulse.lua — after apply, run tests
```lua
-- inside the Do action callback after edit.apply_ops(...)
require('aeiou.test').run(vim.fn.getcwd())
```

## Improve `/generate` requests from impulse (multi‑file)
```lua
-- replace spec in Do callback with stronger ask
local spec = {
  goal='add tests for current file',
  testing_strategy={'pytest minimal'},
  constraints_inferred={'follow style','ok to create tests/test_<name>.py if missing'}
}
```

## Optional: manual multi‑file generation command
```lua
-- nvim/plugin/aeiou.lua
vim.api.nvim_create_user_command("AeiouScaffoldTests", function()
  local http = require('aeiou.http')
  local ui = require('aeiou.ui')
  local edit = require('aeiou.edit')
  local test = require('aeiou.test')
  local path = vim.api.nvim_buf_get_name(0)
  local ctx = { path = path, code = table.concat(vim.api.nvim_buf_get_lines(0,0,-1,false),'
') }
  local spec = { goal='create tests for current module', testing_strategy={'pytest minimal'}, constraints_inferred={'create tests/ if absent'} }
  http.post('/generate', { spec = spec, context = ctx }, function(ok, body)
    if not ok then return ui.toast('Generate failed','error') end
    edit.apply_ops(body.ops or {})
    test.run(vim.fn.getcwd())
  end)
end, {})
```

### Notes
- AST queries are deliberately minimal; expand per‑language over time (methods, classes, receivers for Go).
- Test parsing is best‑effort; for JS/Go, consider grepping `FAIL` lines and populating quickfix similarly.
- Multi‑file ops depend on the model following the contract; the stronger system prompt steers it.



---

# Next Extensions: diff narration, temp branch flow, expanded AST + test parsing

## VCS: ephemeral branches & diff narrator

### sidecar/app/gitwrap.py
```python
import subprocess, shlex, tempfile

def run(cmd, cwd=None):
    p = subprocess.Popen(shlex.split(cmd), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out.strip(), err.strip()

def ensure_branch(root: str, name: str = 'aeiou_tmp') -> str:
    run('git rev-parse --git-dir', cwd=root)
    run(f'git checkout -B {name}', cwd=root)
    return name

def commit_all(root: str, msg: str):
    run('git add -A', cwd=root)
    run(f'git commit -m "{msg}"', cwd=root)

def diff_summary(root: str, base: str = 'HEAD~1', head: str = 'HEAD') -> str:
    code, out, _ = run(f'git diff --unified=0 --stat {base} {head}', cwd=root)
    return out
```

### sidecar/app/main.py
```python
from . import gitwrap

class BranchIn(BaseModel):
    root: str
    msg: str = 'aeiou change'

@app.post('/commit_tmp')
async def commit_tmp(inp: BranchIn):
    br = gitwrap.ensure_branch(inp.root)
    gitwrap.commit_all(inp.root, inp.msg)
    return { 'branch': br, 'msg': inp.msg }

class DiffIn(BaseModel):
    root: str
    base: str = 'HEAD~1'
    head: str = 'HEAD'

@app.post('/diff_summary')
async def diff_summary_ep(inp: DiffIn):
    txt = gitwrap.diff_summary(inp.root, inp.base, inp.head)
    return { 'summary': txt }
```

### nvim/lua/aeiou/vcs.lua
```lua
local M = {}
local http = require('aeiou.http')
local ui = require('aeiou.ui')

function M.commit_tmp(root, msg)
  http.post('/commit_tmp', { root = root, msg = msg }, function(ok, body)
    if not ok then return ui.toast('Commit failed','error') end
    ui.toast('Committed to '..body.branch, 'info')
  end)
end

function M.diff_summary(root)
  http.post('/diff_summary', { root = root }, function(ok, body)
    if not ok then return ui.toast('Diff failed','error') end
    local lines = vim.split(body.summary or '', '
')
    vim.api.nvim_echo({{table.concat(lines,'
')}}, false, {})
  end)
end

return M
```

---

## Expanded AST: methods & receivers

### nvim/lua/aeiou/edit.lua
```lua
-- expand queries to capture methods/class methods/Go receivers
local queries = {
  python = [[
    (function_definition name: (identifier) @name body: (block) @body)
    (class_definition body: (block (function_definition name: (identifier) @name body: (block) @body)))
  ]],
  javascript = [[
    (function_declaration name: (identifier) @name body: (statement_block) @body)
    (method_definition name: (property_identifier) @name body: (statement_block) @body)
  ]],
  typescript = [[
    (function_declaration name: (identifier) @name body: (statement_block) @body)
    (method_definition name: (property_identifier) @name body: (statement_block) @body)
  ]],
  go = [[
    (function_declaration name: (identifier) @name body: (block) @body)
    (method_declaration name: (field_identifier) @name body: (block) @body)
  ]]
}
```

---

## Test parsing improvements

### nvim/lua/aeiou/test.lua
```lua
local function parse_go(out)
  local items = {}
  for file, line, msg in out:gmatch("([%w%._/%-]+):(%d+): ([^
]+)") do
    table.insert(items, { filename=file, lnum=tonumber(line), col=1, text=msg })
  end
  return items
end

local function parse_jest(out)
  local items = {}
  for file, line, msg in out:gmatch("at ([%w%._/%-]+):(%d+):%d+%s+([^
]+)") do
    table.insert(items, { filename=file, lnum=tonumber(line), col=1, text=msg })
  end
  return items
end

function M.run(root)
  http.post('/run_tests', { root = root }, function(ok, body)
    if not ok then return ui.toast('Tests failed to run','error') end
    local code = body.code or 0
    local out = body.stdout or ''
    if code == 0 then ui.toast('Tests passed ✓','info'); return end
    local items = parse_pytest(out)
    if #items == 0 then items = parse_jest(out) end
    if #items == 0 then items = parse_go(out) end
    if #items > 0 then
      vim.fn.setqflist({}, ' ', { title='AI test run', items=items })
      vim.cmd('copen')
    else
      ui.toast('Tests failed; see logs','warn')
    end
  end)
end
```

---

## Example Flow
- Agent applies ops → `vcs.commit_tmp()` → snapshot to temp branch.
- User can call `vcs.diff_summary()` or agent can auto‑narrate.
- Expanded AST queries let `/generate` ops target **class methods** or **Go receivers** precisely.
- Test runner now parses **pytest, jest, and go test** outputs into quickfix.

> Next: tie diff narration into Intent Cards (so each Do shows a bullet summary), and allow replay/rollback of past ops via the action log.



---

# Add: JS/Go quickfix parsing, richer AST locators, and temp‑branch + diff narrator

## sidecar/app/main.py — add `/diff_explain` (LLM risk/summary of git diff)
```python
from pydantic import BaseModel

class DiffIn(BaseModel):
    diff: str
    style: dict | None = None

@app.post('/diff_explain')
async def diff_explain(inp: DiffIn):
    sys = (
        "You are a senior engineer reviewing a git unified diff.
"
        "Summarize in 2–4 bullet points: what changed, potential risks, and impacted tests.
"
        "Be concise. No code blocks."
    )
    text = await llm.chat_text(sys, inp.diff)
    return {"summary": text}
```

## nvim/lua/aeiou/test.lua — add Jest/Go parsers and surface best‑effort failures
```lua
local M = {}
local http = require('aeiou.http')
local ui = require('aeiou.ui')

local function parse_pytest(out)
  local items = {}
  for file, line, msg in out:gmatch("([%w%._/%-]+):(%d+): ([^
]+)") do
    table.insert(items, { filename=file, lnum=tonumber(line), col=1, text=msg })
  end
  return items
end

local function parse_jest(out)
  local items = {}
  -- capture stack frames: at ... (path:line:col)
  for file, line, col in out:gmatch("%(([^
:]+%.[tj]sx?)%:(%d+)%:(%d+)%)") do
    table.insert(items, { filename=file, lnum=tonumber(line), col=tonumber(col), text='jest failure' })
  end
  -- fallback: FAIL path
  for file in out:gmatch("FAIL%s+([%w%._/%-]+%.[tj]sx?)") do
    table.insert(items, { filename=file, lnum=1, col=1, text='jest suite failed' })
  end
  return items
end

local function parse_gotest(out)
  local items = {}
  -- lines like: file.go:123: message
  for file, line, msg in out:gmatch("([%w%._/%-]+%.go):(%d+):%s*([^
]+)") do
    table.insert(items, { filename=file, lnum=tonumber(line), col=1, text=msg })
  end
  -- gather after FAIL: TestX blocks
  for blk in out:gmatch("%-%-%- FAIL:.-%-%-%- ") do
    for file, line in blk:gmatch("([%w%._/%-]+%.go):(%d+)") do
      table.insert(items, { filename=file, lnum=tonumber(line), col=1, text='go test failure' })
    end
  end
  return items
end

local function choose_parser(lang)
  if lang == 'python' then return parse_pytest
  elseif lang == 'javascript' or lang == 'typescript' then return parse_jest
  elseif lang == 'go' then return parse_gotest
  else return function(_) return {} end end
end

function M.run(root, lang)
  http.post('/run_tests', { root = root, lang = lang }, function(ok, body)
    if not ok then return ui.toast('Tests failed to run','error') end
    local code = body.code or 0
    local out = body.stdout or ''
    local used_lang = body.lang or lang or 'python'
    if code == 0 then
      ui.toast('Tests passed ✓','info')
      return
    end
    local items = choose_parser(used_lang)(out)
    if #items > 0 then
      vim.fn.setqflist({}, ' ', { title = 'AI test run', items = items })
      vim.cmd('copen')
    else
      ui.toast('Tests failed; check output','warn')
      vim.notify(out, vim.log.levels.WARN, { title = 'Test Output' })
    end
  end)
end

return M
```

## nvim/lua/aeiou/edit.lua — richer AST locators (methods & receivers)
```lua
-- Add support for locator.kind == 'method' with class/receiver
function M.replace_method(bufnr, locator, new_body)
  local ft = vim.bo[bufnr].filetype
  local lang = vim.treesitter.language.get_lang(ft)
  if not lang then return false, 'no treesitter lang' end
  local ok, parser = pcall(vim.treesitter.get_parser, bufnr, lang)
  if not ok then return false, 'no parser' end
  local tree = parser:parse()[1]
  local root = tree:root()
  if ft == 'python' then
    local q = vim.treesitter.query.parse(lang, [[
      (class_definition name: (identifier) @cls
        body: (block (function_definition name: (identifier) @name body: (block) @body) @m) @blk)
    ]])
    for _, match in q:iter_matches(root, bufnr, 0, -1) do
      local cls, name, body
      for cid, node in pairs(match) do
        local cap = q.captures[cid]
        if cap=='cls' then cls=node elseif cap=='name' then name=node elseif cap=='body' then body=node end
      end
      if cls and name and body then
        local clsname = vim.treesitter.get_node_text(cls, bufnr)
        local mname = vim.treesitter.get_node_text(name, bufnr)
        if clsname == locator.class and mname == locator.name then
          local srow, _, erow = body:range()
          local indent = string.match(vim.api.nvim_buf_get_lines(bufnr, srow, srow+1, false)[1] or '', '^(%s*)') or ''
          local lines = {}
          for line in (new_body.."
"):gmatch("(.-)?
") do table.insert(lines, indent .. line) end
          vim.api.nvim_buf_set_lines(bufnr, srow, erow, false, lines)
          return true
        end
      end
    end
  elseif ft == 'go' then
    local q = vim.treesitter.query.parse(lang, [[
      (method_declaration
        receiver: (parameter_list (parameter name: (identifier) @recv_name type: (type_identifier) @recv_type))
        name: (field_identifier) @name
        body: (block) @body)
    ]])
    for _, match in q:iter_matches(root, bufnr, 0, -1) do
      local rtype, name, body
      for cid, node in pairs(match) do
        local cap = q.captures[cid]
        if cap=='recv_type' then rtype=node elseif cap=='name' then name=node elseif cap=='body' then body=node end
      end
      if rtype and name and body then
        local T = vim.treesitter.get_node_text(rtype, bufnr)
        local m = vim.treesitter.get_node_text(name, bufnr)
        if T == (locator.receiver or locator.class) and m == locator.name then
          local srow, _, erow = body:range()
          local indent = string.match(vim.api.nvim_buf_get_lines(bufnr, srow, srow+1, false)[1] or '', '^(%s*)') or ''
          local lines = {}
          for line in (new_body.."
"):gmatch("(.-)?
") do table.insert(lines, indent .. line) end
          vim.api.nvim_buf_set_lines(bufnr, srow, erow, false, lines)
          return true
        end
      end
    end
  elseif ft == 'typescript' or ft == 'javascript' then
    local q = vim.treesitter.query.parse(lang, [[
      (class_declaration name: (identifier) @cls
        body: (class_body (method_definition name: (property_identifier) @name body: (statement_block) @body)+))
    ]])
    for _, match in q:iter_matches(root, bufnr, 0, -1) do
      local cls, name, body
      for cid, node in pairs(match) do
        local cap = q.captures[cid]
        if cap=='cls' then cls=node elseif cap=='name' then name=node elseif cap=='body' then body=node end
      end
      if cls and name and body then
        local C = vim.treesitter.get_node_text(cls, bufnr)
        local m = vim.treesitter.get_node_text(name, bufnr)
        if C == locator.class and m == locator.name then
          local srow, _, erow = body:range()
          local indent = string.match(vim.api.nvim_buf_get_lines(bufnr, srow, srow+1, false)[1] or '', '^(%s*)') or ''
          local lines = {}
          for line in (new_body.."
"):gmatch("(.-)?
") do table.insert(lines, indent .. line) end
          vim.api.nvim_buf_set_lines(bufnr, srow, erow, false, lines)
          return true
        end
      end
    end
  end
  return false, 'method not found'
end

-- In apply_ops, add a branch for locator.kind == 'method'
-- inside the edit branch:
--   if op.locator and op.locator.kind == 'method' then
--     M.replace_method(bufnr, op.locator, op.content or '')
```

## NEW: nvim/lua/aeiou/vcs.lua — temp branch workflow & diff narrator
```lua
local M = {}
local http = require('aeiou.http')
local ui = require('aeiou.ui')

local prev_branch, temp_branch

local function sys(cmd)
  return vim.fn.system(cmd)
end

local function chomp(s)
  return (s or ''):gsub('
+$','')
end

function M.ensure_temp_branch()
  local root = chomp(vim.fn.system('git rev-parse --show-toplevel'))
  if root == '' then return false, 'not a git repo' end
  prev_branch = chomp(vim.fn.system('git rev-parse --abbrev-ref HEAD'))
  if prev_branch:find('aeiou/') then
    temp_branch = prev_branch; return true
  end
  temp_branch = 'aeiou/'..os.time()
  local out = vim.fn.system('git checkout -b '..temp_branch)
  if vim.v.shell_error ~= 0 then return false, out end
  return true
end

function M.stage_all()
  vim.fn.system('git add -A')
end

function M.diff_staged()
  return chomp(vim.fn.system('git diff --staged'))
end

function M.commit(msg)
  vim.fn.system('git commit -m '..vim.fn.shellescape(msg))
  return vim.v.shell_error == 0
end

function M.abort()
  if not temp_branch or not prev_branch then return end
  vim.fn.system('git reset --hard')
  vim.fn.system('git checkout '..prev_branch)
  vim.fn.system('git branch -D '..temp_branch)
  temp_branch, prev_branch = nil, nil
end

function M.finish()
  -- remain on temp branch; user can merge manually later
  ui.toast('Changes committed to '..temp_branch, 'info')
end

function M.explain_and_confirm()
  M.stage_all()
  local diff = M.diff_staged()
  if diff == '' then ui.toast('No staged changes', 'warn'); return end
  http.post('/diff_explain', { diff = diff }, function(ok, body)
    local summary = ok and (body.summary or '') or 'Summary unavailable.'
    local lines = { 'Diff summary:', summary, '', 'Actions: [c]ommit  [a]bort' }
    local buf = vim.api.nvim_create_buf(false, true)
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
    local win = vim.api.nvim_open_win(buf, true, { relative='editor', style='minimal', border='rounded', width=math.min(90, math.floor(vim.o.columns*0.7)), height=math.min(#lines+2, math.floor(vim.o.lines*0.6)), row=2, col=2 })
    vim.keymap.set('n','c', function()
      pcall(vim.api.nvim_win_close, win, true)
      local msg = 'Apply AI changes'
      if M.commit(msg) then M.finish() else ui.toast('Commit failed','error') end
    end, {buffer=buf, nowait=true})
    vim.keymap.set('n','a', function()
      pcall(vim.api.nvim_win_close, win, true)
      M.abort(); ui.toast('Aborted changes','info')
    end, {buffer=buf, nowait=true})
  end)
end

return M
```

## nvim/lua/aeiou/impulse.lua — wrap Do‑action with temp branch + narrator
```lua
-- inside Do callback before applying ops
local vcs = require('aeiou.vcs')
local ok, err = vcs.ensure_temp_branch()
if not ok then return ui.toast('Git branch error: '..tostring(err), 'error') end
-- apply ops as before, then after tests pass call:
require('aeiou.test').run(vim.fn.getcwd())
-- then prompt commit/abort with narrated summary
vcs.explain_and_confirm()
```

### Notes
- Temp branch flow is conservative: we switch to `aeiou/<timestamp>`, stage changes, show a narrated summary, then **[c]ommit** or **[a]bort**. Merge back to main can be a later action.
- AST method replacement covers Python class methods, Go receiver methods, and TS/JS class methods. Expand with more node patterns over time.
- Quickfix parsing for Jest/Go is heuristic; it errs on surfacing likely locations rather than perfect mapping.

