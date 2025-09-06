# Development Plan — AEIOU Self‑Transcoder + LCCP MVP

## Phase 0 — Bootstrapping (Done)

- [x] Define canonical spec JSON schema (`schemas/canonical_spec.schema.json`).
- [x] Scaffold FastAPI sidecar with `/health` and `/transcode`.
- [x] Validate `/transcode` output against the schema.
- [x] Neovim plugin core with `setup()` and `:AeiouTranscode` command (`nvim/lua/aeiou/init.lua`).
- [x] Floating window UI to capture prompt and pretty‑print spec (`nvim/lua/aeiou/ui.lua`).
- [x] HTTP glue via `curl` job (`nvim/lua/aeiou/http.lua`).

## Phase 1 — L0 Watchers & Impulse Engine

- [ ] Heartbeat scheduler and editor/event hooks (BufWritePost, CursorHold).
- [ ] Watchers: duplication/complexity, test‑gap, security/license, TODO/dead code (light heuristics).
- [ ] Energy/attention budgets to regulate initiative frequency; quiet hours; max unsolicited prompts/hour.
- [ ] Quorum & escalation: fuse multi‑signals before surfacing; composable quorum predicates with tests.
- [ ] Safety caps: max tool‑chain length, runaway detection, kill‑switch.

## Phase 2 — L1 Interpreters & Transcoder

- [ ] Cluster signals → TaskSpec (goal, risk, cost, priority, open questions).
- [ ] Clarifying question generation when constraints are underspecified (surface in UI).
- [ ] Style profile loader (local JSON) → merge into `constraints_inferred`.
- [ ] Prompt Self‑Transcoder: parse explicit constraints (e.g., “avoid …” → `libraries_forbidden`).
- [ ] Support entering `inputs`/`outputs` interactively in the UI.
- [ ] Unit tests for spec generation and JSON Schema validation.

## Phase 3 — L2 Synthesizer & Orchestration

- [ ] Intent Cards (impact/cost/plan) with Do/Defer/Dismiss flow.
- [ ] Focus modes: Pair (narrated small steps), Background (quiet), Solo Batches.
- [ ] Background digests on a cadence (summaries of deferred/backlog items).
- [ ] Parallel subtask dispatch and reconcile rules.

## Model & IO Plumbing

- [ ] Provider abstraction (OpenAI today, pluggable later) with retries/backoff.
- [ ] Streaming responses into buffers; token/cost tracking.
- [ ] Prompt/versioning registry: system prompts, tool manifests; per‑project active profile.
- [ ] Audit which prompt/version produced each change.

## Context Window Manager

- [ ] Tree‑sitter/LSP extractors: current symbol, siblings, imports, callers/callees; outlines.
- [ ] Rolling chat memory with turn compression; focus‑stack for active tasks.
- [ ] Cost/latency budgeter: pick model/context size per task.

## Phase 4 — Project Graph & Memory

- [ ] Project Graph builder via LSP/Tree‑sitter (files → symbols → deps → owners).
- [ ] Embedded SQLite stores:
  - [ ] Relational: decisions, actions, style_profile, sessions.
  - [ ] Vector: embeddings(item_id, kind, dim, vec BLOB) + brute‑force cosine.
  - [ ] Graph: nodes/edges tables; indexes on (src,rel)/(dst,rel).
- [ ] Memory lifecycle: TTL/aging, compaction, pin/forget; redaction.
- [ ] RAG policy: token budgeter; summarize overflow.
- [ ] RAG enrichment into `constraints_inferred` (edge cases, examples, patterns).

## Phase 5 — Governance & Safety

- [ ] Tool permission model: allow/ask/deny per tool; ephemeral elevation per session.
- [ ] Atomic edit engine: AST‑guided where possible; single undo block; fuzzy‑patch fallback.
- [ ] Ephemeral branch workflow for multi‑file edits; merge/cleanup after approval.
- [ ] Policy hooks: forbidden APIs/licenses/security patterns.
- [ ] VCS ops: temp branches, commit/revert/squash; “explain this diff” narrator.
- [ ] Diff narrations (2–4 bullets + risk notes) and replayable action log.

## Phase 6 — Wild Ideas Lane (Curiosity Budget)

- [ ] Allocate small compute budget for alternative designs.
- [ ] Pilot Panel toggle: “Try a different approach?” presents safe variants.

## Phase 7 — Pilot Panel & UX

- [ ] Sidecar “Pilot Panel” UI: Intent Cards, digests, focus mode, status.
- [ ] Resizable/persistent panel; copy/export spec to file.
- [ ] Inline affordances: virtual‑text hints, gentle highlight fade, tiny spinner.
- [ ] Micro‑interactions: one‑keystroke Do/Defer/Dismiss; never steal focus.
- [ ] Theming: named highlight groups; subtle timer‑based animations.
- [ ] Graceful error toasts and sidecar status indicator.
- [ ] Config options (timeouts, model selection, endpoints).

## Voice I/O

- [ ] Push‑to‑talk capture in sidecar; Whisper API (local later) for STT.
- [ ] Earcons/TTS (optional): unobtrusive confirmations; configurable rate/pitch.
- [ ] Barge‑in: interrupt/adjust output while speaking.

## Phase 8 — Code Generation Loop

- [ ] Add `/generate` endpoint: large‑model codegen from approved spec.
- [ ] Neovim `:AeiouGenerate` to render code into a new buffer from `/generate`.
- [ ] Diff preview + apply flow (undo‑friendly, minimal intrusion).
- [ ] Test runner hook and concise defect loop back into the spec.

## Phase 9 — Metrics & Feedback

- [ ] Local telemetry: time‑to‑green, accept/revert/interruption rates, token/cost (SQLite).
- [ ] A/B prompt evaluation harness; replay fixtures; golden answers.
- [ ] Crash recovery: persistent job queue; resume after restart; orphan cleanup.
- [ ] Quality/velocity/collab feel/initiative/personalization metrics collection.
- [ ] Feedback loop: accept/decline rates inform initiative energy.

## Operational & Packaging

- [ ] Packaging/docs for the Neovim plugin (help file, README examples).
- [ ] Dev scripts for sidecar (venv, run, test) and Makefile.
- [ ] CI for sidecar (lint/type/test) and optional Lua format/lint.
- [ ] LICENSE and CONTRIBUTING.

## Security & Privacy

- [ ] Secrets handling: API key discovery, redaction in logs, project‑local .env.
- [ ] PII/code exfiltration guard: redact secrets in prompts; sandbox tool calls to project root.

## Notes

- Current components exist at:
  - Sidecar: `sidecar/app/main.py`, `sidecar/requirements.txt`.
  - Schema: `schemas/canonical_spec.schema.json`.
  - Neovim: `nvim/lua/aeiou/{init.lua,http.lua,ui.lua}`.
