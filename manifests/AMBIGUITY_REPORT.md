# ⚠️ Ambiguity Followup

I have refactored `discord.yaml`, `facebook.yaml`, and `instagram.yaml` to strictly adhere to the `manifest_version: 2` format and the fields defined in `apple.yaml`.

## Data Loss Report
The following "high value" data columns were **dropped** because they do not have a corresponding mapping target in `apple.yaml`:

### Facebook
- **User Cookies**: `datr_cookie` was dropped from all Login/Logout/Access events.
- **Device IDs**: `push_tokens[0].device_id`, `family_device_id`, `android_id`, `advertiser_id` were dropped from Device/Session events.
- **Operating System**: `os` and `os_ver` were dropped from `mobile_devices`.
- **Email Change Details**: In account updates, we capture the timestamp but drop the actual data because there is no `user.email` or `user.target_email` field in the target schema.

### Instagram
- **Email Change Details**: Dropped `Previous Value` (old email) and `New Value` (new email) from Profile Changes.
- **Cookies**: Dropped `Cookie Name`.

### Discord
- **OS Details**: Dropped `os` ("Android") and `os_version` ("10"). Mapped `device` to `device.model.name` (e.g., "Pixel 3") which seemed closest.

## Uncertain Mappings
- **Application Names**: Mapped Facebook's `app_info` / `name` to `service.name`.
- **Model vs Device**: Mapped generic "Device Type" fields (like Facebook `type`) to `device.model.identifier`.
- **User Agent**: Mapped Discord's `browser` field to `user_agent.original`, assuming it contains the UA string.

## Logic / Intent Notes
- **Filters**: In `apple.yaml`, filtering logic (like `drop_duplicates`) is inside `files`. Since Facebook files often contain multiple event types mixed together (Login, Logout, etc.), I created **multiple file entries** for the same physical file (e.g., `fb_account_activity_login`, `fb_account_activity_logout`), each with a specific `filter` in the parser config. This ensures strict 1:1 mapping between a file source and a view.
