# Understanding and writing new manifests

The platform YAML files in `manifests/` (i.e., `apple.yaml`) provide instructions for the Python engine to map data exports into (a slightly modified version of) the Elastic Common Schema (ECS). The goal of this is to minimize how much of the Python engine in `python_core` we have to rewrite if we want to add support for a new platform or if the platforms change file formats. 

A manifest has two main sections:

1. `files`: physical files to parse (inputs)
2. `views`: specs for the logical events/states extracted from those files (outputs).

---

### (1) File Sources

Define the physical file once, even if it contains multiple types of events.

```yaml
files:
  - id: "insta_devices"                 # Unique reference ID        
    path: "path/to/devices.json"        # Relative path in the ZIP
    parser:
      format: "json"
      json_root: "devices_devices[]"
      drop_duplicates:                  # optional deduplication, follows pandas conventions
        subset: ["Device ID"]
        keep: "last"
  - id: ....
```

The attributes under `parser:` describe the shape of the file and how the engine should parse it.

- `format`:
    - `json`: standard JSON, ok for nested dictionaries within dictionaries, but not nested lists.
    - `json_label_values`: Special Meta format where data is stored in lists of `{label: "Key", value: "Val"}`.
    - `jsonl`: newline delimited JSON format, common in Discord
    - `csv`
    - `csv_multi`: a very odd file that contains multiple CSV sections separated by titles and newlines, common in Apple

- `json_root`: (json/json_label_values/jsonl only; optional): The path to the list of objects you want to parse. Use [] to denote a list (e.g., `account_activity_v2[]`).
- `drop_duplicates`: (optional) logic to clean data at the source level. Follows pandas conventions. Requires:
    - `subset`: list of columns to check
    - `keep`: `first`, `last`, or `row_completeness` (keep the row with the most non-null row entries)

---

### (2) Views

A `view` defines how to transform a source into a stream of events/states (vaguely using ECS conventions). You can have multiple views for a single source (e.g., one for "Logins" and one for "Logouts").

```yaml
views:
  - file: 
      id: "insta_devices"           # Must match a file ID
      where: {source: "status", op: "==", value: "active"}  # Filtering (optional) only rows that match this condition

    # hardcoded ECS values for every event in this view.
    static:
      event.kind: "state"                              # 'event' (action) or 'state' (snapshot)
      event.category: ["authentication", "session"]    # follow ECS conventions
      entity.type: "application"
      entity.sub_type: "app_registration"
    
    # dynamic mappings
    fields:
      - {target: "entity.last_seen_timestamp", source: "'Last Login'.timestamp", type: "datetime"}
      - {target: "user_agent.original", source: "'User Agent'.value", type: "string"}
```

#### file attributes:
- `where` selects only rows that match this condition
    - Simple: i.e., `{source: "event_type", op: "==", value: "login"}`
    - Complex: Uses logic: any or all with a conditions list. 
        - Supports operators: `==`, `startswith`, `contains`, `endswith`, `!=`. 
        - Add more supported operators in `python_core/utils/filter_builder.py` (`OP_MAPPING`), and mirror them into `KNOWN_WHERE_OPS` in `scripts/validate_manifests.py`.

#### path traversal for source keys:
JSON (and jsonl) source fields support path traversal for nested dictionaries via dot notation and bracket notation. Use single quotes for keys containing spaces, e.g.:
- `session.ip_address`
- `'Device ID details'.first_seen_time`
- `push_tokens[0].id`: Gets the id of the first item in the list.

#### Static attributes:
hardcoded ECS (Elastic Common Schema) values for every event in this view.

- `event.kind` decides which table the row lands in. Anything else is logged as `Unhandled event_kind` and dropped.
    - `event`: points in time (Logins, Messages, Clicks). Goes to the `events` table, keyed on `@timestamp`.
    - `state`: inventory snapshots (Devices, Sessions, Contacts). Goes to the `devices_raw` table, keyed on `entity.[first/last]_seen_timestamp`.
- `entity.type` is **required for `state` rows.** Only these three are kept; a `state` row with any other `entity.type` is silently discarded by `python_core/semantic_map/worker.py`.
    - `host`: physical hardware (an iPhone, a laptop).
    - `application`: an app or client install registered to the account.
    - `session`: a logged-in session or cookie.
- `entity.sub_type` is an optional refinement used by the Devices view for grouping:
  `app_registration`, `hardware_registration`, `platform_inferred_device`, `trusted_cookie`, `passkey_registration`.
- `event.category` / `event.type` / `event.outcome` follow ECS conventions. The combination that each
  `event.action`, `entity.type`, and `entity.sub_type` requires is declared in `__taxonomy.yaml` under
  `relationships:` and enforced by the validator (see below).

The full accepted vocabulary for every field lives in `manifests/__taxonomy.yaml`, which is the source of
truth. This README summarizes it, but the taxonomy and the validator are what actually gate a manifest.

#### Dynamic field mappings:
Every item must have `target` (the standardized ECS field name) and a `source` (the raw data key in the file), and optionally a `type` and `transform`. Path traversal for `source` fields follows conventions above. 

If transform is set to "coalesce" (or if source is a list), the engine will pick the first non-null value.
- e.g., `{ ... source: ["push_tokens[0].id", "family_id"], transform: "coalesce"}`

#### Custom ECS Fields currently used:
ECS isn't really built for this use case, so we have a couple of custom fields that we're consistently using at the moment:

- `device.id.[platform]`: internal device fingerprint (not user ID) for a specific platform --> also + .ad
- `device.given_name`: user-defined nickname for device (e.g., "Bob's iPhone"), common in Apple
- `device.imei`: International Mobile Equipment Identity
- `device.meid`: Mobile Equipment Identifier
- `entity.type` / `entity.sub_type`: for `state` rows. See the vocabulary under *Static attributes* above
- `entity.[first/last]_seen_timestamp`: for `state` rows, instead of `@timestamp`
- `url.title`: for title of web page associated with a search/website (declared in the taxonomy, not currently mapped by any manifest)
- `client.session.id` and `client.session.type`
- `user.email.new` and `user.email.old`
- `device.screen_resolution`, `device.locale`, `device.timezone`

---

## (3) Validating a manifest

`scripts/validate_manifests.py` checks every `manifests/*.yaml` against `manifests/__taxonomy.yaml`. It is
read-only and never edits either file. Run it after any manifest change:

```bash
uv run python scripts/validate_manifests.py

# or against a single directory / alternate taxonomy
uv run python scripts/validate_manifests.py --manifests-dir manifests --taxonomy manifests/__taxonomy.yaml
```

It exits non-zero if there are any **errors**, and catches the failure modes that are otherwise silent at
runtime: a view whose `file.id` matches no `files[].id`, an unknown `parser.format` or `where` operator, a
`transform` that isn't implemented, a `target` that isn't in the taxonomy, and `static` values that violate
the `relationships:` shape (e.g. `event.action: user_login` without `event.type: [start]`).

**Warnings** don't fail the run: an unrecognized field `type`, a `drop_duplicates.keep` that will fall back
to `first`, or a taxonomy field with no `description` yet.

It also reports taxonomy entries that no manifest references anymore. That's informational, and usually
means a field was renamed and the old entry can be deleted.

### Adding a new field

The validator rejects any `target` not present in the taxonomy, so new fields need an entry in
`manifests/__taxonomy.yaml` first:

```yaml
fields:
  device.locale:
    description: not ECS, language/region the device is configured for (e.g. en_US)
    url: https://www.elastic.co/guide/en/ecs/current/ecs-device.html   # optional, if it is a real ECS field
```

Two flags matter:
- `allowed_values`: if present, any `static:` value for this field outside the list is an error.
- `parsed_field_only: true`: the field is computed in Python (during normalization) and can never be set
  from a manifest. Setting it in a manifest is an error.
