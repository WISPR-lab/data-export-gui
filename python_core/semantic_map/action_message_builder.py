
import sys
import os
sys.path.append(os.path.dirname(__file__))
from utils.misc import clean_target




def message(event_action, **kwargs):  # TODO add kwargs for better messages

    event_action = clean_target(event_action)
    # translate ecs field with dot notation to underscore notation for mapping (dots annoying in sql)
    # also get rid of @ in timeline

    match event_action:

        case "auth_checkpoint_init":
            return "Account verification request"

        case "auth_checkpoint_pass":
            return "Account verification passed"

        case "data_export_request":
            return "Data export requested by user"
        
        case "email_addition":
            return "Email added"

        case "password_reset_request":
            return "Password reset requested by user"

        case "recovery_contact_addition" | "legacy_contact_addition":
            return "Recovery/legacy contact added"

        case "user_login_success":
            return "Successful login"

        case "user_logout":
            return "Logout"

        case "user_password_change":
            return "Password changed"

        case _:
            return event_action

    



