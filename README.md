# hallpass-qt — Native Touchscreen Bathroom & Water Pass System

100% offline PySide6 (Qt Quick/QML) kiosk for Surface Pro 1.

## Features
- Dual pass types: **Bathroom** (default 420s) / **Water** (default 180s) with independent timers
- Dynamic daily block schedule matching + queue with offline TTS (`QTextToSpeech` + `speech-dispatcher/espeak-ng`)
- Silent webcam photo audit (QCamera/OpenCV, no flash)
- SQLite + CSV dual logging with `OVERTIME` / `NOT OVER` evaluation
- Non-destructive roster CSV merge, audio picker + mute, USB/local export
- Kiosk windowing: fullscreen default, Esc/F11 toggle, Ctrl+Q/Alt+F4 quit (admin-gated)

## Run (dev)
```bash
pip install -r requirements.txt
python src/main.py
# or
python -m hallpass
```

## Paths
- Config: `/etc/hallpass/config.json` (fallback: `~/.config/hallpass/config.json` for dev)
- Schedules: `/etc/hallpass/schedules.json`
- Rosters: `/etc/hallpass/rosters.json`
- Logs: `/var/lib/hallpass/pass_history.csv` + `logs.db` + `photos/`
  - Dev fallback: `./data/` when /var/lib not writable

## Packaging
```bash
./scripts/build_deb.sh
# produces hallpass-qt_1.4.0_amd64.deb
```

## Stack
Python 3.10+, PySide6 QtQuick, QtMultimedia (QSoundEffect), QtTextToSpeech, OpenCV optional, SQLite3
