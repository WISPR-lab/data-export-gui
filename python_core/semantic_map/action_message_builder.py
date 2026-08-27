import os
import sys

sys.path.append(os.path.dirname(__file__))
from semantic_map.views import clean_target


def _fallback_base_action(event_action):
    cleaned_action = clean_target(event_action)
    translations = {
        "auth": "authentication",
        "user": "",
        "init": "initiated",
        "pass": "passed",
        "fail": "failed",
    }
    words = cleaned_action.split("_")
    translated_words = [translations.get(w, w) for w in words]
    base_action = " ".join(w for w in translated_words if w)
    if base_action in ("user login", "login"):
        base_action = "login"
    return base_action.capitalize()


def message(event_action, action_labels=None, **kwargs):
    outcome = kwargs.get("event_outcome") or kwargs.get("outcome")

    base_action = (action_labels or {}).get(event_action) or _fallback_base_action(event_action)

    if outcome == "success":
        return f"{base_action} - Success"
    if outcome in ("failure", "fail"):
        return f"{base_action} - Failure"
    return base_action
