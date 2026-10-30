# Architecture

AI Workout Plan Generator is a Streamlit app. The user fills in a form, and the app sends
the answers as structured JSON to an LLM on Groq. The reply must match a JSON schema, and
the app renders it as a weekly plan.

## 1. Components

```mermaid
flowchart LR
    user(["User (browser)"])

    subgraph app["Streamlit app (app.py)"]
        form["Input form<br/>goal, level, days, hours,<br/>equipment, injuries"]
        validate["handle_submit()<br/>validation + one LLM call per submit"]
        state[("st.session_state<br/>inputs, raw_response")]
        gate{"plan_from_response()<br/>matches schema?"}
        cards["Plan UI<br/>summary card, safety chips,<br/>7 day tabs"]
        raw["Raw text fallback"]
        io["Debug expanders<br/>LLM input / output JSON"]
    end

    subgraph pkg["Package: src/ai_workout_plan_generator"]
        input["llm_input.py<br/>build_llm_input()<br/>to_llm_json()"]
        client["llm_client.py<br/>generate_workout_plan()<br/>SYSTEM_PROMPTS v1-v4<br/>retry + error handling"]
        output["llm_output.py<br/>PLAN_SCHEMA<br/>response_format()<br/>plan_from_response()"]
    end

    env[(".env<br/>GROQ_API_KEY<br/>GROQ_MODEL")]
    groq["Groq API<br/>openai/gpt-oss-20b<br/>strict JSON schema"]

    user --> form --> validate
    validate --> client
    client --> input
    client --> output
    env -. load_dotenv .-> client
    client <-->|"chat.completions.create"| groq
    client -->|"JSON text or LLMError"| validate
    validate --> state
    state --> gate
    output -.-> gate
    gate -->|yes| cards
    gate -->|no| raw
    state --> io
    cards --> user
    raw --> user
```

| Module | Responsibility |
|---|---|
| [app.py](app.py) | Page layout, form, validation, session state, rendering the plan (with HTML escaping), debug expanders |
| [llm_input.py](src/ai_workout_plan_generator/llm_input.py) | Turns form answers into the input JSON the model receives (normalises equipment, empty injuries → `null`) |
| [llm_client.py](src/ai_workout_plan_generator/llm_client.py) | System prompts, Groq call, settings (tokens, temperature, retries), turning every failure into `LLMError` |
| [llm_output.py](src/ai_workout_plan_generator/llm_output.py) | Output schema shared by Groq, the prompt and the UI; schema check before rendering; sample plan |

## 2. Request flow (successful submit)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as app.py
    participant I as llm_input.py
    participant C as llm_client.py
    participant O as llm_output.py
    participant G as Groq API

    U->>A: Click "Generate plan"
    A->>A: Validate form (equipment selected?)
    A->>C: generate_workout_plan(goal, level, days, hours, equipment, injuries)
    C->>I: to_llm_json(inputs)
    I-->>C: Input JSON (user message)
    C->>C: Check GROQ_API_KEY
    loop Up to MAX_ATTEMPTS = 3 (only on json_validate_failed)
        C->>G: system prompt (v4) + user JSON<br/>response_format = PLAN_SCHEMA (strict)<br/>temperature 0.3, max 8192 tokens
        G-->>C: JSON reply (checked against schema)
    end
    C->>C: finish_reason == "length"? then error
    C-->>A: JSON text
    A->>A: Save inputs + raw_response in session_state, rerun
    A->>O: plan_from_response(raw_response)
    O-->>A: plan dict
    A-->>U: Summary card, safety chips, 7 day tabs, debug expanders
```

Streamlit reruns the whole script on every click (tabs, expanders). The LLM is called only
in `handle_submit`, and the reply is cached in `st.session_state`, so reruns never call the API
again.

## 3. Error handling

Every failure inside `generate_workout_plan` becomes an `LLMError` with a message safe to show
users. `app.py` shows it under the form and keeps the user on the form.

```mermaid
flowchart TD
    start(["generate_workout_plan()"]) --> key{"GROQ_API_KEY set?"}
    key -->|no| e0["LLMError: key not set"]
    key -->|yes| groqCall["Groq chat.completions.create"]

    groqCall -->|success| fin{"finish_reason == length?"}
    fin -->|yes| e1["LLMError: cut off,<br/>tokens used / limit / reasoning"]
    fin -->|no| ok(["Return JSON text"])

    groqCall -->|"400 json_validate_failed"| retry{"attempt < 3?"}
    retry -->|yes| groqCall
    retry -->|no| e2["LLMError: no valid plan after 3 tries"]

    groqCall -->|"other error"| map["Map to a friendly message<br/>401 key · 403 access · 404 model<br/>429 rate limit · 400/409/422 request<br/>413 token limit · 5xx server<br/>timeout · connection · invalid response<br/>other status · unexpected exception"]
    map --> e3["LLMError"]

    e0 & e1 & e2 & e3 --> ui["app.py: st.error(message)<br/>user stays on the form"]
```

## 4. Data contract

The same field names are used in four places, so they must change together:

```mermaid
flowchart LR
    form["Form fields<br/>(app.py)"] --> inJSON["Input JSON<br/>user_profile, availability,<br/>equipment (llm_input.py)"]
    inJSON --> prompt["System prompt v4<br/>explains each input field,<br/>rules use day_type / phase<br/>(llm_client.py)"]
    schema["PLAN_SCHEMA<br/>days, exercises, enums<br/>(llm_output.py)"] --> prompt
    schema --> groq["Groq strict<br/>response_format"]
    schema --> check["plan_from_response()"]
    check --> ui["UI rendering<br/>plan_title, safety_notes,<br/>days, exercises"]
```

**Input (sent to the model):** `schema_version`, `request_type`, `user_profile` (goal, level,
injuries or `null`), `availability` (days per week, rest days, session minutes), `equipment`
(available list, `bodyweight_only`).

**Output (returned by the model):** `schema_version`, `plan_title`, `summary`, `safety_notes[]`,
`has_physical_limitation` (the model's judgement of the injuries text; the app shows its fixed
disclaimer only when true), and `days[]` (7 items: `day_number`, `day_type` = workout / rest / active_recovery, `title`, `focus`,
`duration_minutes`, `exercises[]` with `name`, `phase` = warmup / main / cooldown, `sets`, `reps`,
`rest_seconds`, `notes`).

## 5. System prompt versions

Kept side by side in `SYSTEM_PROMPTS`; `ACTIVE_PROMPT` picks the one in use.

```mermaid
flowchart LR
    v1["v1<br/>one-line baseline"] --> v2["v2<br/>+ trainer role<br/>+ meaning of input fields"]
    v2 --> v3["v3<br/>+ plan rules<br/>+ experience level<br/>+ JSON output + schema"]
    v3 --> v4["v4 (active)<br/>+ equipment definitions<br/>+ injury safety + disclaimer flag<br/>+ treat user text as data"]
```

## 6. Key settings

| Setting | Where | Value | Why |
|---|---|---|---|
| Model | `.env` `GROQ_MODEL` / `DEFAULT_MODEL` | `openai/gpt-oss-20b` | Supports strict structured output on Groq |
| `MAX_COMPLETION_TOKENS` | llm_client.py | 8192 | Groq's 2048 default cut off replies; reasoning uses part of the budget |
| `TEMPERATURE` | llm_client.py | 0.3 | Fewer random JSON slips, some variety between plans |
| `MAX_ATTEMPTS` | llm_client.py | 3 | Retries only `json_validate_failed` |
| `response_format` | llm_output.py | strict JSON schema | Groq rejects replies that don't match `PLAN_SCHEMA` |

## 7. Safety and security

- **Prompt injection:** the injuries text is user-typed and goes to the model. v4 tells the model
  to treat it as data, and strict output means the reply must still be a plan.
- **HTML injection:** the plan is rendered with `unsafe_allow_html=True`, so every value from the
  LLM goes through `escape()`.
- **Secrets:** the API key lives only in `.env` (gitignored) and is never shown in error messages.
- **Medical safety:** v4 swaps risky exercises, records each adaptation in `safety_notes`, and
  advises seeing a doctor or physiotherapist for serious limitations.
- **Debug expanders** show the user's input and the raw reply. Hide them before sharing the app
  with real users.
