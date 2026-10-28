"""
Standard JSON input context sent to the LLM, built from the form submission.
"""

import json

SCHEMA_VERSION = "1.0"
NO_EQUIPMENT = "No equipment"


def build_llm_input(inputs):
    """Map the form inputs dict (from app.handle_submit) to the LLM input template.

    Sensitive: this JSON is exactly what the model sees about the user, and the system
    prompt explains these field names one by one. Renaming or removing a field here
    without updating SYSTEM_PROMPTS in llm_client leaves the model guessing.
    """
    # "No equipment" plus real equipment is contradictory (e.g. "No equipment" +
    # "Full gym"), so real equipment wins. bodyweight_only is an explicit flag because the
    # prompt rules key off it ("use bodyweight exercises only").
    equipment = [e for e in inputs.get("equipment") or [] if e != NO_EQUIPMENT]
    bodyweight_only = not equipment
    if bodyweight_only:
        equipment = [NO_EQUIPMENT]

    # Blank or whitespace-only text becomes null, so the model sees "no limitation" rather
    # than an empty string it might try to interpret. This is free user text: the v4
    # prompt treats it as data, never as instructions (prompt-injection guard).
    injuries = (inputs.get("injuries") or "").strip() or None
    days = int(inputs["days"])

    return {
        "schema_version": SCHEMA_VERSION,
        "request_type": "weekly_workout_plan",
        "user_profile": {
            "fitness_goal": inputs["goal"],
            "experience_level": inputs["level"],
            "injuries_or_limitations": injuries,
        },
        "availability": {
            "days_per_week": days,
            "rest_days_per_week": 7 - days,
            "session_duration_minutes": round(float(inputs["hours"]) * 60),
        },
        "equipment": {
            "available": equipment,
            "bodyweight_only": bodyweight_only,
        },
    }


def to_llm_json(inputs):
    """The LLM input as a pretty-printed JSON string, ready for the user message."""
    return json.dumps(build_llm_input(inputs), indent=2)
