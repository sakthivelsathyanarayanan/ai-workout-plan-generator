"""
Fitness Plan Generator — Streamlit app

Run:
    uv sync
    uv run streamlit run app.py

Needs GROQ_API_KEY in a .env file (copy .env.sample to .env and add your key).
"""

import json
from html import escape
from typing import Any

import streamlit as st

from ai_workout_plan_generator.llm_client import LLMError, generate_workout_plan
from ai_workout_plan_generator.llm_input import build_llm_input
from ai_workout_plan_generator.llm_output import plan_from_response

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Fitness Plan Generator",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
    --ink: #E8EEF4;
    --muted: #9AA8B8;
    --teal: #2DD4BF;
    --teal-dark: #14B8A6;
    --amber: #FFB703;
    --bg: #0B1220;
    --card: #152033;
    --input: #1C2A40;
    --line: #2A3B55;
}

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stToolbar"] {
    font-family: 'Manrope', sans-serif;
    color: var(--ink);
    background: var(--bg) !important;
}
.stApp { background: var(--bg) !important; }
[data-testid="stHeader"] { background: transparent !important; }

.block-container { padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1400px; }

.app-title { font-size: 2.4rem; font-weight: 800; letter-spacing: -0.02em; margin: 0; color: var(--ink); }
.app-sub { color: var(--muted); font-size: 1.05rem; margin: 0.35rem 0 1.6rem 0; }

[data-testid="stForm"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 2rem 2rem 1.5rem 2rem;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
}
[data-testid="stWidgetLabel"] p,
[data-testid="stForm"] label p {
    font-weight: 600;
    font-size: 0.98rem;
    color: var(--ink) !important;
}

[data-baseweb="select"] > div,
.stTextArea textarea,
.stNumberInput input,
[data-testid="stTextArea"] textarea,
[data-baseweb="input"] {
    border-radius: 10px !important;
    background-color: var(--input) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
}
[data-testid="stSelectbox"] div:has(> input) {
    border-radius: 10px !important;
    background-color: var(--input) !important;
    border: 1px solid var(--line) !important;
}
[data-testid="stSelectbox"] div:has(> input)[data-focus-within] {
    border-color: var(--teal) !important;
}
[data-testid="stSelectbox"] input {
    color: var(--ink) !important;
}
[data-baseweb="select"] svg,
[data-baseweb="select"] input {
    fill: var(--ink) !important;
    color: var(--ink) !important;
}
.stTextArea textarea::placeholder {
    color: var(--muted) !important;
}

[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"],
[data-testid="stSliderThumbValue"] {
    color: var(--ink) !important;
}

[data-testid="stFormSubmitButton"] button,
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
    width: 100%;
    background: linear-gradient(135deg, var(--teal), var(--teal-dark)) !important;
    color: #06201C !important;
    border: none !important;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    font-weight: 700;
    font-size: 1.05rem;
    transition: transform .12s ease, box-shadow .12s ease;
}
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(45, 212, 191, 0.35);
    color: #06201C !important;
}

.summary-card {
    background: #101A2C;
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
}
.summary-card h3 { margin: 0 0 .25rem 0; font-size: 1.3rem; font-weight: 800; color: var(--ink); }
.summary-card p { margin: 0; color: var(--muted); font-size: .95rem; }
.chip {
    display: inline-block; background: rgba(45, 212, 191, .16);
    color: var(--teal);
    border-radius: 999px; padding: .2rem .7rem; margin: .6rem .4rem 0 0;
    font-size: .8rem; font-weight: 600;
}
.chip.warn { background: var(--amber); color: #12263A; }

.day-title { font-size: 1.15rem; font-weight: 800; margin: .2rem 0 .1rem 0; color: var(--ink); }
.day-meta { color: var(--muted); font-size: .88rem; margin-bottom: .8rem; }

.ex-row {
    display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: .7rem 1rem; margin-bottom: .5rem;
    color: var(--ink);
}
.ex-name { font-weight: 700; color: var(--ink); }
.ex-detail { color: var(--muted); font-size: .88rem; white-space: nowrap; }
.ex-row.soft { background: #16353A; border-color: #2A6B68; }

.placeholder {
    border: 2px dashed var(--line); border-radius: 18px; padding: 2rem; text-align: center;
    color: var(--muted);
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Option lists
# --------------------------------------------------------------------------
GOALS = ["Build muscle", "Lose fat", "General fitness", "Improve endurance"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
EQUIPMENT = ["No equipment", "Home dumbbells", "Full gym"]

# Shown under the plan (and in the download) when the model reports a real physical
# limitation (plan["has_physical_limitation"]). The app can't judge free text itself, e.g.
# "bad knees" vs "I love samosa", so the model decides and the app shows fixed wording.
# This is the only disclaimer: the prompt tells the model not to repeat one in
# safety_notes, so the user doesn't see it twice.
INJURY_DISCLAIMER = (
    "This plan is general fitness guidance, not medical advice. Because you mentioned an "
    "injury or limitation, check with a doctor or physiotherapist before starting, and stop "
    "any exercise that causes pain."
)

# Type aliases for readability. Inputs is the form dict built in handle_submit;
# Plan, Day and Exercise follow PLAN_SCHEMA / DAY_SCHEMA / EXERCISE_SCHEMA in llm_output.
Inputs = dict[str, Any]
Plan = dict[str, Any]
Day = dict[str, Any]
Exercise = dict[str, Any]


# --------------------------------------------------------------------------
# UI pieces
# --------------------------------------------------------------------------
def render_form() -> bool:
    """The input form. Returns True when the button is pressed."""
    with st.form("plan_form"):
        st.selectbox("Fitness goal", GOALS, key="goal")
        st.selectbox("Experience level", LEVELS, key="level")
        st.slider("Days available per week", 1, 7, 4, key="days")
        st.slider(
            "Time you can spend per day (hours)",
            min_value=0.5, max_value=3.0, value=1.0, step=0.25, key="hours",
        )
        st.multiselect(
            "Equipment access",
            EQUIPMENT,
            default=["Home dumbbells"],
            key="equipment",
            help="Select everything you can use.",
        )
        st.text_area(
            "Injuries or limitations (optional)",
            key="injuries",
            placeholder='e.g. "bad knees", "no overhead pressing"',
            height=90,
        )
        return st.form_submit_button("Generate plan")


def render_plan(inputs: Inputs) -> None:
    top_l, top_mid, top_r = st.columns([3, 1.3, 1.3])
    with top_l:
        st.markdown("### Your weekly plan")
    with top_mid:
        regenerate = st.button("Regenerate", use_container_width=True)
    with top_r:
        if st.button("Start over", use_container_width=True):
            # Clear both together: inputs controls which layout is shown, and a leftover
            # raw_response would be displayed next to the wrong inputs.
            st.session_state.inputs = None
            st.session_state.raw_response = None
            st.rerun()

    # Regenerate asks for a new plan with the inputs of the plan on screen, not the form's
    # current values (the user may have edited the form without submitting it). With
    # TEMPERATURE 0.3 the new plan varies, but stays close to the previous one.
    # Handled outside the columns so an error message uses the full width.
    if regenerate:
        request_plan(inputs)

    # Gate between the LLM and the UI: the cards below index keys like plan["days"]
    # directly, so only a reply that passes the schema check is rendered as cards.
    # Anything else is shown as plain text instead of crashing the page.
    raw_response = st.session_state.raw_response
    plan = plan_from_response(raw_response)
    if plan is None:
        st.info("Response didn't match the plan schema. Showing raw LLM output.")
        # Safe: st.markdown without unsafe_allow_html does not render raw HTML.
        st.markdown(raw_response)
        return

    # Security: the HTML below is rendered with unsafe_allow_html=True, so every value that
    # comes from the LLM (title, summary, safety notes, exercise names, notes) must go
    # through escape(). Without it, a reply containing <script> or <img onerror=...> would
    # run in the user's browser. goal/level/days/hours come from fixed form options, so
    # they are safe unescaped.
    chips = (
        f'<span class="chip">{inputs["goal"]}</span>'
        f'<span class="chip">{inputs["level"]}</span>'
        f'<span class="chip">{inputs["days"]} days / week</span>'
        f'<span class="chip">{inputs["hours"]:g} h / day</span>'
    )
    chips += "".join(
        f'<span class="chip warn">{escape(note)}</span>' for note in plan["safety_notes"]
    )
    st.markdown(
        f"""
        <div class="summary-card">
            <h3>{escape(plan["plan_title"])}</h3>
            <p>{escape(plan["summary"])}</p>
            {chips}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if plan["has_physical_limitation"]:
        st.warning(INJURY_DISCLAIMER, icon="⚠️")

    # One file with the whole week (all days), placed above the day tabs so it reads as
    # belonging to the plan, not to the day that is open. It is built from the plan
    # already in session state, so it never calls the API. Only offered for a valid plan,
    # because plan_to_markdown reads the schema keys directly.
    st.download_button(
        f'Download full plan ({len(plan["days"])} days, .md)',
        data=plan_to_markdown(plan, inputs),
        file_name="workout-plan.md",
        mime="text/markdown",
        use_container_width=True,
    )

    tabs = st.tabs([f'Day {day["day_number"]}' for day in plan["days"]])
    for tab, day in zip(tabs, plan["days"]):
        with tab:
            render_day(day)


def plan_to_markdown(plan: Plan, inputs: Inputs) -> str:
    """The plan as a Markdown document: summary, safety notes and one table per day."""

    def cell(text: object) -> str:
        # "|" would split a Markdown table cell and newlines would break the row.
        return str(text or "").replace("|", "/").replace("\n", " ")

    lines = [
        f'# {plan["plan_title"]}',
        "",
        plan["summary"],
        "",
        f'**Goal:** {inputs["goal"]} · **Level:** {inputs["level"]} · '
        f'**Days:** {inputs["days"]} / week · **Time:** {inputs["hours"]:g} h / day',
    ]
    if plan["safety_notes"]:
        lines += ["", "## Safety notes", ""]
        lines += [f"- {note}" for note in plan["safety_notes"]]
    if plan["has_physical_limitation"]:
        lines += ["", f"> **Disclaimer:** {INJURY_DISCLAIMER}"]

    for day in plan["days"]:
        meta = day["focus"]
        if day["duration_minutes"]:
            meta += f' · {day["duration_minutes"]} min'
        lines += ["", f'## Day {day["day_number"]} · {day["title"]}', "", f"_{meta}_", ""]
        if not day["exercises"]:
            lines.append("Rest day.")
            continue
        lines += ["| Phase | Exercise | Sets × reps · rest | Notes |", "|---|---|---|---|"]
        lines += [
            f'| {ex["phase"]} | {cell(ex["name"])} | {cell(exercise_detail(ex))} | {cell(ex["notes"])} |'
            for ex in day["exercises"]
        ]
    return "\n".join(lines) + "\n"


def render_llm_io(inputs: Inputs, raw_response: str | None) -> None:
    """The JSON sent to the LLM and the raw reply, for inspecting prompt changes.

    A debugging aid: it shows exactly what the model received and returned, including
    the user's injuries text. Remove or hide it before sharing the app with real users.
    """
    with st.expander("LLM input (JSON)"):
        st.json(build_llm_input(inputs))
    with st.expander("LLM output (JSON)"):
        # Valid JSON is shown as a tree; anything else (e.g. free text from the v1/v2
        # prompts) as plain text, so the raw reply is always visible.
        try:
            st.json(json.loads(raw_response))
        # TypeError covers a None reply, so this expander can never crash the page.
        except (json.JSONDecodeError, TypeError):
            st.code(raw_response, language=None)


def exercise_detail(ex: Exercise) -> str:
    """e.g. "4 × 8-12 · 90s rest", or just "30 sec" for timed items."""
    detail = f'{ex["sets"]} × {ex["reps"]}' if ex["sets"] else ex["reps"]
    if ex["rest_seconds"]:
        detail += f' · {ex["rest_seconds"]}s rest'
    return detail


def render_day(day: Day) -> None:
    # Every LLM-provided string is passed through escape() before it goes into the HTML
    # (rendered with unsafe_allow_html=True). Keep it that way when adding fields.
    meta = escape(day["focus"])
    if day["duration_minutes"]:
        meta += f' · {day["duration_minutes"]} min'
    rows = [
        f'<p class="day-title">Day {day["day_number"]} · {escape(day["title"])}</p>',
        f'<p class="day-meta">{meta}</p>',
    ]
    if not day["exercises"]:
        rows.append('<div class="ex-row soft"><span class="ex-name">Rest day</span></div>')
    for ex in day["exercises"]:
        soft = " soft" if ex["phase"] != "main" else ""
        title = f' title="{escape(ex["notes"])}"' if ex["notes"] else ""
        rows.append(
            f'<div class="ex-row{soft}"{title}>'
            f'<span class="ex-name">{escape(ex["name"])}</span>'
            f'<span class="ex-detail">{escape(exercise_detail(ex))}</span>'
            "</div>"
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def header() -> None:
    st.markdown('<p class="app-title">Fitness Plan Generator</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-sub">Answer a few questions and get a weekly plan that fits your schedule.</p>',
        unsafe_allow_html=True,
    )


def handle_submit() -> None:
    """Validate the form, call the LLM once and store the result in session state.

    Order matters:
    1. Validate first, so an incomplete form never costs an API call.
    2. Call the LLM here, on submit only. Streamlit reruns the whole script on every
       click (tabs, expanders, Start over); calling it during rendering would make a new
       paid, slow request on each of those reruns.
    3. Save inputs and reply only after success. On failure the old state is kept, so
       the user stays on the form with an error instead of an empty plan screen.
    """
    if not st.session_state.equipment:
        st.error("Please select at least one option under Equipment access.")
        return

    inputs = {
        "goal": st.session_state.goal,
        "level": st.session_state.level,
        "days": st.session_state.days,
        "hours": st.session_state.hours,
        "equipment": st.session_state.equipment,
        "injuries": st.session_state.injuries,
    }
    request_plan(inputs)


def request_plan(inputs: Inputs) -> None:
    """Call the LLM for these inputs; on success store the plan and rerun, else show an error.

    Shared by "Generate plan" and "Regenerate", so both get the same spinner, error
    handling and session-state update.
    """
    try:
        with st.spinner("Generating plan..."):
            raw_response = generate_workout_plan(**inputs)
    except LLMError as e:
        # generate_workout_plan only ever raises LLMError, whose messages are written to
        # be shown to users (no API key, no raw Groq bodies). The previous plan, if any,
        # stays on screen.
        st.error(str(e))
        return
    st.session_state.inputs = inputs
    st.session_state.raw_response = raw_response
    st.rerun()


# --------------------------------------------------------------------------
# Layout: centered form first, then form on the left and plan on the right
# --------------------------------------------------------------------------
# Session state survives Streamlit's reruns for this browser tab. inputs decides the
# layout (None = centred form, set = form + plan); raw_response caches the LLM reply so
# reruns never call the API again.
if "inputs" not in st.session_state:
    st.session_state.inputs = None
    st.session_state.raw_response = None

if st.session_state.inputs is None:
    _, center, _ = st.columns([0.4, 2.4, 0.4])
    with center:
        header()
        if render_form():
            handle_submit()
else:
    left, right = st.columns([1.15, 1.2], gap="large")
    with left:
        header()
        if render_form():
            handle_submit()
        render_llm_io(st.session_state.inputs, st.session_state.raw_response)
    with right:
        render_plan(st.session_state.inputs)
