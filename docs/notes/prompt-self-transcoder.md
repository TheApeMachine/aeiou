# Prompt Self-Transcoder for Code Generation

## Concept Overview

A **Prompt Self-Transcoder** is a small, open-weight model trained to convert a messy, human-written coding request into a **canonical, constraint-rich specification** that a larger code generation model can execute accurately.

The goal is not necessarily to produce "objectively good" code — instead, the transcoder learns *your* preferred style, patterns, and conventions from your own repositories.

Instead of you having to prompt-engineer every detail (“use dependency injection,” “follow my naming conventions,” “avoid framework X”), the transcoder automatically embeds these preferences into the spec before the main LLM starts writing.

---

## Why This Matters

### Without a transcoder

- You write a request in natural language.
- The LLM interprets it based on its general training distribution (which may not match your style at all).
- Output quality and style vary dramatically — sometimes clean, sometimes messy, often not *your* way.

### With a transcoder

1. Your request → **Small Model** → Canonical spec that includes:
   - Explicit goals and constraints from the prompt.
   - Inferred constraints based on your style profile.
   - Libraries, patterns, and formatting rules you prefer.
   - Known edge cases and testing patterns.
2. The **Large Model** generates code against the spec.
3. Output is consistent with your personal conventions without restating them every time.

---

## High-Level Architecture

```
User Prompt
   ↓
Prompt Self-Transcoder (Small Model, 3–8B params, LoRA-tuned on your repos)
   ↓
Canonical Spec (JSON, validated)
   ↓
Main Code Generation Model (Large LLM, general-purpose)
   ↓
Generated Code in Your Style
```

---

## Canonical Spec Schema (Example)

```json
{
  "goal": "string",
  "inputs": ["string"],
  "outputs": ["string"],
  "constraints_explicit": ["string"],
  "constraints_inferred": ["string"],
  "libraries_preferred": ["string"],
  "libraries_forbidden": ["string"],
  "style_guides": ["string"],
  "naming_conventions": ["string"],
  "design_patterns": ["string"],
  "testing_strategy": ["string"],
  "edge_cases": ["string"],
  "verbosity": "minimal|normal|verbose",
  "open_questions": ["string"]
}
```

---

## Data for Training

### Source: Your Existing Repositories

You have **156+ repositories** containing code in your preferred style.
We can leverage these to create `(prompt, spec)` pairs for training:

1. **Reverse-Distill Your Code**
   - Extract functions, classes, and modules.
   - Auto-generate specs describing their purpose, inputs, outputs, constraints, and style traits.
   - Generate *underspecified prompts* by stripping some details (simulating how you might actually request them).
   - Label the stripped details as `constraints_inferred`.

2. **Style Pattern Mining**
   - Automatically detect:
     - Naming conventions.
     - Preferred libraries.
     - Code formatting patterns.
     - Typical error-handling approaches.
     - Testing strategies.
   - Use these as defaults in inferred constraints.

3. **Augment With Synthetic Variations**
   - Rephrase prompts in multiple styles (casual, terse, verbose).
   - Introduce ambiguities to teach the transcoder to ask clarifying questions.

---

## Training Recipe

1. **Base Model**
   - Start with an instruction-tuned open-weight model (e.g., Llama-3.1-8B, Mistral-7B, Phi-3.5-Mini).
   - Quantize if running locally.

2. **Supervised Fine-Tuning (SFT)**
   - Train on your `(prompt, spec)` pairs.
   - Enforce strict JSON output via schema validation during training.

3. **Preference Optimization (Optional)**
   - Collect multiple spec candidates for the same prompt.
   - Pick the one that best matches your intent/style.
   - Fine-tune using Direct Preference Optimization (DPO) or rejection sampling.

---

## Inference-Time Workflow

1. **Prompt Capture**
   - User writes natural-language request.

2. **Spec Generation**
   - Small model outputs canonical spec in JSON.
   - If invalid, automatically retries until schema passes.

3. **Approval / Edit**
   - (Optional) Show spec in an IDE side panel for quick human edits.

4. **Code Generation**
   - Large LLM generates code using the approved spec.

5. **Testing & Linting**
   - Run your preferred linting tools and tests.
   - If failures, loop back with a concise defect report.

---

## Benefits

- **Consistency:** Always matches your personal style without repeating constraints.
- **Speed:** Less back-and-forth with the LLM.
- **Privacy:** Small model and style profile can run locally.
- **Control:** Explicit separation between explicit user requirements and inferred defaults.

---

## Next Steps

1. Extract 5–10k `(prompt, spec)` pairs from your existing repos.
2. Fine-tune a small model for spec generation.
3. Integrate into your IDE workflow (e.g., Cursor, VS Code).
4. Incrementally expand dataset and refine schema.
