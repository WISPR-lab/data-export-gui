
import sys
import os
sys.path.append(os.path.dirname(__file__))
from utils.misc import clean_target




def message(event_action, **kwargs):
    cleaned_action = clean_target(event_action)
    outcome = kwargs.get("event_outcome") or kwargs.get("outcome")
    # translate ecs field with dot notation to underscore notation for mapping (dots annoying in sql)
    # also get rid of @ in timeline

    translations = {
        "auth": "authentication",
        "user": "",
        "init": "initiated",
        "pass": "passed",
        "fail": "failed",
    }

    words = cleaned_action.split('_')
    translated_words = [translations.get(w, w) for w in words]
    base_action = " ".join([w for w in translated_words if w])

    if base_action == "user login" or base_action == "login":
        base_action = "login"

    if outcome == "success":
        result_message = f"successful {base_action}"
    elif outcome in ("failure", "fail"):
        result_message = f"failed {base_action}"
    else:
        result_message = base_action

    return result_message.capitalize()

    



