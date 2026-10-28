"""
Structured JSON output the LLM must return, and the schema used to enforce it.
"""

import json

SCHEMA_VERSION = "1.0"
# Allowed values for day_type and phase. Sensitive: they are used in three places at
# once: the schema Groq enforces, the v3/v4 prompt text, and app.py (phase != "main" is
# drawn as a soft row). Renaming one here without updating the others makes Groq reject
# replies or the UI style them wrongly.
DAY_TYPES = ["workout", "rest", "active_recovery"]
PHASES = ["warmup", "main", "cooldown"]

# Schema notes (apply to all three schemas below):
# - Groq strict mode requires every property to be listed in "required" and
#   "additionalProperties": False. Optional values are expressed as ["type", "null"]
#   instead of leaving a field out. Breaking this makes every request fail with a 400.
# - The UI reads these exact keys (app.render_plan / render_day / exercise_detail), and
#   plan_from_response checks the "required" lists. Adding, removing or renaming a field
#   changes what the model must produce, what the prompt shows it, and what the UI reads.

EXERCISE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "phase": {"type": "string", "enum": PHASES},
        "sets": {"type": ["integer", "null"]},
        "reps": {"type": "string", "description": 'e.g. "8-12", "AMRAP", "30 sec"'},
        "rest_seconds": {"type": ["integer", "null"]},
        "notes": {"type": ["string", "null"], "description": "Form cue or substitution."},
    },
    "required": ["name", "phase", "sets", "reps", "rest_seconds", "notes"],
    "additionalProperties": False,
}

DAY_SCHEMA = {
    "type": "object",
    "properties": {
        "day_number": {"type": "integer"},
        "day_type": {"type": "string", "enum": DAY_TYPES},
        "title": {"type": "string"},
        "focus": {"type": "string"},
        "duration_minutes": {"type": "integer"},
        "exercises": {"type": "array", "items": EXERCISE_SCHEMA},
    },
    "required": ["day_number", "day_type", "title", "focus", "duration_minutes", "exercises"],
    "additionalProperties": False,
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "plan_title": {"type": "string"},
        "summary": {"type": "string"},
        "safety_notes": {"type": "array", "items": {"type": "string"}},
        "days": {
            "type": "array",
            "items": DAY_SCHEMA,
            "description": "Exactly 7 days, Day 1 to Day 7, including rest days.",
        },
    },
    "required": ["schema_version", "plan_title", "summary", "safety_notes", "days"],
    "additionalProperties": False,
}


def response_format():
    """The `response_format` argument for a Groq chat completion with strict structured output.

    Effect: Groq checks every reply against PLAN_SCHEMA. Matching replies reach us
    unchanged; non-matching ones are rejected with a 400 "json_validate_failed" error
    (retried in llm_client). With "strict": False, Groq would pass on replies that don't
    match and the UI would fall back to raw text more often.
    """
    return {
        "type": "json_schema",
        "json_schema": {"name": "weekly_workout_plan", "strict": True, "schema": PLAN_SCHEMA},
    }


def parse_plan(text):
    """Parse the LLM response text into a plan dict. Raises ValueError if it is malformed."""
    try:
        plan = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response is not valid JSON: {e}") from e

    if not isinstance(plan, dict) or not isinstance(plan.get("days"), list) or not plan["days"]:
        raise ValueError("LLM response has no 'days' list.")
    for day in plan["days"]:
        if not isinstance(day, dict) or not isinstance(day.get("exercises"), list):
            raise ValueError("Each day in the LLM response needs an 'exercises' list.")
    return plan


def _has_keys(obj, schema):
    return isinstance(obj, dict) and all(key in obj for key in schema["required"])


def plan_from_response(text: str) -> dict | None:
    """The plan dict if the LLM text is JSON matching the plan schema the UI reads, else None.

    Purpose: the gate between the LLM and the UI. The plan cards index keys directly
    (plan["days"], ex["phase"], ...), so rendering a reply with a missing key would crash
    the page. When this returns None, app.py shows the raw text instead.
    Checks only that required keys exist, not their types or values; Groq's strict
    response_format covers those. Kept as a second line of defence, e.g. when
    response_format is turned off to experiment with prompts.
    """
    try:
        plan = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if not _has_keys(plan, PLAN_SCHEMA) or not isinstance(plan["days"], list) or not plan["days"]:
        return None
    for day in plan["days"]:
        if not _has_keys(day, DAY_SCHEMA) or not isinstance(day["exercises"], list):
            return None
        if not all(_has_keys(ex, EXERCISE_SCHEMA) for ex in day["exercises"]):
            return None
    return plan


# --------------------------------------------------------------------------
# Sample output, used to build the UI before the LLM call is wired
# --------------------------------------------------------------------------
def _ex(name, phase, sets, reps, rest_seconds=None, notes=None):
    return {
        "name": name, "phase": phase, "sets": sets, "reps": reps,
        "rest_seconds": rest_seconds, "notes": notes,
    }


def _rest_day(day_number):
    return {
        "day_number": day_number, "day_type": "rest", "title": "Rest",
        "focus": "Recovery", "duration_minutes": 0, "exercises": [],
    }


SAMPLE_PLAN = {
    "schema_version": SCHEMA_VERSION,
    "plan_title": "4-Day Upper/Lower Muscle Builder",
    "summary": "Two upper and two lower sessions with dumbbells. Add a rep each week, then add weight once you hit the top of the range.",
    "safety_notes": ["Knee-friendly: box squats and short-range lunges instead of deep squats."],
    "days": [
        {
            "day_number": 1, "day_type": "workout", "title": "Upper Body Push",
            "focus": "Chest, shoulders, triceps", "duration_minutes": 60,
            "exercises": [
                _ex("Arm circles", "warmup", None, "30 sec"),
                _ex("Dumbbell floor press", "main", 4, "8-12", 90),
                _ex("Seated dumbbell shoulder press", "main", 3, "8-10", 90),
                _ex("Push-ups", "main", 3, "AMRAP", 60, "Elevate hands if needed."),
                _ex("Overhead triceps extension", "main", 3, "10-12", 60),
                _ex("Chest stretch", "cooldown", None, "45 sec"),
            ],
        },
        {
            "day_number": 2, "day_type": "workout", "title": "Lower Body",
            "focus": "Glutes, hamstrings, quads", "duration_minutes": 60,
            "exercises": [
                _ex("Glute bridges", "warmup", 2, "15"),
                _ex("Dumbbell box squat", "main", 4, "8-12", 90, "Sit back to a box at knee height."),
                _ex("Romanian deadlift", "main", 4, "8-10", 90),
                _ex("Short-range reverse lunge", "main", 3, "10 / leg", 60),
                _ex("Hamstring stretch", "cooldown", None, "45 sec"),
            ],
        },
        _rest_day(3),
        {
            "day_number": 4, "day_type": "workout", "title": "Upper Body Pull",
            "focus": "Back, biceps", "duration_minutes": 60,
            "exercises": [
                _ex("Band pull-aparts", "warmup", 2, "15"),
                _ex("One-arm dumbbell row", "main", 4, "8-12", 90),
                _ex("Dumbbell pullover", "main", 3, "10-12", 60),
                _ex("Hammer curls", "main", 3, "10-12", 60),
                _ex("Lat stretch", "cooldown", None, "45 sec"),
            ],
        },
        {
            "day_number": 5, "day_type": "workout", "title": "Lower Body + Core",
            "focus": "Posterior chain, core", "duration_minutes": 60,
            "exercises": [
                _ex("Hip circles", "warmup", None, "30 sec"),
                _ex("Single-leg Romanian deadlift", "main", 3, "10 / leg", 60),
                _ex("Dumbbell hip thrust", "main", 4, "10-12", 90),
                _ex("Dead bug", "main", 3, "12", 45),
                _ex("Plank", "main", 3, "40 sec", 45),
                _ex("Child's pose", "cooldown", None, "60 sec"),
            ],
        },
        {
            "day_number": 6, "day_type": "active_recovery", "title": "Active Recovery",
            "focus": "Mobility, light cardio", "duration_minutes": 30,
            "exercises": [
                _ex("Brisk walk", "main", None, "20 min"),
                _ex("Full-body stretch", "cooldown", None, "10 min"),
            ],
        },
        _rest_day(7),
    ],
}
