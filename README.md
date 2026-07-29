# Resolume Autosave

Windows system-tray companion that periodically saves the open **Resolume Arena** composition and keeps rolling timestamped `.avc` backups.

Arena has no built-in autosave. This tool calls Arena’s local webserver API on an interval, then copies the composition file so a crash or bad edit does not wipe the last good state.

## Features

- Tray icon (gold = running, gray = paused)
- Timed save via Arena REST API (`Preferences → Webserver`)
- Timestamped backups under `Documents\Resolume Arena\Autosaves\`
- Retention limit per composition (default: last 30)
- Settings UI: interval, port, folders, start with Windows
- Manual **Save now**, pause/resume, log viewer

## Requirements

| Need | Detail |
|------|--------|
| Resolume Arena | Webserver enabled (default port `8080`) |
| Composition on disk | Save once in Arena (`Save As`) before relying on autosave |
| Python | 3.10+ on `PATH` |

## Install

```bat
cd autosave
pip install -r requirements.txt
python create_shortcut.py
```

Then start with **`Resolume Autosave.lnk`**, `start.bat`, or:

```bat
pythonw app.py
```

Use `run_console.bat` if you want a visible console for debugging.

## How it works

Every **N seconds** (default **300** / 5 minutes):

1. Ask Arena to save the current composition
2. Copy a timestamped file, e.g. `MyShow_20260724_195518.avc`
3. Prune older backups for that composition beyond the keep limit

Only the composition (`.avc`) is copied — media files are not duplicated.

## Tray menu

| Action | Effect |
|--------|--------|
| **Settings…** | Interval, host/port, backup folders, startup |
| **Pause / Resume** | Toggle without quitting |
| **Save now** | One save + backup immediately |
| **Open Autosaves folder** | Browse backups |
| **Open log** | View `autosave.log` |
| **Quit** | Exit |

## Configuration

Defaults live in `config.default.json`. Runtime overrides go to `config.json` (local, not committed):

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | `true` | Autosave loop on/off |
| `host` / `port` | `127.0.0.1` / `8080` | Arena webserver |
| `interval_seconds` | `300` | Seconds between saves |
| `backup_dir` | *(Documents Autosaves)* | Where `.avc` copies go |
| `keep_backups` | `30` | Max backups per composition |
| `start_with_windows` | `false` | Launch at login |

## Tips

- Use **Test connection** in Settings before a show if the webserver might be off.
- During live sets, raise the interval (10–15 min) or pause to cut disk writes.
- Backups are safety copies of the composition file only.

## License

Use and modify freely for your own shows and tooling.
