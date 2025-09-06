# Layered Collaborative Coding Partner (LCCP)

**Author:** GPT-5 Thinking
**Date:** 2025-08-24
**Status:** Draft v1

---

## 0) Problem & Vision

Modern AI coding tools are linear: *prompt → monolithic output.* They feel like autocomplete, not a peer. We want a **truly collaborative partner** that:

- Works **non‑linearly** (discussion when needed; parallel solo work otherwise).
- Mixes **pair‑programming** and **divide‑and‑conquer**.
- Feels like a **peer**, not a text firehose; adapts to the room’s energy.
- Offers **creative alternatives**, not just likely continuations.
- Shows **initiative** via self‑reflection, research, experiments.

We propose a **layered, always‑on system** of small “engine” models feeding impulses upward to a large **Synthesizer** model that governs UX, planning, and conversation. Initiative emerges from continuous bottom‑up signals, not only top‑down prompts.

---

## 1) Goals & Non‑Goals

**Goals**

1. Produce a collaboration loop that feels human: adaptive, concise, context‑aware.
2. Enable parallelism: LLM and human can work independently, then reconcile.
3. Enforce *your* style by default (trained from your 156+ repos).
4. Surface “wild but plausible” alternatives safely, without noise.
5. Take initiative responsibly: propose, test, summarize, ask when needed.

**Non‑Goals**

- Replace the IDE or VCS entirely. LCCP integrates with them.
- Do unbounded web crawling. Any external search is gated and logged.
- Act without guardrails: destructive changes require explicit approval.

---

## 2) High‑Level Architecture

```
            ┌───────────────────────────────────────────────────┐
            │                 L2: SYNTHESIZER (Large)           │
            │  • Conversational UI & governance                 │
User ↔ IDE  │  • Planning/dispatch • Merge/reconcile            │
──────────▶ │  • Style memory • Intent cards • Summaries        │
            └────────────▲───────────────────────┬──────────────┘
                         │                       │ signals/tasks
                         │                       │
            ┌────────────┴───────────────────────▼──────────────┐
            │                 L1: INTERPRETERS (Small)           │
            │  • Cluster L0 signals → TaskSpecs                  │
            │  • Prioritize/score • Ask clarifying Qs            │
            │  • Draft tests/specs • Route to tools              │
            └────────────▲───────────────────────┬──────────────┘
                         │                       │ observations
                         │                       │
            ┌────────────┴───────────────────────▼──────────────┐
            │                  L0: WATCHERS (Tiny)               │
            │  • AST/LSP diffs • Linters • Dup/complexity        │
            │  • Test gaps • Dep/License • TODO/Dead code        │
            │  • Sandbox probes • Telemetry (typing/idle)        │
            └────────────────────────────────────────────────────┘
```

**Always‑on impulse:** L0 emits lightweight signals on a heartbeat and on file/branch events. L1 turns noise into actionable **TaskSpecs**. L2 decides *what to do now*, *what to run in parallel*, and *what to surface to you*.

---

## 3) Driving the System (Initiative Mechanics)

**3.1 Heartbeat & Events**

- **Heartbeat:** L0 runs every *t* (adaptive: 10–120s) and on events (file save, branch switch, test fail, CI signal).
- **Event types:** `FILE_CHANGED`, `TEST_FAILED`, `NEW_TODO`, `DUP_BLOCK_FOUND`, `SEC_ALERT`, `USER_IDLE`, `USER_FLOW` (typing burst), `PR_OPENED`, `CI_RED`.

**3.2 Attention & Energy Policy**

- Maintain a scalar **energy** ∈ [0,100] that controls initiative frequency.
  - ↑ with `CI_RED`, accumulating TODOs, repeated local failures.
  - ↓ with `USER_FLOW` (you’re typing fast), recent declines, quiet hours.
- **Attention budget** per hour limits surfaced items; excess is batched into digests.

**3.3 Quorum & Escalation**

- A signal escalates only if **quorum** satisfied: e.g., `duplication` + `low test coverage` + `recent bug` hitting same module.
- L1 fuses signals and proposes an **Intent Card** (one‑screen summary with impact, cost, plan, and “Do/Defer/Dismiss”).

**3.4 Curiosity Budget (Wild Ideas Lane)**

- Allocate a small time/compute budget (e.g., 5% of cycles) to counterfactual designs.
- L2 surfaces these behind a **“Try a Different Approach?”** toggle.

**3.5 Focus Modes**

- **Pair Mode:** L2 co‑edits and narrates small steps.
- **Background Mode:** L0/L1 work quietly; L2 delivers concise digests.
- **Solo Batches:** You assign chunks; L2 orchestrates subtasks + merge requests.

---

## 4) Data & Memory

**Project Graph**

- Directed graph of files → symbols → tests → dependencies → owners.
- Built via LSP + tree‑sitter + static analysis; updated incrementally.

**Style Profile (Personalization)**

- Learned from your 156 repos: naming, imports, libraries, patterns, folder layout, testing idioms, docstring style, commit voice.
- Stored as a versioned JSON config + embeddings; editable in UI.

**Session Memory**

- Short‑term: current tasks, decisions, and open questions.
- Long‑term: accepted patterns, banned patterns, recurring traps.
- All memory defaults to **local first**; cloud sync optional.

---

## 5) Schemas (Core Contracts)

**5.1 Signal (from L0)**

```json
{
  "type": "DUP_BLOCK_FOUND|TEST_GAP|SEC_ALERT|...",
  "file": "path/to/file.py",
  "span": [line_start, line_end],
  "evidence": {"hash": "abc", "metric": 0.82},
  "confidence": 0.78,
  "impact_hint": "maintainability|correctness|security",
  "links": ["repo://commit/123"],
  "timestamp": 1699999999
}
```

**5.2 TaskSpec (from L1)**

```json
{
  "goal": "Refactor UserModel to remove duplication in validation.",
  "context": {"module": "users/models.py", "deps": ["validators.py"]},
  "constraints_explicit": ["no external deps"],
  "constraints_inferred": ["follow personal style profile v3"],
  "acceptance_tests": ["existing unit tests stay green"],
  "risk": "low|med|high",
  "cost_estimate": "S|M|L",
  "priority": 0.74,
  "open_questions": ["Prefer dataclass or pydantic?"],
  "work_units": [
    {"id": "WU-1", "type": "patch", "plan": "extract validate_email()"},
    {"id": "WU-2", "type": "tests", "plan": "add edge-case emails"}
  ]
}
```

**5.3 Patch Proposal (from L2 or tool)**

```json
{
  "branch": "lccp/refactor/user-model",
  "diff": "<unified diff>",
  "summary": "Extracted validate_email; reduced duplication by 2x.",
  "checks": {"lint": "pass", "tests": "32/32 pass"}
}
```

**5.4 Intent Card (UI unit)**

```json
{
  "title": "Refactor UserModel duplication",
  "why": ["dup block detected", "low coverage", "recent bug #341"],
  "plan": ["extract helper", "add tests"],
  "cost": "S",
  "impact": "maintainability",
  "actions": ["Do now", "Defer", "Dismiss", "Open details"]
}
```

---

## 6) Layer Responsibilities

**L0 Watchers (Tiny models + heuristics)**

- AST & token‑level duplication; cyclomatic complexity; long function smell.
- Test gap detector (files without tests, mutated code not covered).
- Security & license scanners (semgrep/bandit; SPDX).
- TODO/`FIXME` tracker; dead code finder.
- Sandbox probes: run small inputs in a hermetic REPL to check basic behavior.
- Telemetry: editor state (typing/idle), recent command palette actions.

**L1 Interpreters (Small models, 1–8B)**

- Cluster signals → coherent TaskSpecs; resolve duplicates; rank by impact.
- Generate succinct clarifying questions when info is missing.
- Draft acceptance tests; propose minimal plans (WorkUnits).
- Maintain the Project Graph; detect dependency ripples.
- **Prompt Self‑Transcoder** for your style: turns vague asks → canonical specs using your style profile.

**L2 Synthesizer (Large model)**

- Conversational interface (pair mode) and governance (approval gates).
- Plan/dispatch parallel subtasks; decide Pair vs Background vs Solo.
- Generate/critique patches; narrate changes in 2–4 bullets, not walls of text.
- Manage initiative via energy policy; schedule digests; gate wild ideas.
- Owns merges: ephemeral branches, conflict resolution proposals, commit messages in your voice.

---

## 7) UX: Is this an Editor or Something Else?

**Answer: It’s a Sidecar + Plugin.**

- **IDE Plugin (VS Code/Cursor):** inline code actions, gutter hints, quick‑fixes, diff preview, in‑editor chat.
- **Sidecar “Pilot Panel”:** a compact window that shows Intent Cards, digests, focus mode, and a scratchpad timeline. Lets you peek at background work without spam.
- **Terminal Tools:** `lccp suggest`, `lccp apply`, `lccp digest`, `lccp wild` for CLI‑first users.

Why not a new editor? Leverage existing muscle memory; keep LCCP focused on collaboration and orchestration.

---

## 8) Planning & Scoring

**Priority score** *(normalized to [0,1])*:

```
score = w1*Impact + w2*Confidence - w3*Cost + w4*HygieneUrgency + w5*UserPriority
```

- Impact: predicted reduction in risk/complexity; perf improvements.
- Confidence: alignment of signals; test evidence; historical success.
- Cost: estimated work; blast radius.
- HygieneUrgency: compounding debt signals.
- UserPriority: explicit boosts set by you.

**Dispatch**

- High‑score tasks become **Immediate Actions** (ask once, apply small patch).
- Medium → **Intent Cards** (Do/Defer/Dismiss).
- Low → **Digest backlog** (batch summaries; snooze).

---

## 9) Guardrails & Safety

- All writes on **ephemeral branches**; PRs require confirmation beyond N lines.
- **Policy hooks:** forbidden APIs, license boundaries, security patterns.
- **Diff narrations**: always accompany patches with 2–4 bullets and risk notes.
- **Replayable log**: every action is reproducible from the timeline.

---

## 10) MVP Slice (90 days)

**Phase 1 (Weeks 1–4)**

- L0: duplication, linter, test‑gap watchers; Project Graph builder.
- L1: basic TaskSpec clustering + priority; 1–2 clarifying Qs.
- L2: Synthesizer that surfaces Intent Cards; applies small fixes.
- Sidecar Panel with digest and Do/Defer/Dismiss.

**Phase 2 (Weeks 5–8)**

- Personal **Style Profile** miner from your repos.
- Prompt Self‑Transcoder (small model) trained on `(prompt→spec)` pairs from your code.
- Ephemeral branch flow; unit test drafting for changed code.

**Phase 3 (Weeks 9–12)**

- Wild Ideas lane with curiosity budget.
- Parallel subtasks & reconcile; commit voice mimic.
- Metrics dashboard & feedback loop.

---

## 11) Metrics

- **Quality:** linter errors, test pass rate, defect escape rate.
- **Velocity:** time‑to‑green PR, edits to acceptance, back‑and‑forth count.
- **Collab feel:** average length of messages (shorter is better), accept rate of Intent Cards, user interruption rate.
- **Initiative:** % of useful unsolicited patches; decline rate (lower over time as it learns).
- **Personalization:** distance to style profile (naming, imports, structure).

---

## 12) Risks & Mitigations

- **Over‑initiative/noise:** Energy/attention budgets; quorum gates; digests.
- **Hallucinated constraints:** split explicit vs inferred; require confirmation for inferred‑only tasks.
- **Compute creep:** tiny L0 models; batched evaluation; adaptive heartbeat.
- **Merge conflicts:** small patches; frequent syncs; conflict simulation before proposal.
- **Security/privacy:** local‑first processing; redaction; explicit opt‑in for external search.

---

## 13) Implementation Notes

- **Models:** L0 tiny (rule‑based + distilled 0.5–1B); L1 small (1–8B LoRA); L2 large (API or local if feasible).
- **Runtimes:** Dockerized sandbox for tests; language servers for AST; git for branches.
- **Storage:** SQLite/Parquet for signals + Project Graph; embeddings store for style/profile.
- **APIs:** gRPC/IPC between plugin ↔ sidecar; JSON schemas above as contracts.

---

## 14) Example Interaction (Happy Path)

1. You code the new `InvoiceService` method. Save.
2. L0 emits: `DUP_BLOCK_FOUND` (copy‑paste across 2 files), `TEST_GAP` (no edge‑case tests).
3. L1 clusters → TaskSpec: "Extract common validator; add tests for zero/negative amounts" (cost S, impact maintainability).
4. L2 surfaces an **Intent Card**: *“Quick refactor + 2 tests? 30s to apply.”* Actions: Do/Defer/Dismiss.
5. You click **Do**. L2 creates branch, applies patch, runs tests, narrates:
   - Extracted `validate_amount` to `validation.py`.
   - Reduced dup 2→1 blocks; all tests green.
   - Added edge‑case tests.
6. You accept and continue coding; a digest summarizes background tasks every ~15 min.

---

## 15) Roadmap Beyond MVP

- Multi‑repo/project awareness; cross‑service changesets.
- Live design sessions with whiteboard → code scaffolds.
- Team mode: different style profiles per member; consent‑based knowledge sharing.
- On‑device speech pair‑programming; eye‑on‑screen attention heuristics.

---

## Appendix A: Clarifying Question Template

- Use when `constraints_explicit` are under‑specified *and* risk ≥ medium.

```
“What’s your preference here?”
• Error handling: raise vs return Result
• Sync vs async
• Library: requests vs httpx
• Data model: dataclass vs pydantic
```

## Appendix B: Personal Style Profile (Sketch)

```json
{
  "language_prefs": {"python": {"imports": ["pathlib", "dataclasses"], "http": "httpx"}},
  "naming": {"functions": "snake_case", "classes": "PascalCase"},
  "patterns": ["dependency_injection", "pure_functions_first"],
  "testing": {"framework": "pytest", "style": "arrange_act_assert"},
  "docs": {"docstring": "google", "examples_required": true},
  "commit_voice": {"tense": "imperative", "emoji": false}
}
```
