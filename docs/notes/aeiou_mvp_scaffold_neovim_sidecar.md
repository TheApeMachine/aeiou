# AEIOU MVP Scaffold — Neovim Plugin + FastAPI Sidecar

> Drop-in starter repo tree with minimal, working code you can extend. All local/embedded, no extra DB services.

```text
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

## schemas/canonical_spec.schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CanonicalSpec",
  "type": "object",
  "required": ["goal"],
  "properties": {
    "goal": {"type": "string"},
    "inputs": {"type": "array", "items": {"type": "string"}},
    "outputs": {"type": "array", "items": {"type": "string"}},
    "constraints_explicit": {"type": "array", "items": {"type": "string"}},
    "constraints_inferred": {"type": "array", "items": {"type": "string"}},
    "libraries_preferred": {"type": "array", "items": {"type": "string"}},
    "libraries_forbidden": {"type": "array", "items": {"type": "string"}},
    "style_guides": {"type": "array", "items": {"type": "string"}},
    "naming_conventions": {"type": "array", "items": {"type": "string"}},
    "design_patterns": {"type": "array", "items": {"type": "string"}},
    "testing_strategy": {"type": "array", "items": {"type": "string"}},
    "edge_cases": {"type": "array", "items": {"type": "string"}},
    "verbosity": {"type": "string"},
    "open_questions": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": true
}
```

---

## sidecar/requirements.txt

```txt
fastapi
uvicorn[standard]
pydantic>=2
httpx
numpy
sounddevice; sys_platform != 'win32'
python-dotenv
jsonschema
```

---

## sidecar/app/llm.py

```python
import os, httpx, json
OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("AEIOU_MODEL", "gpt-4o-mini")

async def chat_json(system: str, user: str, schema: dict) -> dict:
    """Call OpenAI and coerce JSON output (tool-free, lightweight)."""
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    prompt = (
        "You are a Prompt Self-Transcoder. Output ONLY a JSON object matching this schema.\n"
        + json.dumps(schema)
        + "\nUser request:"
        + user
    )
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
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
            # best-effort JSON extraction
            start = txt.find("{"); end = txt.rfind("}")
            if start >=0 and end > start:
                return json.loads(txt[start:end+1])
            raise
```

---

## sidecar/app/vectors.py

```python
import sqlite3, json, struct, math
from typing import List, Tuple

DB="aeiou.db"

def _ensure_tables():
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS embeddings(
      item_id TEXT, kind TEXT, dim INT, vec BLOB, meta JSON,
      PRIMARY KEY(item_id, kind)
    );
    """)
    con.commit(); con.close()

def upsert_embedding(item_id: str, kind: str, vec: List[float], meta: dict|None=None):
    _ensure_tables()
    blob = struct.pack(f"{len(vec)}f", *vec)
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("REPLACE INTO embeddings(item_id,kind,dim,vec,meta) VALUES(?,?,?,?,?)",
                (item_id, kind, len(vec), blob, json.dumps(meta or {})))
    con.commit(); con.close()

def _blob_to_vec(blob) -> List[float]:
    return list(struct.unpack(f"{len(blob)//4}f", blob))

def search_similar(query: List[float], kind: str, topk:int=6) -> List[Tuple[float,str,dict]]:
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.execute("SELECT item_id, dim, vec, meta FROM embeddings WHERE kind=?", (kind,))
    rows=cur.fetchall(); con.close()
    def norm(v):
        s=sum(x*x for x in v); return math.sqrt(s) if s>0 else 1.0
    qn = norm(query); results=[]
    for item_id, dim, blob, meta in rows:
        v = _blob_to_vec(blob)
        if len(v)!=len(query):
            continue
        vn = norm(v)
        cos = sum(a*b for a,b in zip(query,v))/(qn*vn)
        results.append((cos, item_id, json.loads(meta or '{}')))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:topk]
```

---

## sidecar/app/voice.py (stub)

```python
import sys
try:
    import sounddevice as sd, queue, numpy as np
except Exception:
    sd=None; queue=None; np=None

def record(seconds=4, samplerate=16000):
    if not sd: return b""  # disabled on this platform
    q = queue.Queue()
    def cb(indata, frames, time, status): q.put(indata.copy())
    with sd.InputStream(samplerate=samplerate, channels=1, callback=cb):
        sd.sleep(int(seconds*1000))
    audio = np.concatenate(list(q.queue), axis=0).astype(np.float32).tobytes()
    return audio
```

---

## sidecar/app/main.py

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

@app.on_event("startup")
def init_db():
    con=sqlite3.connect(DB); cur=con.cursor()
    cur.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS decisions(
      id INTEGER PRIMARY KEY, ts INTEGER, project TEXT, spec JSON
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
```

---

## nvim/plugin/aeiou.lua

```lua
-- Minimal command wiring
vim.api.nvim_create_user_command("AeiouTranscode", function()
  require('aeiou').transcode_prompt()
end, { nargs = 0 })

vim.api.nvim_create_user_command("AeiouPanel", function()
  require('aeiou.ui').toggle_panel()
end, {})
```

---

## nvim/lua/aeiou/init.lua

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

return M
```

---

## nvim/lua/aeiou/http.lua

```lua
local M = {}
local json = vim.json or { encode = vim.fn.json_encode, decode = vim.fn.json_decode }
local cfg = function() return require('aeiou').config end

local function job(cmd, on_exit)
  vim.fn.jobstart(cmd, { stdout_buffered = true, stderr_buffered = true,
    on_stdout = function(_, data) end,
    on_stderr = function(_, data) end,
    on_exit = function(_, code)
      on_exit(code)
    end })
end

local function curl(method, path, lua_tbl, cb)
  local url = cfg().sidecar.url .. path
  local body = lua_tbl and json.encode(lua_tbl) or ''
  local tmp = vim.fn.tempname()
  local cmd = { 'curl', '-sS', '-X', method, url, '-H', 'Content-Type: application/json',
    '-d', body, '-o', tmp }
  job(cmd, function(code)
    local ok = code == 0
    local resp = {}
    if ok then
      local content = table.concat(vim.fn.readfile(tmp), '\n')
      pcall(function() resp = json.decode(content) end)
    else resp = { error = 'curl error' } end
    os.remove(tmp)
    cb(ok, resp)
  end)
end

function M.post(path, tbl, cb) curl('POST', path, tbl, cb) end
function M.get(path, cb) curl('GET', path, nil, cb) end
return M
```

---

## nvim/lua/aeiou/ui.lua

```lua
local M = {}
local ns = vim.api.nvim_create_namespace('aeiou')
local panel_win, panel_buf

local function center_float(lines)
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local w = math.min(84, math.floor(vim.o.columns * 0.6))
  local h = math.min(#lines + 2, math.floor(vim.o.lines * 0.5))
  vim.api.nvim_open_win(buf, true, {
    relative='editor', style='minimal', border='rounded',
    width=w, height=h, row=math.floor((vim.o.lines-h)/2), col=math.floor((vim.o.columns-w)/2)
  })
end

function M.toast(msg, level)
  vim.notify(msg, level == 'error' and vim.log.levels.ERROR or vim.log.levels.INFO, { title = 'AEIOU' })
end

function M.prompt_input(prompt, cb)
  vim.ui.input({ prompt = prompt }, cb)
end

function M.show_spec(spec)
  local lines = { 'Canonical Spec:' }
  local function add(k, v)
    if v == nil then return end
    if type(v) == 'table' then
      table.insert(lines, ('- %s:'):format(k))
      for _, item in ipairs(v) do table.insert(lines, ('  • %s'):format(item)) end
    else table.insert(lines, ('- %s: %s'):format(k, tostring(v))) end
  end
  add('goal', spec.goal)
  add('inputs', spec.inputs)
  add('outputs', spec.outputs)
  add('constraints_explicit', spec.constraints_explicit)
  add('constraints_inferred', spec.constraints_inferred)
  add('open_questions', spec.open_questions)
  center_float(lines)
end

function M.toggle_panel()
  if panel_win and vim.api.nvim_win_is_valid(panel_win) then
    vim.api.nvim_win_close(panel_win, true); panel_win=nil; panel_buf=nil; return
  end
  panel_buf = vim.api.nvim_create_buf(false, true)
  panel_win = vim.api.nvim_open_win(panel_buf, false, {
    relative='editor', style='minimal', border='single',
    row=1, col=vim.o.columns-50, width=48, height=math.floor(vim.o.lines*0.7)
  })
  vim.api.nvim_buf_set_lines(panel_buf, 0, -1, false, { 'AEIOU Pilot Panel', '—', 'idle…' })
end

return M
```

---

## nvim/lua/aeiou/impulse.lua

```lua
local M = {}
local energy = 40

local function heartbeat()
  local ui = require('aeiou.ui')
  -- placeholder: later call sidecar for suggestions
  if energy > 70 then ui.toast('Idea: add tests for changed file?', 'info') end
  vim.defer_fn(heartbeat, math.max(10000, 120000 - energy * 1000))
end

function M.setup()
  vim.api.nvim_create_autocmd('BufWritePost', {
    callback = function(args)
      energy = math.min(100, energy + 8)
    end
  })
  vim.api.nvim_create_autocmd('CursorHold', {
    callback = function() energy = math.max(0, energy - 5) end
  })
  heartbeat()
end

return M
```

---

## nvim/lua/aeiou/ts.lua

```lua
local M = {}
function M.toplevel_symbols(bufnr)
  local ft = vim.bo[bufnr].filetype
  local lang = vim.treesitter.language.get_lang(ft)
  if not lang then return {} end
  local ok, parser = pcall(vim.treesitter.get_parser, bufnr, lang)
  if not ok then return {} end
  local tree = parser:parse()[1]
  local root = tree:root()
  local syms = {}
  local query_str = [[
    (function_definition name: (identifier) @name)
    (class_definition name: (identifier) @name)
  ]]
  local q = vim.treesitter.query.parse(lang, query_str)
  for _, match in q:iter_matches(root, bufnr, 0, -1) do
    for id, node in pairs(match) do
      local name = vim.treesitter.get_node_text(node, bufnr)
      table.insert(syms, name)
    end
  end
  return syms
end
return M
```

---

## Quick Start

1) **Sidecar**

```bash
cd sidecar
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-... # or set in .env
uvicorn app.main:app --reload
```

2) **Neovim**

- Put `nvim/` files into your runtime (or packer/lazy.nvim plugin dir).
- In `init.lua` (or equivalent):

```lua
require('aeiou').setup({ sidecar = { url = 'http://127.0.0.1:8000' } })
```

- Run `:AeiouTranscode` → enter a task → spec float appears.
- Run `:AeiouPanel` to toggle the side panel.

3) **Next Hooks to Implement**

- Call `/transcode` from the heartbeat based on events/quorum.
- Add test runner tools and AST-guided edit patches.
- Wire vector/graph upserts from Tree-sitter + LSP walkers.

> This is intentionally minimal but real. Extend `main.py` with `/generate`, add policy, and evolve the panel into Intent Cards. All storage is SQLite/built-in; no external services required aside from the LLM API.
