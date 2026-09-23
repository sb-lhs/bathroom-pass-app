# School bell-schedule presets

Share your school's bell schedule so other schools can start from it in one tap.
Presets are **times only** — they never contain student names or rosters.

## Easiest path: export from the app

1. Set up your templates + weekday mapping in Admin → Schedules.
2. Admin → Schools → Export my setup. Fill in school, location, contributor.
3. Save the file, then open a pull request adding it to this `schools/` folder.

## File format (`<slug>.json`)

Full example — copy it and replace the times with your school's published bells:

```json
{
  "school": "Example High School",
  "slug": "example-high-school",
  "location": "Anytown, USA",
  "contributor": "Your Name",
  "version": 1,
  "notes": "Optional: what you collapsed or left out and why.",
  "templates": {
    "Regular": [
      {"start": "08:00", "end": "09:20", "name": "Block 1"},
      {"start": "09:25", "end": "09:50", "name": "Advisory"},
      {"start": "09:55", "end": "11:15", "name": "Block 2"},
      {"start": "11:15", "end": "13:05", "name": "Block 3"},
      {"start": "13:10", "end": "14:30", "name": "Block 4"}
    ],
    "Regular Wednesday": [
      {"start": "07:30", "end": "08:30", "name": "Flex Hour"},
      {"start": "09:00", "end": "10:00", "name": "Block 1"},
      {"start": "10:05", "end": "10:50", "name": "Advisory"},
      {"start": "10:55", "end": "11:55", "name": "Block 2"},
      {"start": "11:55", "end": "13:25", "name": "Block 3"},
      {"start": "13:30", "end": "14:30", "name": "Block 4"}
    ],
    "Late Start": [
      {"start": "09:50", "end": "10:50", "name": "Block 1"},
      {"start": "10:55", "end": "11:55", "name": "Block 2"},
      {"start": "11:55", "end": "13:25", "name": "Block 3"},
      {"start": "13:30", "end": "14:30", "name": "Block 4"}
    ],
    "Early Dismissal": [
      {"start": "08:00", "end": "08:55", "name": "Block 1"},
      {"start": "09:00", "end": "09:55", "name": "Block 2"},
      {"start": "10:00", "end": "10:55", "name": "Block 3"},
      {"start": "11:00", "end": "11:55", "name": "Block 4"}
    ]
  },
  "weekday_templates": {
    "Monday": "Regular",
    "Tuesday": "Regular",
    "Wednesday": "Regular Wednesday",
    "Thursday": "Regular",
    "Friday": "Regular",
    "Saturday": "Regular",
    "Sunday": "Regular"
  },
  "weekday_letters": {
    "Monday": "Everyday",
    "Tuesday": "Everyday",
    "Wednesday": "Everyday",
    "Thursday": "Everyday",
    "Friday": "Everyday",
    "Saturday": "Everyday",
    "Sunday": "Everyday"
  }
}
```

Rules:

- `slug`: lowercase letters, numbers, hyphens. File must be named `<slug>.json`.
- Times are 24h `HH:MM`, end after start. `"name": ""` means auto `Block N` by position.
- `weekday_templates` values must name a template in the same file. Letters are `Everyday`, `A`, or `B`.
- Partial weekday maps are fine — missing days keep the user's current setup.
- Copy `example-high-school.json` as your starting point.

## Checklist before opening a PR

- [ ] `python3 scripts/validate_presets.py` passes, including your file.
- [ ] Times match your school's published bell schedule.
- [ ] No student names anywhere (there is nowhere to put them — keep it that way).

Applying a preset **merges**: its templates are added alongside the user's current
setup and never overwrite anything. Name collisions import as `School — Template`.

## Shared index (`index.json`)

The app's Browse GitHub button reads `schools/index.json` from the repo's main
branch. When merging a school PR, maintainers add one entry:

```json
[{"slug": "example-high-school", "school": "Example High School", "location": "Anytown, USA", "version": 1, "path": "schools/example-high-school.json"}]
```

Entries need `slug`, `school`, and `path` (repo-relative, no `..`). Anything else
is ignored. The file starts as `[]` until the first real school lands.
