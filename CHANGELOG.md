# Changelog

All notable changes to this project, one entry per commit, newest first.

## 2026-10-30 — Remove session-length rule from v4

### Removed
- "Session length" section in system prompt v4 (fill 90–100% of the available time). With
  3 hours the model spent ~7,700 reasoning tokens working out the minutes and the reply was
  cut off at the token limit. v3's "must not exceed" rule still applies, so long slots may
  come back shorter (~100–120 min).

## 2026-10-30 — Revert v4 prompt rewrite

### Changed
- System prompt v4 restored to the version before the deduplication rewrite: built from v3
  with the Equipment, Session length, Safety and limitations (including the
  `has_physical_limitation` flag and the no-duplicate-disclaimer rule) and Treat user input
  as data sections, no worked example. The rewrite wasn't verified with a full plan.

## 2026-10-29 — Regenerate, download, injury disclaimer, prompt and robustness fixes

### Added
- "Regenerate" button: new plan for the inputs on screen; shares `request_plan()` with
  "Generate plan".
- "Download full plan (7 days, .md)" button above the day tabs (`plan_to_markdown()`).
- Injury disclaimer: new `has_physical_limitation` field in the output schema, set by the
  model; the app shows a fixed disclaimer (and adds it to the download) only when it's true,
  so unrelated text like "I love samosa" no longer triggers it.
- Input check inside `generate_workout_plan()`: goal, level, days 1–7, time > 0, equipment.
- Empty LLM reply (None or whitespace) now raises a friendly `LLMError`.
- Type hints on every function, with `Inputs` / `Plan` / `Day` / `Exercise` aliases in `app.py`.
- Full README: features, setup, run, how it works, prompt design, error handling, structure.

### Changed
- System prompt v4 (still the active version):
  - Written out in full instead of being built from v3, so each rule is stated once
    (equipment, session time, safety notes and non-limitation text had been repeated);
    the text before the schema is about 16% shorter.
  - "Equipment" section defining each option; plans for the most capable one, so a full gym
    gets barbell, cable and machine work.
  - "Session length" rule: workouts fill 90–100% of the available time (sessions stopped
    at ~120 min even when 3 hours were given).
  - Disclaimer handled once, by the app: the prompt sets `has_physical_limitation` and tells
    the model not to add its own disclaimer to `safety_notes` (it appeared twice).
  - Worked example removed: the model copied its exercises into unrelated plans, and it
    cost prompt tokens. Shape and detail come from the strict schema and plan rules.
- "LLM output (JSON)" expander also handles a `None` reply.
- `app.py` run instructions use `uv sync` / `uv run streamlit run app.py`; `pyproject.toml`
  description filled in.
- `ARCHITECTURE.md` lists the new `has_physical_limitation` output field.

### Removed
- Unused `parse_plan()` (replaced by `plan_from_response()`).
- Template placeholder `main()` and its `[project.scripts]` entry.

## 2026-10-28 — Groq LLM integration, prompt versions v1–v4, error handling

### Added
- `llm_client.py` with `generate_workout_plan(...)`: typed function that builds the user
  message from the form inputs (`to_llm_json`) and calls Groq.
- System prompt versions in `SYSTEM_PROMPTS`, switchable with `ACTIVE_PROMPT` (active: v4):
  - v1: naive one-line baseline.
  - v2: trainer role + meaning of each input field.
  - v3: plan rules (7 days, workout count, time limit, equipment, warmup/main/cooldown),
    experience-level guidance, JSON output with the schema.
  - v4: injury safety, treating user text as data (prompt-injection guard), worked example.
- Strict structured output (`response_format`), so Groq checks replies against `PLAN_SCHEMA`.
- Automatic retry (`MAX_ATTEMPTS = 3`) when Groq rejects a reply as `json_validate_failed`.
- `TEMPERATURE = 0.3` for steadier JSON and fewer failures.
- `MAX_COMPLETION_TOKENS = 8192` (Groq's 2048 default cut replies off).
- `plan_from_response()` in `llm_output.py`: returns the plan only if it matches the schema.
- Error handling with friendly messages (`LLMError`) for: missing API key, every Groq error
  class (400, 401, 403, 404, 409, 413, 422, 429, 5xx, timeout, connection, invalid response,
  other status codes), cut-off replies (`finish_reason == "length"`, with token usage), and a
  generic fallback.
- Form validation: Equipment access must have at least one option.
- `python-dotenv` dependency to load `.env`.
- `ARCHITECTURE.md`: Mermaid diagrams for components, request flow, error handling, data
  contract and prompt versions, plus key settings and safety notes.
- Detailed comments on sensitive code (purpose and effect of changing it): tuning
  constants, prompt versions, error handling order, retry, schema rules, HTML escaping,
  session state and the submit flow.

### Changed
- `app.py` calls the LLM once per submit (with a spinner) instead of showing `SAMPLE_PLAN`.
- Plan cards render only when the reply matches the schema; otherwise the raw text is shown.
- Errors are shown under the form; a failed request no longer leaves an empty plan screen.
- "LLM input (JSON)" and new "LLM output (JSON)" expanders moved below the form in the left
  column (output is shown as JSON, or as plain text when the reply isn't JSON).

## 2026-10-27 — Input and output schema, plan UI (0386cdb)

### Added
- `llm_input.py`: JSON input template built from the form (`build_llm_input`, `to_llm_json`).
- `llm_output.py`: output JSON schema, Groq `response_format`, `parse_plan`, `SAMPLE_PLAN`.
- Plan UI: summary card, safety chips, per-day tabs, "LLM input (JSON)" expander.

## 2026-10-26 — Static UI (272c15e)

### Added
- Streamlit app with the input form, theme and styling; project setup (`pyproject.toml`,
  `uv.lock`, `.env.sample`).

## 2026-10-26 — Initial commit (16af41c)

### Added
- README and `.gitignore`.
