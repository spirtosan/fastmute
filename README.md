# Quick Mixer

A small per-app volume mixer for Windows with one-click mute, built for people who take calls while other apps (games, music, videos) are playing.

- Every app that is playing sound gets its own row with a volume slider and a big **MUTE** button.
- Tick **Work** next to your call-center / meeting app(s).
- Press **Mute non-work apps** (or the global hotkey **Ctrl+Alt+M**) to silence everything else at once. Press it again to unmute.

## Download

Grab `QuickMixer.exe` from the [latest release](https://github.com/spirtosan/fastmute/releases/latest) and run it. No installation or Python needed.

> Windows SmartScreen may warn about an unsigned app the first time. Click **More info → Run anyway**.

## Run from source

Requires Windows and Python 3.9+.

```bat
pip install -r requirements.txt
pythonw quick_mixer.py
```

Or just double-click `start.bat`, which installs the dependencies and launches the app.

## Usage

| Control | What it does |
| --- | --- |
| **Work** checkbox | Marks an app as work. Work apps are listed first and are never muted by the big button. |
| Slider | Sets that app's volume (0–100%). |
| **MUTE / MUTED** | Toggles mute for that one app (green = playing, red = muted). |
| **Mute non-work apps** | Mutes every non-work app; if they're all muted already, unmutes them. |
| **On top** | Keeps the window above other windows. |
| **Ctrl+Alt+M** | Global hotkey for the big button. Works even when the window isn't focused. |

The app list refreshes every 1.5 s, so apps appear as soon as they start playing sound.

## Settings

Settings are saved to `quick_mixer_config.json` next to the script / exe:

```json
{
  "work_apps": ["Teams.exe"],
  "hotkey": "ctrl+alt+m",
  "always_on_top": true
}
```

To change the hotkey, edit `hotkey` (any combo the [`keyboard`](https://github.com/boppreh/keyboard) library understands, e.g. `"ctrl+shift+f12"`) and restart the app.

## Building the exe

```bat
pip install pyinstaller
pyinstaller --onefile --noconsole --name QuickMixer quick_mixer.py
```

The result is in `dist\QuickMixer.exe`.
