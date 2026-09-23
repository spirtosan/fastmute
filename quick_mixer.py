"""
Quick Mixer - a per-app volume mixer with one-click mute.

- Every app that plays sound gets a row: volume slider + big MUTE button.
- Tick "Work" on your call-center app(s). The "Mute non-work apps" button
  (or the global hotkey, default Ctrl+Alt+M) mutes/unmutes everything else
  in one go, so your games go silent when a call comes in.
- Settings are saved to quick_mixer_config.json next to this script.

Requires Windows + Python 3.9+:  pip install -r requirements.txt
"""

import json
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    tk.Tk().withdraw()
    messagebox.showerror("Quick Mixer", "Missing library.\n\nRun:  pip install pycaw psutil keyboard")
    sys.exit(1)

try:
    import keyboard  # optional: global hotkey
except ImportError:
    keyboard = None

APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG_PATH = APP_DIR / "quick_mixer_config.json"
DEFAULT_CONFIG = {"work_apps": [], "hotkey": "ctrl+alt+m", "always_on_top": True}
REFRESH_MS = 1500

MUTED_BG, MUTED_FG = "#d93636", "white"
LIVE_BG, LIVE_FG = "#2e9e4f", "white"


# ---------------------------------------------------------------- audio ----
def get_apps():
    """Return {process_name: [ISimpleAudioVolume, ...]} for all audio sessions."""
    apps = {}
    try:
        sessions = AudioUtilities.GetAllSessions()
    except Exception:
        return apps  # no audio device right now (e.g. headset unplugged)
    for session in sessions:
        try:
            name = session.Process.name() if session.Process else "System Sounds"
            apps.setdefault(name, []).append(session.SimpleAudioVolume)
        except Exception:
            continue  # process exited in the meantime
    return apps


def is_muted(volumes):
    try:
        return all(v.GetMute() for v in volumes)
    except Exception:
        return False


def set_muted(volumes, muted):
    for v in volumes:
        try:
            v.SetMute(1 if muted else 0, None)
        except Exception:
            pass


def get_level(volumes):
    try:
        return round(volumes[0].GetMasterVolume() * 100)
    except Exception:
        return 0


def set_level(volumes, percent):
    for v in volumes:
        try:
            v.SetMasterVolume(max(0.0, min(1.0, percent / 100)), None)
        except Exception:
            pass


# --------------------------------------------------------------- config ----
def load_config():
    try:
        return {**DEFAULT_CONFIG, **json.loads(CONFIG_PATH.read_text(encoding="utf-8"))}
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass


# ------------------------------------------------------------------- UI ----
class AppRow:
    def __init__(self, mixer, parent, name, volumes):
        self.mixer, self.name, self.volumes = mixer, name, volumes
        self.dragging = False
        self.updating = False

        self.frame = ttk.Frame(parent, padding=(6, 4))
        self.work_var = tk.BooleanVar(value=name in mixer.cfg["work_apps"])
        ttk.Checkbutton(self.frame, text="Work", variable=self.work_var,
                        command=self.on_work_toggle).grid(row=0, column=0, padx=(0, 8))

        label = name[:-4] if name.lower().endswith(".exe") else name
        ttk.Label(self.frame, text=label, width=18, anchor="w").grid(row=0, column=1)

        self.scale = ttk.Scale(self.frame, from_=0, to=100, length=180, command=self.on_scale)
        self.scale.grid(row=0, column=2, padx=6)
        self.scale.bind("<ButtonPress-1>", lambda e: setattr(self, "dragging", True))
        self.scale.bind("<ButtonRelease-1>", lambda e: setattr(self, "dragging", False))

        self.pct = ttk.Label(self.frame, width=4, anchor="e")
        self.pct.grid(row=0, column=3)

        self.btn = tk.Button(self.frame, width=8, relief="flat", font=("Segoe UI", 9, "bold"),
                             cursor="hand2", command=self.toggle_mute)
        self.btn.grid(row=0, column=4, padx=(8, 0))
        self.refresh(volumes)

    def refresh(self, volumes):
        self.volumes = volumes
        if not self.dragging:
            level = get_level(volumes)
            self.updating = True
            self.scale.set(level)
            self.updating = False
            self.pct.config(text=f"{level}%")
        muted = is_muted(volumes)
        self.btn.config(text="MUTED" if muted else "MUTE",
                        bg=MUTED_BG if muted else LIVE_BG,
                        fg=MUTED_FG if muted else LIVE_FG,
                        activebackground=MUTED_BG if muted else LIVE_BG)

    def on_scale(self, value):
        if self.updating:
            return
        level = round(float(value))
        set_level(self.volumes, level)
        self.pct.config(text=f"{level}%")

    def toggle_mute(self):
        set_muted(self.volumes, not is_muted(self.volumes))
        self.refresh(self.volumes)

    def on_work_toggle(self):
        work = set(self.mixer.cfg["work_apps"])
        (work.add if self.work_var.get() else work.discard)(self.name)
        self.mixer.cfg["work_apps"] = sorted(work)
        save_config(self.mixer.cfg)


class QuickMixer:
    def __init__(self):
        self.cfg = load_config()
        self.rows = {}
        self.events = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Quick Mixer")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", self.cfg["always_on_top"])

        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        hotkey = self.cfg["hotkey"] if keyboard else None
        self.game_btn = tk.Button(
            top, text="Mute non-work apps" + (f"   ({hotkey})" if hotkey else ""),
            font=("Segoe UI", 11, "bold"), bg="#3b5bdb", fg="white",
            activebackground="#2f4ac0", relief="flat", padx=12, pady=6,
            cursor="hand2", command=self.toggle_non_work)
        self.game_btn.pack(side="left", fill="x", expand=True)

        self.top_var = tk.BooleanVar(value=self.cfg["always_on_top"])
        ttk.Checkbutton(top, text="On top", variable=self.top_var,
                        command=self.on_top_toggle).pack(side="right", padx=(8, 0))

        ttk.Label(self.root, padding=(8, 0),
                  text="Tick “Work” for your call app — the big button never mutes it.",
                  foreground="#666").pack(anchor="w")
        ttk.Separator(self.root).pack(fill="x", pady=4)

        self.list = ttk.Frame(self.root)
        self.list.pack(fill="both", padx=4, pady=(0, 6))
        self.empty = ttk.Label(self.list, text="No apps are playing sound right now.", padding=12)
        self.empty.pack()

        if keyboard:
            try:
                keyboard.add_hotkey(self.cfg["hotkey"], lambda: self.events.put("toggle"))
            except Exception as exc:
                messagebox.showwarning("Quick Mixer", f"Couldn't register hotkey:\n{exc}")

        self.refresh()
        self.poll_events()

    # -- actions --
    def non_work_apps(self):
        return {n: r for n, r in self.rows.items() if not r.work_var.get()}

    def toggle_non_work(self):
        others = self.non_work_apps()
        mute = any(not is_muted(r.volumes) for r in others.values())
        for row in others.values():
            set_muted(row.volumes, mute)
            row.refresh(row.volumes)

    def on_top_toggle(self):
        self.cfg["always_on_top"] = self.top_var.get()
        self.root.attributes("-topmost", self.cfg["always_on_top"])
        save_config(self.cfg)

    # -- loops --
    def poll_events(self):
        try:
            while True:
                if self.events.get_nowait() == "toggle":
                    self.toggle_non_work()
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)

    def refresh(self):
        apps = get_apps()
        if set(apps) != set(self.rows):
            for row in self.rows.values():
                row.frame.destroy()
            self.rows.clear()
            # work apps first, then alphabetical
            order = sorted(apps, key=lambda n: (n not in self.cfg["work_apps"], n.lower()))
            for name in order:
                row = AppRow(self, self.list, name, apps[name])
                row.frame.pack(fill="x")
                self.rows[name] = row
            if apps:
                self.empty.pack_forget()
            else:
                self.empty.pack()
        else:
            for name, row in self.rows.items():
                row.refresh(apps[name])
        self.root.after(REFRESH_MS, self.refresh)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    QuickMixer().run()
