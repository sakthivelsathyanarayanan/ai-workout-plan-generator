"""
Fitness Plan Generator — Streamlit app

Run:
    pip install streamlit
    streamlit run app.py
"""

from html import escape

import streamlit as st

from ai_workout_plan_generator.llm_input import build_llm_input
from ai_workout_plan_generator.llm_output import SAMPLE_PLAN

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
[data-testid="stButton"] button {
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
[data-testid="stButton"] button:hover {
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


# --------------------------------------------------------------------------
# UI pieces
# --------------------------------------------------------------------------
def render_form():
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


def render_plan(inputs):
    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.markdown("### Your weekly plan")
    with top_r:
        if st.button("Start over", use_container_width=True):
            st.session_state.inputs = None
            st.rerun()

    # TODO: replace with the Groq response once the LLM call is wired
    plan = SAMPLE_PLAN
    st.caption("Sample plan, not yet generated by the LLM.")

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

    with st.expander("LLM input (JSON)"):
        st.json(build_llm_input(inputs))

    tabs = st.tabs([f'Day {day["day_number"]}' for day in plan["days"]])
    for tab, day in zip(tabs, plan["days"]):
        with tab:
            render_day(day)


def exercise_detail(ex):
    """e.g. "4 × 8-12 · 90s rest", or just "30 sec" for timed items."""
    detail = f'{ex["sets"]} × {ex["reps"]}' if ex["sets"] else ex["reps"]
    if ex["rest_seconds"]:
        detail += f' · {ex["rest_seconds"]}s rest'
    return detail


def render_day(day):
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


def header():
    st.markdown('<p class="app-title">Fitness Plan Generator</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-sub">Answer a few questions and get a weekly plan that fits your schedule.</p>',
        unsafe_allow_html=True,
    )


def handle_submit():
    st.session_state.inputs = {
        "goal": st.session_state.goal,
        "level": st.session_state.level,
        "days": st.session_state.days,
        "hours": st.session_state.hours,
        "equipment": st.session_state.equipment,
        "injuries": st.session_state.injuries,
    }
    st.rerun()


# --------------------------------------------------------------------------
# Layout: centered form first, then form on the left and plan on the right
# --------------------------------------------------------------------------
if "inputs" not in st.session_state:
    st.session_state.inputs = None

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
    with right:
        render_plan(st.session_state.inputs)
